"""Batch local Whisper (mlx-whisper) over a CV manifest — no ElevenLabs API."""

from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

WHISPER_MODEL_REPO = "mlx-community/whisper-large-v3-turbo"
WHISPER_MODEL_ID = "whisper-large-v3-turbo"
WHISPER_LANGUAGE = "pl"


@dataclass(frozen=True, slots=True)
class ManifestClip:
    clip_id: str
    path: str
    audio_relative: str
    sentence: str
    split: str
    duration_ms: int | None


TranscribeFn = Callable[[Path], dict[str, Any]]


def load_manifest_rows(manifest_csv: Path) -> list[ManifestClip]:
    if not manifest_csv.is_file():
        raise FileNotFoundError(manifest_csv)
    with manifest_csv.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"clip_id", "path", "audio_relative", "sentence", "split"}
        if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
            raise ValueError(
                f"{manifest_csv} missing columns {sorted(required)}; "
                f"got {reader.fieldnames!r}"
            )
        out: list[ManifestClip] = []
        for row in reader:
            raw_dur = (row.get("duration_ms") or "").strip()
            duration_ms = int(raw_dur) if raw_dur else None
            out.append(
                ManifestClip(
                    clip_id=(row["clip_id"] or "").strip(),
                    path=(row["path"] or "").strip(),
                    audio_relative=(row["audio_relative"] or "").strip(),
                    sentence=(row["sentence"] or "").strip(),
                    split=(row["split"] or "").strip(),
                    duration_ms=duration_ms,
                )
            )
    return out


def resolve_audio_path(corpus_dir: Path, clip: ManifestClip) -> Path:
    rel = clip.audio_relative
    if rel:
        candidate = corpus_dir / rel
        if candidate.is_file():
            return candidate
    if clip.path:
        candidate = corpus_dir / "clips" / clip.path
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"audio not found for clip_id={clip.clip_id!r} under {corpus_dir}"
    )


def public_path(path: Path, *, root: Path | None = None) -> str:
    """Prefer repo-relative POSIX paths in published metadata (no home prefixes)."""
    root = (root or Path.cwd()).resolve()
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.name


def default_mlx_transcribe(audio_path: Path) -> dict[str, Any]:
    import mlx_whisper

    result = mlx_whisper.transcribe(
        str(audio_path),
        path_or_hf_repo=WHISPER_MODEL_REPO,
        language=WHISPER_LANGUAGE,
        verbose=False,
    )
    if not isinstance(result, dict):
        raise TypeError(f"unexpected mlx_whisper return type: {type(result)!r}")
    return result


def run_whisper_batch(
    *,
    clips: Sequence[ManifestClip],
    corpus_dir: Path,
    hypothesis_dir: Path,
    meta_dir: Path,
    dry_run: bool = False,
    skip_existing: bool = True,
    limit: int | None = None,
    transcribe_fn: TranscribeFn | None = None,
    model_repo: str = WHISPER_MODEL_REPO,
    model_id: str = WHISPER_MODEL_ID,
) -> dict[str, Any]:
    """Transcribe manifest clips; write ``<clip_id>.txt`` and per-clip meta JSON."""
    hypothesis_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    selected = list(clips[:limit] if limit is not None else clips)
    records: list[dict[str, Any]] = []
    started = datetime.now(timezone.utc).isoformat()

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
                    "meta_path": public_path(meta_path),
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

        fn = transcribe_fn or default_mlx_transcribe
        t0 = time.perf_counter()
        try:
            result = fn(audio_path)
            text = str(result.get("text", "")).strip()
            latency_s = time.perf_counter() - t0
            hyp_path.write_text(text + ("\n" if text else ""), encoding="utf-8")
            meta = {
                "clip_id": clip.clip_id,
                "split": clip.split,
                "status": "ok",
                "model_id": model_id,
                "model_repo": model_repo,
                "language": WHISPER_LANGUAGE,
                "audio_path": public_path(audio_path),
                "audio_relative": clip.audio_relative or f"clips/{clip.path}",
                "duration_ms_manifest": clip.duration_ms,
                "latency_s": round(latency_s, 3),
                "hypothesis_path": public_path(hyp_path),
                "hypothesis_chars": len(text),
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "api_used": False,
            }
            meta_path.write_text(
                json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            records.append({**meta, "status": "ok"})
        except Exception as exc:  # noqa: BLE001 — batch must continue
            latency_s = time.perf_counter() - t0
            meta = {
                "clip_id": clip.clip_id,
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
                "audio_path": public_path(audio_path),
                "latency_s": round(latency_s, 3),
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "api_used": False,
            }
            meta_path.write_text(
                json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            records.append(meta)

    summary = {
        "batch_started_utc": started,
        "batch_finished_utc": datetime.now(timezone.utc).isoformat(),
        "model_id": model_id,
        "model_repo": model_repo,
        "language": WHISPER_LANGUAGE,
        "corpus_dir": public_path(corpus_dir),
        "hypothesis_dir": public_path(hypothesis_dir),
        "meta_dir": public_path(meta_dir),
        "dry_run": dry_run,
        "skip_existing": skip_existing,
        "n_requested": len(selected),
        "n_ok": sum(1 for r in records if r.get("status") == "ok"),
        "n_skipped_existing": sum(
            1 for r in records if r.get("status") == "skipped_existing"
        ),
        "n_dry_run": sum(1 for r in records if r.get("status") == "dry_run"),
        "n_missing_audio": sum(1 for r in records if r.get("status") == "missing_audio"),
        "n_error": sum(1 for r in records if r.get("status") == "error"),
        "api_used": False,
        "clips": records,
    }
    return summary


def write_batch_summary(path: Path, summary: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
