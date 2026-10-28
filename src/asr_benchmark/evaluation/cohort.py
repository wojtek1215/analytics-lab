"""Offline multi-clip cohort scoring (manifest + hypothesis dirs; no STT/API)."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from asr_benchmark.evaluation.alignment import align_words
from asr_benchmark.evaluation.metrics import (
    EVALUATION_VERSION_V2,
    ClipMetrics,
    aggregate_corpus,
    compute_metrics,
)
from asr_benchmark.evaluation.normalize import (
    NORMALIZATION_VERSION,
    NUMBERS_NORMALIZATION_VERSION,
)
from asr_benchmark.evaluation.normalize_v2 import (
    EVALUATION_PROTOCOL,
    WER_NORMALIZATION_VERSION,
)
from asr_benchmark.evaluation.taxonomy_v2 import (
    TAXONOMY_VERSION,
    reconcile_taxonomy_with_metrics,
    tag_alignment_v2,
)
from asr_benchmark.inference.whisper_batch import ManifestClip, load_manifest_rows

PROFILES = (
    NORMALIZATION_VERSION,
    NUMBERS_NORMALIZATION_VERSION,
    WER_NORMALIZATION_VERSION,
)

PRIMARY_PROFILE = WER_NORMALIZATION_VERSION
MODEL_SCRIBE = "scribe_v2"
MODEL_WHISPER = "whisper-large-v3-turbo"


def _read_hypothesis(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8").strip()


def score_cohort(
    *,
    clips: Sequence[ManifestClip],
    hypothesis_dirs: Mapping[str, Path],
    cohort_id: str,
) -> dict[str, Any]:
    """Score all clips × models × normalization profiles; attach primary taxonomy."""
    per_clip_rows: list[dict[str, Any]] = []
    alignment_rows: list[dict[str, Any]] = []
    metrics_by_model_profile: dict[str, dict[str, list[ClipMetrics]]] = {
        mid: {p: [] for p in PROFILES} for mid in hypothesis_dirs
    }
    taxonomy_by_model: dict[str, list[dict[str, Any]]] = {
        mid: [] for mid in hypothesis_dirs
    }
    missing: list[dict[str, str]] = []

    for clip in clips:
        for model_id, hyp_dir in hypothesis_dirs.items():
            hyp_path = hyp_dir / f"{clip.clip_id}.txt"
            try:
                hypothesis = _read_hypothesis(hyp_path)
            except FileNotFoundError:
                missing.append(
                    {
                        "clip_id": clip.clip_id,
                        "model_id": model_id,
                        "path": str(hyp_path),
                    }
                )
                continue

            reference = clip.sentence
            for profile in PROFILES:
                m = compute_metrics(
                    reference,
                    hypothesis,
                    clip_id=clip.clip_id,
                    model_id=model_id,
                    normalization_version=profile,
                    evaluation_version=EVALUATION_VERSION_V2,
                )
                metrics_by_model_profile[model_id][profile].append(m)
                per_clip_rows.append(
                    {
                        "cohort_id": cohort_id,
                        "clip_id": clip.clip_id,
                        "model_id": model_id,
                        "normalization_version": profile,
                        "wer": m.wer,
                        "cer": m.cer,
                        "substitutions": m.substitutions,
                        "deletions": m.deletions,
                        "insertions": m.insertions,
                        "n_words_ref": m.n_words_ref,
                        "n_chars_ref": m.n_chars_ref,
                        "reference": reference,
                        "hypothesis": hypothesis,
                        "normalized_reference": m.normalized_reference,
                        "normalized_hypothesis": m.normalized_hypothesis,
                    }
                )

            # Taxonomy on primary profile only
            primary = compute_metrics(
                reference,
                hypothesis,
                clip_id=clip.clip_id,
                model_id=model_id,
                normalization_version=PRIMARY_PROFILE,
                evaluation_version=EVALUATION_VERSION_V2,
            )
            alignment = align_words(
                reference,
                hypothesis,
                normalization_version=PRIMARY_PROFILE,
            )
            tagged = tag_alignment_v2(alignment)
            reconcile_taxonomy_with_metrics(
                tagged,
                substitutions=primary.substitutions,
                deletions=primary.deletions,
                insertions=primary.insertions,
            )
            for t in tagged:
                td = t.to_dict()
                row = {
                    "cohort_id": cohort_id,
                    "clip_id": clip.clip_id,
                    "model_id": model_id,
                    "normalization_version": PRIMARY_PROFILE,
                    "reference": reference,
                    "hypothesis": hypothesis,
                    "op": td["op"],
                    "ref_span": " ".join(td["ref_tokens"]),
                    "hyp_span": " ".join(td["hyp_tokens"]),
                    "edit_mass": td["edit_mass"],
                    "primary_category": td["primary_category"],
                    "secondary_tags": "|".join(td["secondary_tags"]),
                    "semantic_impact": td["semantic_impact"],
                    "review_status": td["review_status"],
                    "rationale": td["rationale"],
                }
                alignment_rows.append(row)
                taxonomy_by_model[model_id].append(td)

    corpus: dict[str, Any] = {}
    for model_id, by_profile in metrics_by_model_profile.items():
        corpus[model_id] = {}
        for profile, clip_metrics in by_profile.items():
            if not clip_metrics:
                continue
            agg = aggregate_corpus(clip_metrics)
            corpus[model_id][profile] = agg.to_dict()

    taxonomy_summary: dict[str, Any] = {}
    for model_id, tagged_dicts in taxonomy_by_model.items():
        if not tagged_dicts:
            taxonomy_summary[model_id] = {
                "taxonomy_version": TAXONOMY_VERSION,
                "n_edits": 0,
                "total_edit_mass": 0,
            }
            continue
        # rebuild minimal objects for summarize — use Counter directly
        by_primary: Counter[str] = Counter()
        by_impact: Counter[str] = Counter()
        total = 0
        for d in tagged_dicts:
            mass = int(d["edit_mass"])
            by_primary[d["primary_category"]] += mass
            by_impact[d["semantic_impact"]] += mass
            total += mass
        taxonomy_summary[model_id] = {
            "taxonomy_version": TAXONOMY_VERSION,
            "n_edits": len(tagged_dicts),
            "total_edit_mass": total,
            "by_primary_category": dict(by_primary),
            "by_semantic_impact": dict(by_impact),
        }

    hard_cases = _select_hard_cases(per_clip_rows, alignment_rows)

    return {
        "cohort_id": cohort_id,
        "evaluation_protocol": EVALUATION_PROTOCOL,
        "evaluation_version": EVALUATION_VERSION_V2,
        "primary_normalization_version": PRIMARY_PROFILE,
        "taxonomy_version": TAXONOMY_VERSION,
        "api_used": False,
        "asr_inference_performed": False,
        "n_clips_manifest": len(clips),
        "n_missing_hypotheses": len(missing),
        "missing_hypotheses": missing,
        "corpus": corpus,
        "taxonomy_summary": taxonomy_summary,
        "per_clip": per_clip_rows,
        "alignment_rows": alignment_rows,
        "hard_cases": hard_cases,
    }


def _select_hard_cases(
    per_clip: Sequence[Mapping[str, Any]],
    alignments: Sequence[Mapping[str, Any]],
    *,
    top_n: int = 8,
) -> list[dict[str, Any]]:
    """Clips with highest primary WER, plus notable content-changing edits."""
    primary_rows = [
        r
        for r in per_clip
        if r["normalization_version"] == PRIMARY_PROFILE
    ]
    # pair by clip
    by_clip: dict[str, dict[str, Mapping[str, Any]]] = {}
    for r in primary_rows:
        by_clip.setdefault(r["clip_id"], {})[r["model_id"]] = r

    ranked: list[tuple[float, str, dict[str, Mapping[str, Any]]]] = []
    for clip_id, models in by_clip.items():
        max_wer = max(float(m["wer"]) for m in models.values())
        ranked.append((max_wer, clip_id, models))
    ranked.sort(reverse=True)

    cases: list[dict[str, Any]] = []
    for max_wer, clip_id, models in ranked[:top_n]:
        if max_wer <= 0:
            continue
        edits = [a for a in alignments if a["clip_id"] == clip_id]
        content_edits = [
            a
            for a in edits
            if a.get("semantic_impact") == "content_difference"
        ]
        cases.append(
            {
                "clip_id": clip_id,
                "max_primary_wer": max_wer,
                "models": {
                    mid: {
                        "wer": models[mid]["wer"],
                        "sdi": (
                            f"{models[mid]['substitutions']}/"
                            f"{models[mid]['deletions']}/"
                            f"{models[mid]['insertions']}"
                        ),
                        "hypothesis": models[mid]["hypothesis"],
                        "reference": models[mid]["reference"],
                    }
                    for mid in models
                },
                "content_edits": [
                    {
                        "model_id": e["model_id"],
                        "op": e["op"],
                        "ref_span": e.get("ref_span") or " ".join(e.get("ref_tokens", [])),
                        "hyp_span": e.get("hyp_span") or " ".join(e.get("hyp_tokens", [])),
                        "primary_category": e["primary_category"],
                        "rationale": e.get("rationale"),
                    }
                    for e in content_edits[:6]
                ],
            }
        )
    return cases


def write_cohort_artifacts(payload: Mapping[str, Any], *, cohort_dir: Path) -> dict[str, Path]:
    metrics_dir = cohort_dir / "metrics"
    errors_dir = cohort_dir / "errors"
    reports_dir = cohort_dir / "reports"
    for d in (metrics_dir, errors_dir, reports_dir):
        d.mkdir(parents=True, exist_ok=True)

    corpus_path = metrics_dir / "corpus.json"
    per_clip_path = metrics_dir / "per_clip.csv"
    alignment_path = errors_dir / "alignment.csv"
    taxonomy_path = errors_dir / "taxonomy_summary.json"
    hard_cases_json = errors_dir / "hard_cases.json"
    hard_cases_md = errors_dir / "hard_cases.md"
    report_md = reports_dir / "comparison.md"

    corpus_path.write_text(
        json.dumps(
            {
                "cohort_id": payload["cohort_id"],
                "evaluation_protocol": payload["evaluation_protocol"],
                "evaluation_version": payload["evaluation_version"],
                "primary_normalization_version": payload[
                    "primary_normalization_version"
                ],
                "n_clips_manifest": payload["n_clips_manifest"],
                "n_missing_hypotheses": payload["n_missing_hypotheses"],
                "missing_hypotheses": payload["missing_hypotheses"],
                "corpus": payload["corpus"],
                "api_used": False,
                "asr_inference_performed": False,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    _write_csv(
        per_clip_path,
        payload["per_clip"],
        fieldnames=[
            "cohort_id",
            "clip_id",
            "model_id",
            "normalization_version",
            "wer",
            "cer",
            "substitutions",
            "deletions",
            "insertions",
            "n_words_ref",
            "n_chars_ref",
            "reference",
            "hypothesis",
            "normalized_reference",
            "normalized_hypothesis",
        ],
    )

    align_fields = [
        "cohort_id",
        "clip_id",
        "model_id",
        "normalization_version",
        "op",
        "ref_span",
        "hyp_span",
        "edit_mass",
        "primary_category",
        "secondary_tags",
        "semantic_impact",
        "review_status",
        "rationale",
        "reference",
        "hypothesis",
    ]
    # ensure ref_span/hyp_span present
    align_rows = []
    for row in payload["alignment_rows"]:
        r = dict(row)
        if "ref_span" not in r:
            r["ref_span"] = " ".join(r.get("ref_tokens") or [])
        if "hyp_span" not in r:
            r["hyp_span"] = " ".join(r.get("hyp_tokens") or [])
        align_rows.append(r)
    _write_csv(alignment_path, align_rows, fieldnames=align_fields)

    taxonomy_path.write_text(
        json.dumps(payload["taxonomy_summary"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    hard_cases_json.write_text(
        json.dumps(payload["hard_cases"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    hard_cases_md.write_text(
        _render_hard_cases_md(payload), encoding="utf-8"
    )
    report_md.write_text(_render_comparison_md(payload), encoding="utf-8")

    return {
        "corpus": corpus_path,
        "per_clip": per_clip_path,
        "alignment": alignment_path,
        "taxonomy": taxonomy_path,
        "hard_cases_json": hard_cases_json,
        "hard_cases_md": hard_cases_md,
        "report": report_md,
    }


def _write_csv(
    path: Path, rows: Sequence[Mapping[str, Any]], *, fieldnames: list[str]
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _pct(rate: float) -> str:
    return f"{100.0 * rate:.1f}%"


def _render_comparison_md(payload: Mapping[str, Any]) -> str:
    cohort = payload["cohort_id"]
    primary = payload["primary_normalization_version"]
    corpus = payload["corpus"]
    lines = [
        f"# Cohort comparison — `{cohort}`",
        "",
        f"- **Protocol:** `{payload['evaluation_protocol']}` / eval `{payload['evaluation_version']}`",
        f"- **Primary metric:** WER after `{primary}`",
        f"- **Clips in manifest:** {payload['n_clips_manifest']}",
        f"- **Missing hypotheses:** {payload['n_missing_hypotheses']}",
        f"- **Offline only:** `api_used={payload['api_used']}`, "
        f"`asr_inference_performed={payload['asr_inference_performed']}`",
        "",
        "## Corpus WER / CER",
        "",
        "| Model | Basic WER | Numbers WER | **Normalized WER** | Norm CER | Norm S/D/I | N_words |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for model_id, profiles in corpus.items():
        basic = profiles.get(NORMALIZATION_VERSION, {})
        numbers = profiles.get(NUMBERS_NORMALIZATION_VERSION, {})
        norm = profiles.get(WER_NORMALIZATION_VERSION, {})
        if not norm:
            continue
        lines.append(
            f"| `{model_id}` | {_pct(basic.get('wer', float('nan')))} | "
            f"{_pct(numbers.get('wer', float('nan')))} | "
            f"**{_pct(norm['wer'])}** | {_pct(norm['cer'])} | "
            f"{norm['substitutions']}/{norm['deletions']}/{norm['insertions']} | "
            f"{norm['n_words_ref']} |"
        )

    lines.extend(
        [
            "",
            "## Error taxonomy (primary profile)",
            "",
            "Edit mass by automatic `taxonomy_v2` category "
            "(does **not** change WER).",
            "",
        ]
    )
    tax = payload["taxonomy_summary"]
    for model_id, summary in tax.items():
        lines.append(f"### `{model_id}` — total edit mass {summary.get('total_edit_mass', 0)}")
        lines.append("")
        by_cat = summary.get("by_primary_category") or {}
        if not by_cat:
            lines.append("_No residual edits under primary normalization._")
            lines.append("")
            continue
        lines.append("| Category | Edit mass |")
        lines.append("|---|---:|")
        for cat, mass in sorted(by_cat.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"| `{cat}` | {mass} |")
        impact = summary.get("by_semantic_impact") or {}
        if impact:
            lines.append("")
            lines.append(
                "Impact: "
                + ", ".join(f"`{k}`={v}" for k, v in sorted(impact.items()))
            )
        lines.append("")

    lines.extend(
        [
            "## Hard cases",
            "",
            "See [`../errors/hard_cases.md`](../errors/hard_cases.md) for "
            "clip-level examples (where models fail most).",
            "",
            "## Limitations",
            "",
            f"- N = {payload['n_clips_manifest']} QA clips; not a population estimate.",
            "- Holdout must not guide methodology changes.",
            "- Taxonomy labels are auto-inferred until human review.",
            "",
        ]
    )
    return "\n".join(lines)


def _render_hard_cases_md(payload: Mapping[str, Any]) -> str:
    lines = [
        f"# Hard cases — `{payload['cohort_id']}`",
        "",
        f"Primary profile: `{payload['primary_normalization_version']}`. "
        "Focus: content-changing residual errors after normalization.",
        "",
    ]
    cases = payload.get("hard_cases") or []
    if not cases:
        lines.append("_No non-zero WER clips in this cohort._")
        lines.append("")
        return "\n".join(lines)

    for i, case in enumerate(cases, start=1):
        lines.append(
            f"## {i}. `{case['clip_id']}` (max primary WER {_pct(case['max_primary_wer'])})"
        )
        lines.append("")
        # reference from any model block
        any_model = next(iter(case["models"].values()))
        lines.append(f"- **Reference:** {any_model['reference']}")
        for mid, block in case["models"].items():
            lines.append(
                f"- **`{mid}`** WER {_pct(block['wer'])} "
                f"(S/D/I {block['sdi']}): {block['hypothesis']}"
            )
        if case.get("content_edits"):
            lines.append("")
            lines.append("| Model | Op | Ref | Hyp | Category |")
            lines.append("|---|---|---|---|---|")
            for e in case["content_edits"]:
                lines.append(
                    f"| `{e['model_id']}` | {e['op']} | "
                    f"{e['ref_span'] or '∅'} | {e['hyp_span'] or '∅'} | "
                    f"`{e['primary_category']}` |"
                )
        lines.append("")
    return "\n".join(lines)


def evaluate_manifest_cohort(
    *,
    manifest: Path,
    cohort_dir: Path,
    cohort_id: str,
    scribe_dir: Path | None = None,
    whisper_dir: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Path]]:
    clips = load_manifest_rows(manifest)
    hyp_dirs = {
        MODEL_SCRIBE: scribe_dir or (cohort_dir / "hypotheses" / "scribe"),
        MODEL_WHISPER: whisper_dir or (cohort_dir / "hypotheses" / "whisper"),
    }
    payload = score_cohort(
        clips=clips, hypothesis_dirs=hyp_dirs, cohort_id=cohort_id
    )
    paths = write_cohort_artifacts(payload, cohort_dir=cohort_dir)
    return payload, paths
