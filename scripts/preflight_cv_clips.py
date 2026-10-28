#!/usr/bin/env python3
"""Automated audio QC for a CV manifest (missing / 0-byte / tiny duration / unreadable).

Does not call ASR APIs. Does not decide ref≠audio (that requires human listen).
See docs/evaluation_protocol.md — Pre-holdout audio QC.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from asr_benchmark.inference.whisper_batch import (  # noqa: E402
    load_manifest_rows,
    public_path,
    resolve_audio_path,
)

DEFAULT_MIN_DURATION_MS = 200
DEFAULT_MIN_BYTES = 1


def ffprobe_ok(path: Path) -> tuple[bool, str]:
    """Return (ok, detail). Uses ffprobe if available; else size-only fallback note."""
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except FileNotFoundError:
        return True, "ffprobe_missing_size_only"
    except subprocess.TimeoutExpired:
        return False, "ffprobe_timeout"
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()[:200]
        return False, f"ffprobe_fail:{err or proc.returncode}"
    return True, "ffprobe_ok"


def check_clip(
    *,
    clip_id: str,
    audio_path: Path,
    duration_ms: int | None,
    min_duration_ms: int,
    min_bytes: int,
) -> list[dict]:
    issues: list[dict] = []
    if not audio_path.is_file():
        issues.append(
            {
                "clip_id": clip_id,
                "reason_id": "corrupt_unreadable",
                "detail": "missing_file",
                "path": public_path(audio_path, root=ROOT),
            }
        )
        return issues

    size = audio_path.stat().st_size
    if size < min_bytes:
        issues.append(
            {
                "clip_id": clip_id,
                "reason_id": "corrupt_unreadable",
                "detail": f"size_bytes={size}",
                "path": public_path(audio_path, root=ROOT),
            }
        )

    if duration_ms is None:
        issues.append(
            {
                "clip_id": clip_id,
                "reason_id": "corrupt_unreadable",
                "detail": "missing_duration_ms",
                "path": public_path(audio_path, root=ROOT),
            }
        )
    elif duration_ms < min_duration_ms:
        issues.append(
            {
                "clip_id": clip_id,
                "reason_id": "silence_or_no_speech",
                "detail": f"duration_ms={duration_ms}<{min_duration_ms}",
                "path": public_path(audio_path, root=ROOT),
                "note": "automated duration gate only; confirm by listen before excluding",
            }
        )

    ok, detail = ffprobe_ok(audio_path)
    if not ok:
        issues.append(
            {
                "clip_id": clip_id,
                "reason_id": "corrupt_unreadable",
                "detail": detail,
                "path": public_path(audio_path, root=ROOT),
            }
        )

    return issues


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data/manifests/cv27_pl_test_speaker_disjoint_v1_holdout.csv",
    )
    p.add_argument(
        "--corpus-dir",
        type=Path,
        default=ROOT / "data/raw/cv-corpus-27.0-2026-09-11/pl",
    )
    p.add_argument("--min-duration-ms", type=int, default=DEFAULT_MIN_DURATION_MS)
    p.add_argument("--min-bytes", type=int, default=DEFAULT_MIN_BYTES)
    p.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional machine-readable report path",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    clips = load_manifest_rows(args.manifest)
    all_issues: list[dict] = []
    for clip in clips:
        try:
            audio = resolve_audio_path(args.corpus_dir, clip)
        except FileNotFoundError as exc:
            all_issues.append(
                {
                    "clip_id": clip.clip_id,
                    "reason_id": "corrupt_unreadable",
                    "detail": str(exc),
                }
            )
            continue
        all_issues.extend(
            check_clip(
                clip_id=clip.clip_id,
                audio_path=audio,
                duration_ms=clip.duration_ms,
                min_duration_ms=args.min_duration_ms,
                min_bytes=args.min_bytes,
            )
        )

    summary = {
        "manifest": public_path(args.manifest, root=ROOT),
        "n_clips": len(clips),
        "n_issue_rows": len(all_issues),
        "n_clips_with_issues": len({i["clip_id"] for i in all_issues}),
        "min_duration_ms": args.min_duration_ms,
        "min_bytes": args.min_bytes,
        "issues": all_issues,
        "note": (
            "Automated suspects only. ref_ne_audio requires human listen. "
            "See docs/evaluation_protocol.md."
        ),
    }

    print(
        f"preflight: clips={summary['n_clips']} "
        f"clips_with_issues={summary['n_clips_with_issues']} "
        f"issue_rows={summary['n_issue_rows']}"
    )
    for row in all_issues:
        print(
            f"  {row['clip_id']}: {row['reason_id']} — {row.get('detail', '')}"
        )
    if not all_issues:
        print("  (no automated issues)")

    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"wrote {public_path(args.json_out, root=ROOT)}")

    return 1 if all_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
