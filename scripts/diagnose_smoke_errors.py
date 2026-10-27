#!/usr/bin/env python3
"""Offline alignment + taxonomy diagnostics for saved smoke transcripts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from asr_benchmark.evaluation.alignment import (  # noqa: E402
    align_words,
    assert_alignment_matches_counts,
)
from asr_benchmark.evaluation.metrics import compute_metrics  # noqa: E402
from asr_benchmark.evaluation.normalize import (  # noqa: E402
    NORMALIZATION_VERSION,
    NUMBERS_NORMALIZATION_VERSION,
)
from asr_benchmark.evaluation.taxonomy import (  # noqa: E402
    TAXONOMY_VERSION,
    summarize_tags,
    tag_alignment,
)


def _read_text(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8").strip()


def _pct(x: float | None) -> str:
    if x is None:
        return "—"
    return f"{100.0 * x:.1f}%"


def _load_existing_smoke_metrics(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Diagnose smoke ASR edits (alignment + taxonomy_v0). Offline only."
    )
    p.add_argument(
        "--reference",
        type=Path,
        default=ROOT / "data/raw/test_pl_reference.txt",
    )
    p.add_argument(
        "--scribe",
        type=Path,
        default=ROOT / "results/smoke/scribe.txt",
    )
    p.add_argument(
        "--whisper",
        type=Path,
        default=ROOT / "results/smoke/whisper.txt",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/evaluation",
    )
    p.add_argument("--clip-id", default="test_pl")
    p.add_argument(
        "--baseline-json",
        type=Path,
        default=ROOT / "results/evaluation/smoke_pl_basic_v1.json",
        help="Existing primary metrics JSON to cross-check (read-only)",
    )
    return p.parse_args(argv)


def _diagnose_model(
    *,
    clip_id: str,
    model_id: str,
    reference: str,
    hypothesis: str,
    baseline_model: dict | None,
) -> dict:
    metrics = compute_metrics(
        reference,
        hypothesis,
        clip_id=clip_id,
        model_id=model_id,
        normalization_version=NORMALIZATION_VERSION,
    )
    alignment = align_words(reference, hypothesis)
    assert_alignment_matches_counts(
        alignment,
        substitutions=metrics.substitutions,
        deletions=metrics.deletions,
        insertions=metrics.insertions,
        n_words_ref=metrics.n_words_ref,
        wer=metrics.wer,
    )

    if baseline_model is not None:
        assert_alignment_matches_counts(
            alignment,
            substitutions=baseline_model["substitutions"],
            deletions=baseline_model["deletions"],
            insertions=baseline_model["insertions"],
            n_words_ref=baseline_model["n_words_ref"],
            wer=float(baseline_model["wer"]),
        )

    tagged = tag_alignment(alignment)
    summary = summarize_tags(tagged)

    # Auxiliary sensitivity (not primary): whole-clip WER under pl_numbers_v1
    numbers_metrics = compute_metrics(
        reference,
        hypothesis,
        clip_id=clip_id,
        model_id=model_id,
        normalization_version=NUMBERS_NORMALIZATION_VERSION,
    )

    return {
        "clip_id": clip_id,
        "model_id": model_id,
        "normalization_version": NORMALIZATION_VERSION,
        "taxonomy_version": TAXONOMY_VERSION,
        "wer": metrics.wer,
        "substitutions": metrics.substitutions,
        "deletions": metrics.deletions,
        "insertions": metrics.insertions,
        "n_words_ref": metrics.n_words_ref,
        "total_edit_mass": alignment.total_edit_mass,
        "wer_check_ok": True,
        "pl_numbers_v1_wer_auxiliary": numbers_metrics.wer,
        "summary": summary,
        "ops": [t.to_dict() for t in tagged],
        "baseline_crosscheck": baseline_model is not None,
    }


def render_markdown(payload: dict) -> str:
    lines: list[str] = [
        "# Smoke error taxonomy (`taxonomy_v0`)",
        "",
        f"- **clip_id:** `{payload['clip_id']}`",
        f"- **normalization (primary):** `{NORMALIZATION_VERSION}`",
        f"- **taxonomy:** `{TAXONOMY_VERSION}`",
        "",
        "Heuristics are exploratory. Tags on a chunk may be `ambiguous`; "
        "one edit operation does not always map to one semantic error. "
        "Primary WER is unchanged.",
        "",
        "## Consistency with primary WER",
        "",
        "| Model | S | D | I | N | mass | WER | vs baseline JSON |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]

    for model in payload["models"]:
        lines.append(
            "| {mid} | {s} | {d} | {i} | {n} | {m} | {wer} | {ok} |".format(
                mid=model["model_id"],
                s=model["substitutions"],
                d=model["deletions"],
                i=model["insertions"],
                n=model["n_words_ref"],
                m=model["total_edit_mass"],
                wer=_pct(model["wer"]),
                ok="OK" if model.get("baseline_crosscheck") else "n/a",
            )
        )

    lines.extend(
        [
            "",
            "## Format vs content (edit mass)",
            "",
            "| Model | format_only | content_changing | unclear |",
            "|---|---:|---:|---:|",
        ]
    )
    for model in payload["models"]:
        pct = model["summary"]["pct_by_content_impact"]
        lines.append(
            "| {mid} | {f} | {c} | {u} |".format(
                mid=model["model_id"],
                f=_pct(pct.get("format_only")),
                c=_pct(pct.get("content_changing")),
                u=_pct(pct.get("unclear")),
            )
        )

    lines.extend(
        [
            "",
            "## Mass by tag",
            "",
            "| Model | number_format | proper_name | lexical | homophone | insertion_extra | ambiguous |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    tags = [
        "number_format",
        "proper_name",
        "lexical",
        "homophone",
        "insertion_extra",
        "ambiguous",
    ]
    for model in payload["models"]:
        mass = model["summary"]["mass_by_tag"]
        total = model["total_edit_mass"] or 1
        cells = []
        for t in tags:
            v = mass.get(t, 0)
            cells.append(f"{v} ({100 * v / total:.0f}%)")
        lines.append(f"| {model['model_id']} | " + " | ".join(cells) + " |")

    lines.extend(
        [
            "",
            "## Auxiliary: `pl_numbers_v1` WER (not primary)",
            "",
            "| Model | pl_basic_v1 WER | pl_numbers_v1 WER |",
            "|---|---:|---:|",
        ]
    )
    for model in payload["models"]:
        lines.append(
            f"| {model['model_id']} | {_pct(model['wer'])} | "
            f"{_pct(model['pl_numbers_v1_wer_auxiliary'])} |"
        )

    for model in payload["models"]:
        lines.extend(
            [
                "",
                f"## Operations — `{model['model_id']}`",
                "",
                "| # | op | REF | HYP | mass | tag | impact | notes |",
                "|---|---|---|---|---:|---|---|---|",
            ]
        )
        for idx, op in enumerate(model["ops"], start=1):
            ref = " ".join(op["ref_tokens"]) or "∅"
            hyp = " ".join(op["hyp_tokens"]) or "∅"
            lines.append(
                "| {i} | {op} | {ref} | {hyp} | {m} | {tag} | {imp} | {notes} |".format(
                    i=idx,
                    op=op["op"],
                    ref=ref.replace("|", "\\|"),
                    hyp=hyp.replace("|", "\\|"),
                    m=op["edit_mass"],
                    tag=op["tag"],
                    imp=op["content_impact"],
                    notes=(op["notes"] or "—").replace("|", "\\|"),
                )
            )

    lines.extend(
        [
            "",
            "## Interpretation (from counted mass)",
            "",
            payload.get("interpretation", ""),
            "",
            "## Manual audit",
            "",
            "Review rows tagged `ambiguous` / impact `unclear` before quoting "
            "percentages in external reports.",
            "",
        ]
    )
    return "\n".join(lines)


def _build_interpretation(models: list[dict]) -> str:
    by_id = {m["model_id"]: m for m in models}
    scribe = by_id.get("scribe_v2")
    whisper = by_id.get("whisper-large-v3-turbo")
    if not scribe or not whisper:
        return "Interpretation requires both scribe_v2 and whisper-large-v3-turbo."

    def share(model: dict, tag: str) -> float:
        return float(model["summary"]["mass_by_tag"].get(tag, 0)) / max(
            model["total_edit_mass"], 1
        )

    s_num = share(scribe, "number_format")
    s_amb = share(scribe, "ambiguous")
    w_lex = share(whisper, "lexical")
    w_name = share(whisper, "proper_name")
    w_ins = share(whisper, "insertion_extra")
    s_fmt = float(
        scribe["summary"]["pct_by_content_impact"].get("format_only") or 0
    )
    w_chg = float(
        whisper["summary"]["pct_by_content_impact"].get("content_changing") or 0
    )

    return (
        f"Scribe edit mass is dominated by number-related tags "
        f"(number_format={_pct(s_num)}, ambiguous-with-numbers often nearby; "
        f"ambiguous={_pct(s_amb)}); format_only impact ≈ {_pct(s_fmt)}. "
        f"Whisper retains similar headline WER but more "
        f"lexical={_pct(w_lex)}, proper_name={_pct(w_name)}, "
        f"insertion_extra={_pct(w_ins)}; content_changing ≈ {_pct(w_chg)}. "
        "Nearly equal WER therefore does not imply similar error types."
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    reference = _read_text(args.reference)
    scribe_hyp = _read_text(args.scribe)
    whisper_hyp = _read_text(args.whisper)
    if not reference:
        raise SystemExit(f"empty reference: {args.reference}")

    baseline = _load_existing_smoke_metrics(args.baseline_json)
    baseline_by_model: dict[str, dict] = {}
    if baseline and "models" in baseline:
        for m in baseline["models"]:
            baseline_by_model[m["model_id"]] = m

    models = []
    for model_id, hyp in [
        ("scribe_v2", scribe_hyp),
        ("whisper-large-v3-turbo", whisper_hyp),
    ]:
        models.append(
            _diagnose_model(
                clip_id=args.clip_id,
                model_id=model_id,
                reference=reference,
                hypothesis=hyp,
                baseline_model=baseline_by_model.get(model_id),
            )
        )

    payload = {
        "clip_id": args.clip_id,
        "normalization_version": NORMALIZATION_VERSION,
        "taxonomy_version": TAXONOMY_VERSION,
        "paths": {
            "reference": str(args.reference),
            "scribe": str(args.scribe),
            "whisper": str(args.whisper),
            "baseline_json": str(args.baseline_json),
        },
        "models": models,
        "interpretation": _build_interpretation(models),
        "notes": (
            "Diagnostic only. Does not overwrite results/smoke/ or primary "
            "smoke_pl_basic_v1.json metrics fields. pl_numbers_v1 WER is auxiliary."
        ),
    }

    out_dir = args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "smoke_alignment_pl_basic_v1.json"
    md_path = out_dir / "smoke_error_taxonomy.md"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    md_path.write_text(render_markdown(payload), encoding="utf-8")

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    for m in models:
        print(
            f"{m['model_id']}: mass={m['total_edit_mass']} "
            f"WER={100 * m['wer']:.1f}% "
            f"tags={m['summary']['mass_by_tag']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
