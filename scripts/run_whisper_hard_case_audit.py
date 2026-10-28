#!/usr/bin/env python3
"""Audit-only hard-case re-run for Whisper and/or Scribe (does not touch pilot hypotheses)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
from asr_benchmark.inference.whisper_batch import (  # noqa: E402
    WHISPER_LANGUAGE,
    WHISPER_MODEL_ID,
    WHISPER_MODEL_REPO,
    ManifestClip,
    load_manifest_rows,
    public_path,
    resolve_audio_path,
)

AUDIT_CLIP_HALLUCINATION = "common_voice_pl_25378583"
DEFAULT_MANIFEST = ROOT / "data/manifests/cv27_pl_pilot_hard_case_audit_2.csv"
DEFAULT_CORPUS = ROOT / "data/raw/cv-corpus-27.0-2026-09-11/pl"
DEFAULT_AUDIT_ROOT = ROOT / "results/cv/pilot/audit"

# Variant name -> (decode kwargs beyond language/model/verbose, clip_ids or None=all)
WHISPER_VARIANTS: list[tuple[str, dict[str, Any], frozenset[str] | None]] = [
    ("baseline", {}, None),
    ("temp0", {"temperature": 0.0}, frozenset({AUDIT_CLIP_HALLUCINATION})),
    (
        "no_condition",
        {"condition_on_previous_text": False},
        frozenset({AUDIT_CLIP_HALLUCINATION}),
    ),
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit-only re-transcription of pilot hard cases. "
            "Writes under results/cv/pilot/audit/; never overwrites pilot hypotheses."
        )
    )
    parser.add_argument(
        "--whisper",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run local Whisper variants (default: true)",
    )
    parser.add_argument(
        "--scribe",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Run ElevenLabs Scribe v2 for both clips (paid; needs --i-accept-paid-api)",
    )
    parser.add_argument(
        "--i-accept-paid-api",
        action="store_true",
        help="Explicit consent for paid ElevenLabs STT calls",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=ROOT / ".env",
        help="Load ELEVENLABS_API_KEY from this file (never printed)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=DEFAULT_CORPUS,
    )
    parser.add_argument(
        "--audit-root",
        type=Path,
        default=DEFAULT_AUDIT_ROOT,
    )
    return parser.parse_args(argv)


def mlx_transcribe(audio_path: Path, *, decode_kwargs: dict[str, Any]) -> dict[str, Any]:
    import mlx_whisper

    result = mlx_whisper.transcribe(
        str(audio_path),
        path_or_hf_repo=WHISPER_MODEL_REPO,
        language=WHISPER_LANGUAGE,
        verbose=False,
        **decode_kwargs,
    )
    if not isinstance(result, dict):
        raise TypeError(f"unexpected mlx_whisper return type: {type(result)!r}")
    return result


def run_whisper_variant(
    *,
    name: str,
    decode_kwargs: dict[str, Any],
    clips: list[ManifestClip],
    corpus_dir: Path,
    audit_root: Path,
) -> dict[str, Any]:
    hyp_dir = audit_root / name / "hypotheses"
    meta_dir = audit_root / name / "meta"
    hyp_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    for clip in clips:
        audio_path = resolve_audio_path(corpus_dir, clip)
        hyp_path = hyp_dir / f"{clip.clip_id}.txt"
        meta_path = meta_dir / f"{clip.clip_id}.json"

        t0 = time.perf_counter()
        try:
            result = mlx_transcribe(audio_path, decode_kwargs=decode_kwargs)
            text = str(result.get("text", "")).strip()
            latency_s = time.perf_counter() - t0
            hyp_path.write_text(text + ("\n" if text else ""), encoding="utf-8")
            meta: dict[str, Any] = {
                "clip_id": clip.clip_id,
                "system": "whisper",
                "variant": name,
                "status": "ok",
                "model_id": WHISPER_MODEL_ID,
                "model_repo": WHISPER_MODEL_REPO,
                "language": WHISPER_LANGUAGE,
                "decode_kwargs": decode_kwargs,
                "audio_path": public_path(audio_path, root=ROOT),
                "duration_ms_manifest": clip.duration_ms,
                "latency_s": round(latency_s, 3),
                "hypothesis_path": public_path(hyp_path, root=ROOT),
                "hypothesis_text": text,
                "hypothesis_chars": len(text),
                "reference_sentence": clip.sentence,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "api_used": False,
                "audit_only": True,
            }
            meta_path.write_text(
                json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            records.append(meta)
            print(f"  [whisper/{name}] {clip.clip_id}: {text!r} ({latency_s:.2f}s)")
        except Exception as exc:  # noqa: BLE001 — continue remaining clips
            latency_s = time.perf_counter() - t0
            meta = {
                "clip_id": clip.clip_id,
                "system": "whisper",
                "variant": name,
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
                "decode_kwargs": decode_kwargs,
                "audio_path": public_path(audio_path, root=ROOT),
                "latency_s": round(latency_s, 3),
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "api_used": False,
                "audit_only": True,
            }
            meta_path.write_text(
                json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            records.append(meta)
            print(f"  [whisper/{name}] {clip.clip_id}: ERROR {exc}", file=sys.stderr)

    return {
        "system": "whisper",
        "variant": name,
        "decode_kwargs": decode_kwargs,
        "hypothesis_dir": public_path(hyp_dir, root=ROOT),
        "meta_dir": public_path(meta_dir, root=ROOT),
        "n_ok": sum(1 for r in records if r.get("status") == "ok"),
        "n_error": sum(1 for r in records if r.get("status") == "error"),
        "clips": records,
    }


def run_whisper_audit(
    *,
    clips: list[ManifestClip],
    corpus_dir: Path,
    audit_root: Path,
) -> dict[str, Any]:
    by_id = {c.clip_id: c for c in clips}
    variant_summaries: list[dict[str, Any]] = []
    started = datetime.now(timezone.utc).isoformat()

    for name, decode_kwargs, clip_filter in WHISPER_VARIANTS:
        if clip_filter is None:
            selected = clips
        else:
            missing = sorted(clip_filter - set(by_id))
            if missing:
                raise FileNotFoundError(f"clips missing from manifest: {missing}")
            selected = [c for c in clips if c.clip_id in clip_filter]
            selected = sorted(
                selected,
                key=lambda c: (0 if c.clip_id == AUDIT_CLIP_HALLUCINATION else 1, c.clip_id),
            )
        print(
            f"whisper variant={name} decode={decode_kwargs or '(production defaults)'} "
            f"n={len(selected)}"
        )
        variant_summaries.append(
            run_whisper_variant(
                name=name,
                decode_kwargs=decode_kwargs,
                clips=selected,
                corpus_dir=corpus_dir,
                audit_root=audit_root,
            )
        )

    summary = {
        "batch_started_utc": started,
        "batch_finished_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "audit_only_hard_case_rerun",
        "system": "whisper",
        "does_not_overwrite_pilot_hypotheses": True,
        "model_id": WHISPER_MODEL_ID,
        "model_repo": WHISPER_MODEL_REPO,
        "language": WHISPER_LANGUAGE,
        "api_used": False,
        "variants": variant_summaries,
    }
    path = audit_root / "whisper_batch_summary.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"whisper summary → {public_path(path, root=ROOT)}")
    return summary


def run_scribe_audit(
    *,
    clips: list[ManifestClip],
    corpus_dir: Path,
    audit_root: Path,
    confirm_paid: bool,
) -> dict[str, Any]:
    hyp_dir = audit_root / "scribe" / "hypotheses"
    meta_dir = audit_root / "scribe" / "meta"
    budget = estimate_budget(clips)
    print("=== Scribe audit plan ===")
    print(f"clips: {budget['n_clips']} audio={budget['total_duration_s']}s")
    print(
        f"estimate (public list): ~${budget['estimate_usd_list_price']} "
        f"or ~{budget['estimate_credits_approx']} credits"
    )
    print(f"ELEVENLABS_API_KEY configured: {api_key_is_configured()}")

    summary = run_scribe_batch(
        clips=clips,
        corpus_dir=corpus_dir,
        hypothesis_dir=hyp_dir,
        meta_dir=meta_dir,
        dry_run=False,
        confirm_paid=confirm_paid,
        skip_existing=False,
        max_audio_seconds=60.0,
    )
    summary = {
        **summary,
        "purpose": "audit_only_hard_case_rerun",
        "system": "scribe",
        "does_not_overwrite_pilot_hypotheses": True,
        "audit_only": True,
        "budget_estimate": budget,
    }
    # Attach hypothesis text for easier side-by-side docs
    for rec in summary.get("clips", []):
        if rec.get("status") != "ok":
            continue
        hyp_path = hyp_dir / f"{rec['clip_id']}.txt"
        if hyp_path.is_file():
            rec["hypothesis_text"] = hyp_path.read_text(encoding="utf-8").strip()

    path = audit_root / "scribe_batch_summary.json"
    write_batch_summary(path, summary)
    print(f"scribe summary → {public_path(path, root=ROOT)}")
    for rec in summary.get("clips", []):
        if rec.get("status") == "ok":
            print(f"  [scribe] {rec['clip_id']}: {rec.get('hypothesis_text')!r}")
        else:
            print(f"  [scribe] {rec['clip_id']}: {rec.get('status')} {rec.get('error', '')}")
    return summary


def write_combined_summary(
    audit_root: Path,
    *,
    whisper: dict[str, Any] | None,
    scribe: dict[str, Any] | None,
) -> Path:
    path = audit_root / "batch_summary.json"
    existing: dict[str, Any] = {}
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}

    combined = {
        "purpose": "audit_only_hard_case_rerun",
        "does_not_overwrite_pilot_hypotheses": True,
        "manifest": public_path(DEFAULT_MANIFEST, root=ROOT),
        "corpus_dir": public_path(DEFAULT_CORPUS, root=ROOT),
        "audit_root": public_path(audit_root, root=ROOT),
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "whisper": whisper
        if whisper is not None
        else existing.get("whisper") or existing.get("variants"),
        "scribe": scribe if scribe is not None else existing.get("scribe"),
    }
    # Preserve prior top-level whisper fields if this run was scribe-only and old format
    if whisper is None and "variants" in existing and "whisper" not in existing:
        combined["whisper"] = {
            k: existing[k]
            for k in (
                "batch_started_utc",
                "batch_finished_utc",
                "model_id",
                "model_repo",
                "language",
                "api_used",
                "variants",
            )
            if k in existing
        }
    path.write_text(json.dumps(combined, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"combined summary → {public_path(path, root=ROOT)}")
    return path


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.whisper and not args.scribe:
        print("error: enable at least one of --whisper / --scribe", file=sys.stderr)
        return 1
    if args.scribe and not args.i_accept_paid_api:
        print(
            "error: --scribe requires --i-accept-paid-api (refusing paid calls).",
            file=sys.stderr,
        )
        return 1
    if args.env_file.is_file():
        load_dotenv(args.env_file)

    if not args.manifest.is_file():
        print(f"error: manifest not found: {args.manifest}", file=sys.stderr)
        return 1
    if not args.corpus_dir.is_dir():
        print(f"error: corpus dir not found: {args.corpus_dir}", file=sys.stderr)
        return 1

    clips = load_manifest_rows(args.manifest)
    args.audit_root.mkdir(parents=True, exist_ok=True)
    print(
        f"hard-case audit: {len(clips)} clips → {public_path(args.audit_root, root=ROOT)} "
        f"(whisper={args.whisper} scribe={args.scribe})"
    )

    whisper_summary: dict[str, Any] | None = None
    scribe_summary: dict[str, Any] | None = None
    n_err = 0

    if args.whisper:
        whisper_summary = run_whisper_audit(
            clips=clips,
            corpus_dir=args.corpus_dir,
            audit_root=args.audit_root,
        )
        n_err += sum(v["n_error"] for v in whisper_summary["variants"])

    if args.scribe:
        try:
            scribe_summary = run_scribe_audit(
                clips=clips,
                corpus_dir=args.corpus_dir,
                audit_root=args.audit_root,
                confirm_paid=args.i_accept_paid_api,
            )
        except (PermissionError, EnvironmentError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        n_err += int(scribe_summary.get("n_error", 0)) + int(
            scribe_summary.get("n_missing_audio", 0)
        )

    write_combined_summary(
        args.audit_root, whisper=whisper_summary, scribe=scribe_summary
    )
    return 2 if n_err else 0


if __name__ == "__main__":
    raise SystemExit(main())
