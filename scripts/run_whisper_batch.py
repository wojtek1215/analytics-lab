#!/usr/bin/env python3
"""Run local mlx-whisper over a CV manifest (no ElevenLabs API)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from asr_benchmark.inference.whisper_batch import (  # noqa: E402
    WHISPER_MODEL_REPO,
    load_manifest_rows,
    run_whisper_batch,
    write_batch_summary,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Batch-transcribe Common Voice clips with local Whisper "
            "(mlx-community/whisper-large-v3-turbo). Never calls ElevenLabs."
        )
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data/manifests/cv27_pl_test_speaker_disjoint_v1_qa.csv",
        help="Manifest CSV (qa / pilot / holdout)",
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=ROOT / "data/raw/cv-corpus-27.0-2026-09-11/pl",
        help="Local CV locale directory containing clips/",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results/cv/qa/hypotheses/whisper",
        help="Directory for <clip_id>.txt hypotheses",
    )
    parser.add_argument(
        "--meta-dir",
        type=Path,
        default=ROOT / "results/cv/qa/hypotheses/_meta/whisper",
        help="Directory for per-clip JSON metadata",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=None,
        help="Optional batch summary JSON path (default: <meta-dir>/batch_summary.json)",
    )
    parser.add_argument(
        "--model-repo",
        default=WHISPER_MODEL_REPO,
        help="mlx-whisper HF repo id",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Transcribe at most N clips from the manifest",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve paths and plan work without loading Whisper",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-transcribe even if hypothesis file already exists",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    clips = load_manifest_rows(args.manifest)
    if not args.corpus_dir.is_dir():
        print(f"error: corpus dir not found: {args.corpus_dir}", file=sys.stderr)
        return 1

    summary_path = args.summary or (args.meta_dir / "batch_summary.json")
    summary = run_whisper_batch(
        clips=clips,
        corpus_dir=args.corpus_dir,
        hypothesis_dir=args.output_dir,
        meta_dir=args.meta_dir,
        dry_run=args.dry_run,
        skip_existing=not args.force,
        limit=args.limit,
        model_repo=args.model_repo,
    )
    write_batch_summary(summary_path, summary)

    print(
        f"whisper_batch dry_run={summary['dry_run']} "
        f"requested={summary['n_requested']} ok={summary['n_ok']} "
        f"skipped={summary['n_skipped_existing']} "
        f"missing={summary['n_missing_audio']} error={summary['n_error']}"
    )
    print(f"hypotheses → {args.output_dir}")
    print(f"summary → {summary_path}")
    if summary["n_error"] or summary["n_missing_audio"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
