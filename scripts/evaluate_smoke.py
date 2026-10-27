#!/usr/bin/env python3
"""Offline rescore of saved smoke transcripts (no STT, no API calls)."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from asr_benchmark.evaluation.metrics import (  # noqa: E402
    aggregate_corpus,
    compute_metrics,
)
from asr_benchmark.evaluation.reporting import (  # noqa: E402
    build_smoke_payload,
    write_json,
    write_markdown,
)


def _read_text(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8").strip()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate saved smoke ASR hypotheses against a frozen reference."
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=ROOT / "data/raw/test_pl_reference.txt",
        help="Path to reference transcript",
    )
    parser.add_argument(
        "--scribe",
        type=Path,
        default=ROOT / "results/smoke/scribe.txt",
        help="Path to Scribe hypothesis",
    )
    parser.add_argument(
        "--whisper",
        type=Path,
        default=ROOT / "results/smoke/whisper.txt",
        help="Path to Whisper hypothesis",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/evaluation",
        help="Directory for JSON/Markdown reports",
    )
    parser.add_argument(
        "--clip-id",
        default="test_pl",
        help="Clip identifier used in the report",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    reference = _read_text(args.reference)
    scribe_hyp = _read_text(args.scribe)
    whisper_hyp = _read_text(args.whisper)

    if not reference:
        raise SystemExit(f"empty reference: {args.reference}")

    models = [
        ("scribe_v2", scribe_hyp),
        ("whisper-large-v3-turbo", whisper_hyp),
    ]

    clips = []
    corpus_by_model = {}
    for model_id, hypothesis in models:
        clip = compute_metrics(
            reference,
            hypothesis,
            clip_id=args.clip_id,
            model_id=model_id,
        )
        clips.append(clip)
        corpus_by_model[model_id] = aggregate_corpus([clip])

    payload = build_smoke_payload(
        clip_id=args.clip_id,
        clips=clips,
        corpus_by_model=corpus_by_model,
    )
    payload["reference_sha256"] = _sha256(reference)
    payload["paths"] = {
        "reference": str(args.reference),
        "scribe": str(args.scribe),
        "whisper": str(args.whisper),
    }

    out_dir = args.output
    json_path = out_dir / "smoke_pl_basic_v1.json"
    md_path = out_dir / "smoke_comparison.md"
    write_json(json_path, payload)
    write_markdown(md_path, payload)

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    print(f"reference_sha256={payload['reference_sha256'][:12]}…")
    for clip in clips:
        print(
            f"{clip.model_id}: WER={100 * clip.wer:.1f}% "
            f"CER={100 * clip.cer:.1f}% "
            f"S={clip.substitutions} D={clip.deletions} I={clip.insertions} "
            f"N={clip.n_words_ref}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
