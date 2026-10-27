"""Serialize evaluation results to JSON and Markdown."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from asr_benchmark.evaluation.metrics import ClipMetrics, CorpusMetrics

# Historical smoke notes from the project plan (not produced by this repo).
HISTORICAL_SMOKE = {
    "scribe_v2": {"wer": 0.103, "cer": 0.024},
    "whisper-large-v3-turbo": {"wer": 0.207, "cer": 0.064},
}


def build_smoke_payload(
    *,
    clip_id: str,
    clips: list[ClipMetrics],
    corpus_by_model: dict[str, CorpusMetrics],
) -> dict[str, Any]:
    """Assemble a machine-readable smoke evaluation record."""
    return {
        "clip_id": clip_id,
        "normalization_version": clips[0].normalization_version if clips else None,
        "evaluation_version": clips[0].evaluation_version if clips else None,
        "models": [c.to_dict() for c in clips],
        "corpus_by_model": {k: v.to_dict() for k, v in corpus_by_model.items()},
        "historical_smoke_notes": HISTORICAL_SMOKE,
        "discrepancy_vs_historical": (
            "Recomputed pl_basic_v1 scores are higher than the plan notes "
            "(Scribe ~10.3%/2.4%, Whisper ~20.7%/6.4%). Likely causes: "
            "(1) no scoring code existed in-repo for those notes; "
            "(2) pl_basic_v1 counts digit↔word expansions as errors "
            "(Scribe spells 2026, 97.5, 120 → large S/I and CER insertions); "
            "(3) Whisper still pays for ChatGPT/ElevenLabs tokenization, "
            "homophone/content errors, and the trailing 'KONIEC' insertion. "
            "Historical figures are retained only as notes — not overwritten."
        ),
        "notes": (
            "Historical WER/CER were reported before this evaluator existed; "
            "differences may come from a different normalizer or reference. "
            "Do not overwrite results/smoke/."
        ),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _pct(rate: float) -> str:
    return f"{100.0 * rate:.1f}%"


def render_comparison_markdown(payload: dict[str, Any]) -> str:
    """Human-readable comparison table for the smoke rescore."""
    lines: list[str] = [
        "# Smoke evaluation — `pl_basic_v1`",
        "",
        f"- **clip_id:** `{payload['clip_id']}`",
        f"- **normalization_version:** `{payload['normalization_version']}`",
        f"- **evaluation_version:** `{payload['evaluation_version']}`",
        "",
        "## Scores",
        "",
        "| Model | WER | CER | S | D | I | N_words | N_chars |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for model in payload["models"]:
        lines.append(
            "| {model_id} | {wer} | {cer} | {s} | {d} | {i} | {nw} | {nc} |".format(
                model_id=model["model_id"],
                wer=_pct(model["wer"]),
                cer=_pct(model["cer"]),
                s=model["substitutions"],
                d=model["deletions"],
                i=model["insertions"],
                nw=model["n_words_ref"],
                nc=model["n_chars_ref"],
            )
        )

    lines.extend(
        [
            "",
            "## vs historical notes (plan)",
            "",
            "| Model | Historical WER | Recomputed WER | Historical CER | Recomputed CER |",
            "|---|---:|---:|---:|---:|",
        ]
    )

    hist = payload.get("historical_smoke_notes", {})
    for model in payload["models"]:
        mid = model["model_id"]
        h = hist.get(mid, {})
        lines.append(
            "| {mid} | {hw} | {rw} | {hc} | {rc} |".format(
                mid=mid,
                hw=_pct(h["wer"]) if "wer" in h else "—",
                rw=_pct(model["wer"]),
                hc=_pct(h["cer"]) if "cer" in h else "—",
                rc=_pct(model["cer"]),
            )
        )

    lines.extend(["", "## Normalized texts", ""])
    for model in payload["models"]:
        lines.extend(
            [
                f"### {model['model_id']}",
                "",
                "**Reference (normalized):**",
                "",
                "```",
                model["normalized_reference"],
                "```",
                "",
                "**Hypothesis (normalized):**",
                "",
                "```",
                model["normalized_hypothesis"],
                "```",
                "",
            ]
        )

    discrepancy = payload.get("discrepancy_vs_historical")
    if discrepancy:
        lines.extend(["## Why recomputed ≠ historical", "", discrepancy, ""])

    lines.extend(
        [
            "## Notes",
            "",
            payload.get("notes", ""),
            "",
            "Primary metric: corpus / clip WER after `pl_basic_v1`. "
            "Digit vs spelled-number mismatches count as errors. "
            "Spaces are included in CER. `results/smoke/` was not modified.",
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_comparison_markdown(payload), encoding="utf-8")
