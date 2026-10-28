"""Batch ElevenLabs Scribe v2 over a CV manifest (paid API; gated by explicit confirm)."""

from __future__ import annotations

import json
import mimetypes
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from asr_benchmark.inference.whisper_batch import (
    ManifestClip,
    public_path,
    resolve_audio_path,
)

SCRIBE_MODEL_ID = "scribe_v2"
SCRIBE_LANGUAGE = "pl"
SCRIBE_ENDPOINT = "https://api.elevenlabs.io/v1/speech-to-text"
# Public list prices (see ElevenLabs pricing pages). Not an account balance.
PUBLIC_USD_PER_AUDIO_HOUR = 0.22
PUBLIC_CREDITS_PER_AUDIO_MINUTE = 330

TranscribeFn = Callable[[Path, str], dict[str, Any]]


def api_key_is_configured() -> bool:
    """True if ELEVENLABS_API_KEY is non-empty. Never returns the secret."""
    value = os.getenv("ELEVENLABS_API_KEY")
    return bool(value and value.strip())


def estimate_budget(clips: Sequence[ManifestClip]) -> dict[str, Any]:
    """Estimate cost from manifest durations + public list prices (not billing truth)."""
    durations = [c.duration_ms for c in clips if c.duration_ms is not None]
    total_ms = sum(durations) if durations else 0
    total_s = total_ms / 1000.0
    total_min = total_s / 60.0
    total_h = total_s / 3600.0
    return {
        "n_clips": len(clips),
        "n_with_duration": len(durations),
        "total_duration_ms": total_ms,
        "total_duration_s": round(total_s, 3),
        "total_duration_min": round(total_min, 4),
        "estimate_usd_list_price": round(total_h * PUBLIC_USD_PER_AUDIO_HOUR, 4),
        "estimate_credits_approx": round(total_min * PUBLIC_CREDITS_PER_AUDIO_MINUTE, 1),
        "pricing_note": (
            f"Rough public-list estimate only: "
            f"${PUBLIC_USD_PER_AUDIO_HOUR}/audio-hour API and/or "
            f"~{PUBLIC_CREDITS_PER_AUDIO_MINUTE} credits/min in-app STT. "
            "Actual plan, promotions, and metering may differ; check your account."
        ),
        "source_urls": [
            "https://elevenlabs.io/pricing/api",
            "https://elevenlabs.io/pricing",
        ],
    }


def _guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    if mime:
        return mime
    if path.suffix.lower() == ".mp3":
        return "audio/mpeg"
    if path.suffix.lower() in {".m4a", ".mp4"}:
        return "audio/mp4"
    return "application/octet-stream"


def default_scribe_transcribe(audio_path: Path, api_key: str) -> dict[str, Any]:
    """POST multipart to ElevenLabs STT; returns JSON body (no key logged)."""
    import requests

    mime = _guess_mime(audio_path)
    with audio_path.open("rb") as handle:
        files = {"file": (audio_path.name, handle, mime)}
        data = {
            "model_id": SCRIBE_MODEL_ID,
            "language_code": SCRIBE_LANGUAGE,
            "tag_audio_events": "false",
        }
        headers = {"xi-api-key": api_key}
        response = requests.post(
            SCRIBE_ENDPOINT,
            headers=headers,
            data=data,
            files=files,
            timeout=120,
        )
    if response.status_code >= 400:
        # Do not include response headers (may echo auth). Body may be useful; truncate.
        body = response.text[:500]
        raise RuntimeError(
            f"ElevenLabs STT HTTP {response.status_code}: {body}"
        )
    payload = response.json()
    if not isinstance(payload, dict):
        raise TypeError(f"unexpected JSON type: {type(payload)!r}")
    return payload


