#!/usr/bin/env python3
"""Build deterministic Common Voice qa/pilot/holdout manifests (no STT, no API)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from asr_benchmark.sampling.cv_manifest import (  # noqa: E402
    SAMPLE_COUNTS,
    SEED,
    build_manifest,
    write_manifest_artifacts,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Deterministic speaker-disjoint sample from Common Voice test.tsv "
            "(seed default 20261026). Writes JSON/CSV/Markdown under --output-dir."
        )
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=ROOT / "data/raw/cv-corpus-27.0-2026-09-11/pl",
        help="Local CV locale directory containing test.tsv and clips/",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data/manifests",
        help="Directory for manifest artifacts (safe to commit; no audio)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=SEED,
        help=f"RNG seed (default {SEED})",
    )
    parser.add_argument(
        "--qa",
        type=int,
        default=SAMPLE_COUNTS["qa"],
        help="QA split size",
    )
    parser.add_argument(
        "--pilot",
        type=int,
        default=SAMPLE_COUNTS["pilot"],
        help="Pilot split size",
    )
    parser.add_argument(
        "--holdout",
        type=int,
        default=SAMPLE_COUNTS["holdout"],
        help="Holdout split size",
    )
    parser.add_argument(
        "--basename",
        default="cv27_pl_test_speaker_disjoint_v1",
        help="Output filename prefix",
    )
    parser.add_argument(
        "--allow-missing-audio",
        action="store_true",
        help="Do not require clips/<path> to exist (tests / dry metadata only)",
    )
    parser.add_argument(
        "--allow-missing-duration",
        action="store_true",
        help="Do not require positive duration from clip_durations.tsv",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    corpus_dir = args.corpus_dir
    if not corpus_dir.is_dir():
        print(f"error: corpus dir not found: {corpus_dir}", file=sys.stderr)
        return 1

    counts = {"qa": args.qa, "pilot": args.pilot, "holdout": args.holdout}
    manifest = build_manifest(
        corpus_dir=corpus_dir,
        seed=args.seed,
        counts=counts,
        require_audio=not args.allow_missing_audio,
        require_positive_duration=not args.allow_missing_duration,
    )
    paths = write_manifest_artifacts(
        manifest, args.output_dir, basename=args.basename
    )

    stats = manifest["filter_stats"]
    print(f"sampling_protocol={manifest['sampling_protocol']}")
    print(f"seed={manifest['seed']}")
    print(
        f"pool: eligible={stats['eligible']} "
        f"speaker_pool={stats['speaker_pool']} "
        f"audio_missing={stats['audio_missing']}"
    )
    print(
        f"selected: qa={counts['qa']} pilot={counts['pilot']} "
        f"holdout={counts['holdout']}"
    )
    print(f"wrote {paths['json']}")
    print(f"wrote {paths['report']}")
    for key in ("csv_qa", "csv_pilot", "csv_holdout", "all_csv"):
        print(f"wrote {paths[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
