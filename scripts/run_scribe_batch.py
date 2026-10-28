#!/usr/bin/env python3
"""Batch ElevenLabs Scribe v2 over a CV manifest.

Default mode is --dry-run (no API). Paid calls require --i-accept-paid-api.
Never prints the API key.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from asr_benchmark.inference.scribe_batch import (  # noqa: E402
    api_key_is_configured,
    estimate_budget,
    run_scribe_batch,
    write_batch_summary,
)
from asr_benchmark.inference.whisper_batch import load_manifest_rows  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Batch-transcribe Common Voice clips with ElevenLabs scribe_v2. "
            "Default: dry-run only. Live paid requests need --i-accept-paid-api."
        )
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data/manifests/cv27_pl_test_speaker_disjoint_v1_qa.csv",
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=ROOT / "data/raw/cv-corpus-27.0-2026-09-11/pl",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results/cv/qa/hypotheses/scribe",
    )
    parser.add_argument(
        "--meta-dir",
        type=Path,
        default=ROOT / "results/cv/qa/hypotheses/_meta/scribe",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="At most N clips from the manifest",
    )
    parser.add_argument(
        "--max-audio-seconds",
        type=float,
        default=120.0,
        help="Refuse live batch if total manifest duration exceeds this (qa≈53s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Plan only (default). No ElevenLabs requests.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Disable dry-run (still requires --i-accept-paid-api)",
    )
    parser.add_argument(
        "--i-accept-paid-api",
        action="store_true",
        help="Explicit consent for paid ElevenLabs STT calls",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-call API even if hypothesis file exists",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=ROOT / ".env",
        help="Load this env file for ELEVENLABS_API_KEY (never printed)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.env_file.is_file():
        load_dotenv(args.env_file)

    clips = load_manifest_rows(args.manifest)
    if args.limit is not None:
        planned = clips[: args.limit]
    else:
        planned = clips

    budget = estimate_budget(planned)
    print("=== Scribe batch plan ===")
    print(f"manifest: {args.manifest}")
    print(f"clips: {budget['n_clips']}")
    print(
        f"audio: {budget['total_duration_s']}s "
        f"({budget['total_duration_min']} min)"
    )
    print(
        f"estimate (public list): ~${budget['estimate_usd_list_price']} "
        f"or ~{budget['estimate_credits_approx']} credits"
    )
    print(budget["pricing_note"])
    print(f"ELEVENLABS_API_KEY configured: {api_key_is_configured()}")

    dry_run = not args.execute
    if args.execute and not args.i_accept_paid_api:
        print(
            "error: --execute requires --i-accept-paid-api "
            "(refusing paid calls).",
            file=sys.stderr,
        )
        return 1

    if not args.corpus_dir.is_dir():
        print(f"error: corpus dir not found: {args.corpus_dir}", file=sys.stderr)
        return 1

    summary_path = args.summary or (args.meta_dir / "batch_summary.json")
    try:
        summary = run_scribe_batch(
            clips=clips,
            corpus_dir=args.corpus_dir,
            hypothesis_dir=args.output_dir,
            meta_dir=args.meta_dir,
            dry_run=dry_run,
            confirm_paid=args.i_accept_paid_api,
            skip_existing=not args.force,
            limit=args.limit,
            max_audio_seconds=args.max_audio_seconds,
        )
    except (PermissionError, EnvironmentError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    write_batch_summary(summary_path, summary)
    print(
        f"scribe_batch dry_run={summary['dry_run']} api_used={summary['api_used']} "
        f"requested={summary['n_requested']} ok={summary['n_ok']} "
        f"skipped={summary['n_skipped_existing']} "
        f"missing={summary['n_missing_audio']} error={summary['n_error']}"
    )
    print(f"hypotheses → {args.output_dir}")
    print(f"summary → {summary_path}")
    if dry_run:
        print(
            "Next (paid): uv run --env-file .env python scripts/run_scribe_batch.py "
            "--execute --i-accept-paid-api"
        )
    if summary["n_error"] or summary["n_missing_audio"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
