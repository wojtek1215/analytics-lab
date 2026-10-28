#!/usr/bin/env python3
"""Offline cohort scorer: manifest + saved hypotheses → metrics/errors/reports.

No STT and no ElevenLabs API calls.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from asr_benchmark.evaluation.cohort import (  # noqa: E402
    PRIMARY_PROFILE,
    evaluate_manifest_cohort,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score a CV cohort offline (WER/CER + taxonomy_v2)."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data/manifests/cv27_pl_test_speaker_disjoint_v1_qa.csv",
    )
    parser.add_argument(
        "--cohort-dir",
        type=Path,
        default=ROOT / "results/cv/qa",
        help="Directory with hypotheses/ and output metrics|errors|reports",
    )
    parser.add_argument(
        "--cohort-id",
        default="cv27_pl_qa",
        help="Label written into reports",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.manifest.is_file():
        print(f"error: manifest not found: {args.manifest}", file=sys.stderr)
        return 1
    if not args.cohort_dir.is_dir():
        print(f"error: cohort dir not found: {args.cohort_dir}", file=sys.stderr)
        return 1

    payload, paths = evaluate_manifest_cohort(
        manifest=args.manifest,
        cohort_dir=args.cohort_dir,
        cohort_id=args.cohort_id,
    )

    if payload["n_missing_hypotheses"]:
        print(
            f"warning: missing {payload['n_missing_hypotheses']} hypotheses",
            file=sys.stderr,
        )
        for m in payload["missing_hypotheses"]:
            print(f"  - {m['model_id']} {m['clip_id']}", file=sys.stderr)

    print(f"cohort={payload['cohort_id']} primary={PRIMARY_PROFILE}")
    for model_id, profiles in payload["corpus"].items():
        norm = profiles.get(PRIMARY_PROFILE)
        if not norm:
            continue
        print(
            f"  {model_id}: WER={100*norm['wer']:.1f}% "
            f"CER={100*norm['cer']:.1f}% "
            f"S/D/I={norm['substitutions']}/{norm['deletions']}/{norm['insertions']} "
            f"N={norm['n_words_ref']} clips={norm['n_clips']}"
        )
    print(f"wrote {paths['report']}")
    print(f"wrote {paths['hard_cases_md']}")
    print(f"wrote {paths['corpus']}")
    return 1 if payload["n_missing_hypotheses"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