def run_scribe_batch(
    *,
    clips: Sequence[ManifestClip],
    corpus_dir: Path,
    hypothesis_dir: Path,
    meta_dir: Path,
    dry_run: bool = True,
    confirm_paid: bool = False,
    skip_existing: bool = True,
    limit: int | None = None,
    max_audio_seconds: float | None = 120.0,
    transcribe_fn: TranscribeFn | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """
    Transcribe manifest clips with Scribe v2.

    Live paid calls require ``dry_run=False`` and ``confirm_paid=True``.
    """
    hypothesis_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    selected = list(clips[:limit] if limit is not None else clips)
    budget = estimate_budget(selected)
    started = datetime.now(timezone.utc).isoformat()

    if not dry_run and not confirm_paid:
        raise PermissionError(
            "Refusing paid ElevenLabs calls without confirm_paid=True "
            "(pass --i-accept-paid-api on the CLI)."
        )

    if not dry_run:
        key = api_key if api_key is not None else os.getenv("ELEVENLABS_API_KEY")
        if not key or not str(key).strip():
            raise EnvironmentError(
                "ELEVENLABS_API_KEY is not set (load via uv run --env-file .env …)."
            )
        api_key = str(key).strip()
        if max_audio_seconds is not None:
            total_s = budget["total_duration_s"]
            if total_s > max_audio_seconds:
                raise PermissionError(
                    f"Batch duration {total_s}s exceeds --max-audio-seconds "
                    f"{max_audio_seconds}. Raise the limit explicitly if intended."
                )
    else:
        api_key = None

    records: list[dict[str, Any]] = []
    for clip in selected:
        hyp_path = hypothesis_dir / f"{clip.clip_id}.txt"
        meta_path = meta_dir / f"{clip.clip_id}.json"
        try:
            audio_path = resolve_audio_path(corpus_dir, clip)
        except FileNotFoundError as exc:
            rec = {
                "clip_id": clip.clip_id,
                "status": "missing_audio",
                "error": str(exc),
                "hypothesis_path": public_path(hyp_path),
            }
            records.append(rec)
            meta_path.write_text(
                json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            continue

        if skip_existing and hyp_path.is_file() and hyp_path.stat().st_size > 0:
            records.append(
                {
                    "clip_id": clip.clip_id,
                    "status": "skipped_existing",
                    "audio_path": public_path(audio_path),
                    "hypothesis_path": public_path(hyp_path),
                }
            )
            continue

        if dry_run:
            records.append(
                {
                    "clip_id": clip.clip_id,
                    "status": "dry_run",
                    "audio_path": public_path(audio_path),
                    "hypothesis_path": public_path(hyp_path),
                    "duration_ms": clip.duration_ms,
                }
            )
            continue

        assert api_key is not None
        fn = transcribe_fn or default_scribe_transcribe
        t0 = time.perf_counter()
        try:
            payload = fn(audio_path, api_key)
            text = str(payload.get("text", "")).strip()
            latency_s = time.perf_counter() - t0
            hyp_path.write_text(text + ("\n" if text else ""), encoding="utf-8")
            # Persist only non-secret operational fields (never API key / full raw dump).
            meta = {
                "clip_id": clip.clip_id,
                "split": clip.split,
                "status": "ok",
                "model_id": SCRIBE_MODEL_ID,
                "language_code": SCRIBE_LANGUAGE,
                "endpoint": SCRIBE_ENDPOINT,
                "tag_audio_events": False,
                "audio_path": public_path(audio_path),
                "audio_relative": clip.audio_relative or f"clips/{clip.path}",
                "duration_ms_manifest": clip.duration_ms,
                "latency_s": round(latency_s, 3),
                "hypothesis_path": public_path(hyp_path),
                "hypothesis_chars": len(text),
                "request_id": payload.get("request_id") or payload.get("transcription_id"),
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "api_used": True,
            }
            meta_path.write_text(
                json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            records.append({**meta, "status": "ok"})
        except Exception as exc:  # noqa: BLE001
            latency_s = time.perf_counter() - t0
            meta = {
                "clip_id": clip.clip_id,
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
                "audio_path": public_path(audio_path),
                "latency_s": round(latency_s, 3),
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "api_used": True,
            }
            meta_path.write_text(
                json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            records.append(meta)

    summary: dict[str, Any] = {
        "batch_started_utc": started,
        "batch_finished_utc": datetime.now(timezone.utc).isoformat(),
        "model_id": SCRIBE_MODEL_ID,
        "language_code": SCRIBE_LANGUAGE,
        "endpoint": SCRIBE_ENDPOINT,
        "corpus_dir": public_path(corpus_dir),
        "hypothesis_dir": public_path(hypothesis_dir),
        "meta_dir": public_path(meta_dir),
        "dry_run": dry_run,
        "confirm_paid": confirm_paid,
        "skip_existing": skip_existing,
        "max_audio_seconds": max_audio_seconds,
        "api_key_configured": api_key_is_configured(),
        "budget_estimate": budget,
        "n_requested": len(selected),
        "n_ok": sum(1 for r in records if r.get("status") == "ok"),
        "n_skipped_existing": sum(
            1 for r in records if r.get("status") == "skipped_existing"
        ),
        "n_dry_run": sum(1 for r in records if r.get("status") == "dry_run"),
        "n_missing_audio": sum(1 for r in records if r.get("status") == "missing_audio"),
        "n_error": sum(1 for r in records if r.get("status") == "error"),
        "api_used": (not dry_run),
        "clips": records,
    }
    return summary


def write_batch_summary(path: Path, summary: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
