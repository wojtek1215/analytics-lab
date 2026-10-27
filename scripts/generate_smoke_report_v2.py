#!/usr/bin/env python3
"""Offline polish_asr_eval_v2 smoke report (no STT, no API calls).

Writes only under results/evaluation/v2/. Refuses to mutate legacy artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from asr_benchmark.evaluation.alignment import (  # noqa: E402
    align_words,
    assert_alignment_matches_counts,
)
from asr_benchmark.evaluation.metrics import (  # noqa: E402
    EVALUATION_VERSION_V2,
    compute_metrics,
)
from asr_benchmark.evaluation.normalize import (  # noqa: E402
    NORMALIZATION_VERSION,
    NUMBERS_NORMALIZATION_VERSION,
)
from asr_benchmark.evaluation.normalize_v2 import (  # noqa: E402
    ALL_RULES,
    EVALUATION_PROTOCOL,
    RULE_BRAND,
    RULE_CARDINAL,
    RULE_CURRENCY_SYMBOL,
    RULE_DECIMAL,
    RULE_DIGIT_DECIMAL,
    RULE_MINUS,
    RULE_PERCENT,
    RULE_UNIT,
    RULE_YEAR,
    WER_NORMALIZATION_VERSION,
    normalize_pl_wer_v1,
)
from asr_benchmark.evaluation.reporting_v2 import (  # noqa: E402
    render_comparison_markdown_v2,
    write_alignment_csv,
    write_json,
    write_markdown_v2,
)
from asr_benchmark.evaluation.taxonomy_v2 import (  # noqa: E402
    TAXONOMY_VERSION,
    reconcile_taxonomy_with_metrics,
    summarize_tags_v2,
    tag_alignment_v2,
)

LEGACY_ARTIFACTS = [
    ROOT / "results/evaluation/smoke_pl_basic_v1.json",
    ROOT / "results/evaluation/smoke_comparison.md",
    ROOT / "results/evaluation/smoke_error_taxonomy.md",
    ROOT / "results/evaluation/smoke_alignment_pl_basic_v1.json",
    ROOT / "results/evaluation/transcipts.md",
]

PROFILES = (
    NORMALIZATION_VERSION,
    NUMBERS_NORMALIZATION_VERSION,
    WER_NORMALIZATION_VERSION,
)

ABLATION_RULE_SETS: list[tuple[str, frozenset[str]]] = [
    ("numbers_only", frozenset({RULE_CARDINAL, RULE_DECIMAL, RULE_DIGIT_DECIMAL, RULE_YEAR, RULE_MINUS})),
    ("numbers_percent", frozenset({RULE_CARDINAL, RULE_DECIMAL, RULE_DIGIT_DECIMAL, RULE_YEAR, RULE_MINUS, RULE_PERCENT})),
    ("numbers_percent_units", frozenset({RULE_CARDINAL, RULE_DECIMAL, RULE_DIGIT_DECIMAL, RULE_YEAR, RULE_MINUS, RULE_PERCENT, RULE_UNIT, RULE_CURRENCY_SYMBOL})),
    ("full", ALL_RULES),
]


def _read_text(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8").strip()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _git_commit() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None


def _jiwer_version() -> str:
    try:
        return metadata.version("jiwer")
    except metadata.PackageNotFoundError:
        return "unknown"


def _hash_legacy() -> dict[str, str]:
    out: dict[str, str] = {}
    for path in LEGACY_ARTIFACTS:
        if path.is_file():
            out[str(path.relative_to(ROOT))] = _sha256_file(path)
    return out


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate polish_asr_eval_v2 smoke report from saved transcripts."
    )
    p.add_argument("--reference", type=Path, default=ROOT / "data/raw/test_pl_reference.txt")
    p.add_argument("--scribe", type=Path, default=ROOT / "results/smoke/scribe.txt")
    p.add_argument("--whisper", type=Path, default=ROOT / "results/smoke/whisper.txt")
    p.add_argument("--audio", type=Path, default=ROOT / "data/raw/test_pl.m4a")
    p.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/evaluation/v2",
        help="Must be results/evaluation/v2 (or a subdirectory)",
    )
    p.add_argument("--clip-id", default="test_pl")
    return p.parse_args(argv)


def _validate_output_dir(path: Path) -> Path:
    resolved = path.resolve()
    allowed = (ROOT / "results/evaluation/v2").resolve()
    if resolved != allowed and allowed not in resolved.parents:
        # allow exact v2 dir only (or nested under it)
        try:
            resolved.relative_to(allowed)
        except ValueError as exc:
            raise SystemExit(
                f"refusing to write outside results/evaluation/v2: {path}"
            ) from exc
    return resolved


def _profile_dict(clip) -> dict:
    hyp_words = len(clip.normalized_hypothesis.split()) if clip.normalized_hypothesis else 0
    return {
        "wer": clip.wer,
        "cer": clip.cer,
        "substitutions": clip.substitutions,
        "deletions": clip.deletions,
        "insertions": clip.insertions,
        "hits": clip.hits,
        "n_words_ref": clip.n_words_ref,
        "n_words_hyp": hyp_words,
        "n_chars_ref": clip.n_chars_ref,
        "char_substitutions": clip.char_substitutions,
        "char_deletions": clip.char_deletions,
        "char_insertions": clip.char_insertions,
        "normalized_reference": clip.normalized_reference,
        "normalized_hypothesis": clip.normalized_hypothesis,
        "normalization_version": clip.normalization_version,
        "evaluation_version": clip.evaluation_version,
        "status": clip.status,
    }


def _ablation_rows(reference: str, hypothesis: str, clip_id: str, model_id: str) -> list[dict]:
    rows = []
    for label, rules in ABLATION_RULE_SETS:
        def _norm(text: str, _rules: frozenset[str] = rules) -> str:
            return normalize_pl_wer_v1(text, enabled_rules=_rules)

        # Score via compute_wer path: normalize both, then metrics helpers
        from asr_benchmark.evaluation.metrics import compute_cer, compute_wer

        nr = _norm(reference)
        nh = _norm(hypothesis)
        word = compute_wer(nr, nh)
        rows.append(
            {
                "rules_label": label,
                "enabled_rules": sorted(rules),
                "wer": word["wer"],
                "substitutions": word["substitutions"],
                "deletions": word["deletions"],
                "insertions": word["insertions"],
                "n_words_ref": word["n_words_ref"],
                "cer": compute_cer(nr, nh)["cer"],
            }
        )
    return rows


def _meaningful_notes(model_id: str, edits: list[dict]) -> list[str]:
    notes: list[str] = []
    for e in edits:
        cat = e["primary_category"]
        ref = " ".join(e["ref_tokens"])
        hyp = " ".join(e["hyp_tokens"])
        if cat == "morphology":
            notes.append(
                f"{model_id}: morphology/lexical verb difference `{ref}` → `{hyp}`."
            )
        elif cat == "homophone_ambiguity":
            notes.append(
                f"{model_id}: homophone ambiguity `{ref}` → `{hyp}` "
                "(WER retains the distinction)."
            )
        elif cat == "proper_name_recognition":
            notes.append(
                f"{model_id}: proper-name recognition/misspelling `{ref}` → `{hyp}`."
            )
        elif cat == "potential_hallucination":
            notes.append(
                f"{model_id}: potential trailing hallucination `{hyp}` "
                "(insertion; not audio-verified here)."
            )
        elif cat == "lexical_substitution" and e["semantic_impact"] == "content_difference":
            notes.append(f"{model_id}: content substitution `{ref}` → `{hyp}`.")
        elif cat == "deletion":
            notes.append(f"{model_id}: deletion of `{ref}`.")
        elif cat == "insertion" and e["semantic_impact"] != "equivalent_formatting":
            notes.append(f"{model_id}: insertion of `{hyp}`.")
    return notes


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = _validate_output_dir(args.output)

    # Block accidental network stack imports in this process.
    for banned in ("requests", "mlx_whisper", "openai", "httpx"):
        if banned in sys.modules:
            raise SystemExit(f"refusing to run with {banned} already imported")

    legacy_before = _hash_legacy()

    reference = _read_text(args.reference)
    scribe_hyp = _read_text(args.scribe)
    whisper_hyp = _read_text(args.whisper)
    if not reference:
        raise SystemExit(f"empty reference: {args.reference}")

    audio_sha = _sha256_file(args.audio) if args.audio.is_file() else None
    hashes = {
        "reference_sha256": _sha256_text(reference),
        "scribe_sha256": _sha256_text(scribe_hyp),
        "whisper_sha256": _sha256_text(whisper_hyp),
        "audio_sha256": audio_sha,
    }

    models = [
        ("scribe_v2", scribe_hyp),
        ("whisper-large-v3-turbo", whisper_hyp),
    ]

    warnings: list[str] = []
    model_payload: dict[str, dict] = {}
    csv_rows: list[dict] = []
    taxonomy_payload: dict[str, dict] = {}
    all_notes: list[str] = []
    sensitivity: dict[str, list] = {}

    for model_id, hypothesis in models:
        profiles: dict[str, dict] = {}
        for profile in PROFILES:
            eval_ver = (
                EVALUATION_VERSION_V2
                if profile == WER_NORMALIZATION_VERSION
                else "1.0.0"
            )
            clip = compute_metrics(
                reference,
                hypothesis,
                clip_id=args.clip_id,
                model_id=model_id,
                normalization_version=profile,
                evaluation_version=eval_ver,
            )
            # Independent jiwer consistency: alignment must match
            alignment = align_words(
                reference,
                hypothesis,
                normalization_version=profile,
            )
            assert_alignment_matches_counts(
                alignment,
                substitutions=clip.substitutions,
                deletions=clip.deletions,
                insertions=clip.insertions,
                n_words_ref=clip.n_words_ref,
                wer=clip.wer,
            )
            profiles[profile] = _profile_dict(clip)

            tagged = tag_alignment_v2(alignment)
            reconcile_taxonomy_with_metrics(
                tagged,
                substitutions=clip.substitutions,
                deletions=clip.deletions,
                insertions=clip.insertions,
            )
            summary = summarize_tags_v2(tagged)

            for t in tagged:
                csv_rows.append(
                    {
                        "model_id": model_id,
                        "normalization_version": profile,
                        "op": t.op,
                        "ref_span": " ".join(t.ref_tokens),
                        "hyp_span": " ".join(t.hyp_tokens),
                        "ref_start": t.ref_start,
                        "ref_end": t.ref_end,
                        "hyp_start": t.hyp_start,
                        "hyp_end": t.hyp_end,
                        "edit_mass": t.edit_mass,
                        "primary_category": t.primary_category,
                        "secondary_tags": "|".join(t.secondary_tags),
                        "semantic_impact": t.semantic_impact,
                        "review_status": t.review_status,
                        "rationale": t.rationale,
                    }
                )

            if profile == WER_NORMALIZATION_VERSION:
                edit_dicts = []
                for t in tagged:
                    d = t.to_dict()
                    d["ref_span"] = " ".join(t.ref_tokens)
                    d["hyp_span"] = " ".join(t.hyp_tokens)
                    # tuples → lists for JSON
                    d["ref_tokens"] = list(t.ref_tokens)
                    d["hyp_tokens"] = list(t.hyp_tokens)
                    d["secondary_tags"] = list(t.secondary_tags)
                    edit_dicts.append(d)
                taxonomy_payload[model_id] = {
                    "summary": summary,
                    "edits": edit_dicts,
                    "alignment": {
                        "substitutions": alignment.substitutions,
                        "deletions": alignment.deletions,
                        "insertions": alignment.insertions,
                        "n_words_ref": alignment.n_words_ref,
                        "wer": alignment.wer,
                    },
                }
                all_notes.extend(_meaningful_notes(model_id, edit_dicts))

        sensitivity[model_id] = _ablation_rows(
            reference, hypothesis, args.clip_id, model_id
        )
        model_payload[model_id] = {
            "model_id": model_id,
            "hypothesis_sha256": _sha256_text(hypothesis),
            "profiles": profiles,
            "number_format_sensitivity": {
                "wer_basic": profiles[NORMALIZATION_VERSION]["wer"],
                "wer_numbers": profiles[NUMBERS_NORMALIZATION_VERSION]["wer"],
                "wer_normalized": profiles[WER_NORMALIZATION_VERSION]["wer"],
                "delta_basic_to_normalized": (
                    profiles[WER_NORMALIZATION_VERSION]["wer"]
                    - profiles[NORMALIZATION_VERSION]["wer"]
                ),
            },
        }

    # Cross-check legacy basic WER against saved JSON when present
    legacy_json = ROOT / "results/evaluation/smoke_pl_basic_v1.json"
    if legacy_json.is_file():
        saved = json.loads(legacy_json.read_text(encoding="utf-8"))
        by_id = {m["model_id"]: m for m in saved["models"]}
        for mid in model_payload:
            got = model_payload[mid]["profiles"][NORMALIZATION_VERSION]
            exp = by_id[mid]
            for key in ("wer", "cer", "substitutions", "deletions", "insertions", "n_words_ref"):
                if abs(float(got[key]) - float(exp[key])) > 1e-12:
                    raise SystemExit(
                        f"legacy pl_basic_v1 mismatch for {mid}.{key}: "
                        f"{got[key]} != {exp[key]}"
                    )

    unavailable = {
        "named_entity_accuracy": (
            "Requires verified entity span annotations on the reference; "
            "not present for this smoke clip."
        ),
        "number_value_accuracy_annotated": (
            "Optional digit-token agreement can be derived, but annotated "
            "number-value accuracy needs human-verified number spans."
        ),
        "critical_meaning_error_rate": (
            "Requires human labels for meaning-changing errors."
        ),
    }

    created_at = datetime.now(timezone.utc).isoformat()
    metrics_payload = {
        "clip_id": args.clip_id,
        "evaluation_protocol": EVALUATION_PROTOCOL,
        "evaluation_version": EVALUATION_VERSION_V2,
        "primary_normalization_version": WER_NORMALIZATION_VERSION,
        "primary_metric_status": "accepted",
        "primary_metric_warning": None,
        "taxonomy_version": TAXONOMY_VERSION,
        "api_used": False,
        "asr_inference_performed": False,
        "created_at": created_at,
        "model_ids": [m for m, _ in models],
        "models": model_payload,
        "hashes": hashes,
        "paths": {
            "reference": str(args.reference.relative_to(ROOT)),
            "scribe": str(args.scribe.relative_to(ROOT)),
            "whisper": str(args.whisper.relative_to(ROOT)),
            "audio": str(args.audio.relative_to(ROOT)) if args.audio.is_file() else None,
        },
        "environment": {
            "python_version": platform.python_version(),
            "jiwer_version": _jiwer_version(),
            "git_commit": _git_commit(),
            "platform": platform.platform(),
        },
        "run_configuration": {
            "profiles": list(PROFILES),
            "ablation_rule_sets": [label for label, _ in ABLATION_RULE_SETS],
        },
        "normalization_sensitivity": sensitivity,
        "taxonomy": taxonomy_payload,
        "meaningful_error_notes": all_notes,
        "unavailable_metrics": unavailable,
        "validation_warnings": warnings,
        "score_status": "ok",
        "legacy_artifact_hashes_before": legacy_before,
    }

    # Write artifacts
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = out_dir / "smoke_metrics.json"
    alignment_path = out_dir / "smoke_alignment.csv"
    taxonomy_path = out_dir / "smoke_taxonomy.json"
    review_path = out_dir / "smoke_review_annotations.json"
    md_path = out_dir / "smoke_comparison_v2.md"

    write_json(metrics_path, metrics_payload)
    write_alignment_csv(alignment_path, csv_rows)
    write_json(
        taxonomy_path,
        {
            "clip_id": args.clip_id,
            "taxonomy_version": TAXONOMY_VERSION,
            "normalization_version": WER_NORMALIZATION_VERSION,
            "models": taxonomy_payload,
            "review_status": "auto_inferred",
        },
    )
    write_json(
        review_path,
        {
            "clip_id": args.clip_id,
            "note": "Human-review template; human_label is null until audited.",
            "items": [
                {
                    "model_id": row["model_id"],
                    "normalization_version": row["normalization_version"],
                    "ref_span": row["ref_span"],
                    "hyp_span": row["hyp_span"],
                    "op": row["op"],
                    "auto_primary_category": row["primary_category"],
                    "human_label": None,
                    "human_semantic_impact": None,
                    "reviewer": None,
                    "notes": None,
                }
                for row in csv_rows
                if row["normalization_version"] == WER_NORMALIZATION_VERSION
            ],
        },
    )

    # Render markdown from the written metrics payload (reload for consistency)
    written = json.loads(metrics_path.read_text(encoding="utf-8"))
    md_body = render_comparison_markdown_v2(written)
    # Verify key numbers appear
    for mid in written["model_ids"]:
        wer = written["models"][mid]["profiles"][WER_NORMALIZATION_VERSION]["wer"]
        token = f"{100.0 * wer:.1f}%"
        if token not in md_body:
            raise SystemExit(f"report missing WER token {token} for {mid}")
    write_markdown_v2(md_path, written)

    legacy_after = _hash_legacy()
    if legacy_after != legacy_before:
        raise SystemExit(
            "legacy evaluation artifacts changed during v2 report generation"
        )
    metrics_payload["legacy_artifact_hashes_after"] = legacy_after
    # Re-write with after hashes
    write_json(metrics_path, metrics_payload)
    # Re-render md with final payload
    write_markdown_v2(md_path, metrics_payload)

    print(f"Wrote {metrics_path.relative_to(ROOT)}")
    print(f"Wrote {alignment_path.relative_to(ROOT)}")
    print(f"Wrote {taxonomy_path.relative_to(ROOT)}")
    print(f"Wrote {review_path.relative_to(ROOT)}")
    print(f"Wrote {md_path.relative_to(ROOT)}")
    for mid, _ in models:
        v = model_payload[mid]["profiles"][WER_NORMALIZATION_VERSION]
        print(
            f"{mid}: normalized WER={100 * v['wer']:.1f}% "
            f"S={v['substitutions']} D={v['deletions']} I={v['insertions']} "
            f"N={v['n_words_ref']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
