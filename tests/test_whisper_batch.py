"""Offline tests for Whisper batch I/O (mocked transcribe; no MLX required)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from asr_benchmark.inference.whisper_batch import (
    load_manifest_rows,
    resolve_audio_path,
    run_whisper_batch,
    write_batch_summary,
)


def _write_fixture(root: Path) -> tuple[Path, Path]:
    corpus = root / "pl"
    clips_dir = corpus / "clips"
    clips_dir.mkdir(parents=True)
    audio_name = "common_voice_pl_1.mp3"
    (clips_dir / audio_name).write_bytes(b"ID3fake")

    manifest = root / "qa.csv"
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "split",
                "clip_id",
                "path",
                "audio_relative",
                "sentence",
                "duration_ms",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "split": "qa",
                "clip_id": "common_voice_pl_1",
                "path": audio_name,
                "audio_relative": f"clips/{audio_name}",
                "sentence": "Test.",
                "duration_ms": "1000",
            }
        )
    return corpus, manifest


def test_load_and_resolve(tmp_path: Path) -> None:
    corpus, manifest = _write_fixture(tmp_path)
    clips = load_manifest_rows(manifest)
    assert len(clips) == 1
    audio = resolve_audio_path(corpus, clips[0])
    assert audio.is_file()


def test_dry_run_and_mocked_transcribe(tmp_path: Path) -> None:
    corpus, manifest = _write_fixture(tmp_path)
    clips = load_manifest_rows(manifest)
    hyp = tmp_path / "hyp"
    meta = tmp_path / "meta"

    dry = run_whisper_batch(
        clips=clips,
        corpus_dir=corpus,
        hypothesis_dir=hyp,
        meta_dir=meta,
        dry_run=True,
    )
    assert dry["n_dry_run"] == 1
    assert dry["api_used"] is False
    assert not list(hyp.glob("*.txt"))

    def fake_transcribe(path: Path) -> dict:
        assert path.is_file()
        return {"text": "  Hello world.  "}

    summary = run_whisper_batch(
        clips=clips,
        corpus_dir=corpus,
        hypothesis_dir=hyp,
        meta_dir=meta,
        dry_run=False,
        skip_existing=False,
        transcribe_fn=fake_transcribe,
    )
    assert summary["n_ok"] == 1
    text = (hyp / "common_voice_pl_1.txt").read_text(encoding="utf-8").strip()
    assert text == "Hello world."
    meta_payload = json.loads((meta / "common_voice_pl_1.json").read_text(encoding="utf-8"))
    assert meta_payload["status"] == "ok"
    assert meta_payload["api_used"] is False

    skipped = run_whisper_batch(
        clips=clips,
        corpus_dir=corpus,
        hypothesis_dir=hyp,
        meta_dir=meta,
        dry_run=False,
        skip_existing=True,
        transcribe_fn=fake_transcribe,
    )
    assert skipped["n_skipped_existing"] == 1

    summary_path = meta / "batch_summary.json"
    write_batch_summary(summary_path, summary)
    assert summary_path.is_file()
