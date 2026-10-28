"""Offline tests for Scribe batch gating and I/O (mocked HTTP; no real API)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from asr_benchmark.inference.scribe_batch import (
    estimate_budget,
    run_scribe_batch,
)
from asr_benchmark.inference.whisper_batch import load_manifest_rows


def _fixture(root: Path) -> tuple[Path, Path]:
    corpus = root / "pl"
    clips = corpus / "clips"
    clips.mkdir(parents=True)
    name = "common_voice_pl_9.mp3"
    (clips / name).write_bytes(b"ID3fake")
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
                "clip_id": "common_voice_pl_9",
                "path": name,
                "audio_relative": f"clips/{name}",
                "sentence": "Test.",
                "duration_ms": "2000",
            }
        )
    return corpus, manifest


def test_estimate_budget(tmp_path: Path) -> None:
    _, manifest = _fixture(tmp_path)
    clips = load_manifest_rows(manifest)
    budget = estimate_budget(clips)
    assert budget["n_clips"] == 1
    assert budget["total_duration_s"] == 2.0
    assert budget["estimate_usd_list_price"] >= 0


def test_refuses_paid_without_confirm(tmp_path: Path) -> None:
    corpus, manifest = _fixture(tmp_path)
    clips = load_manifest_rows(manifest)
    with pytest.raises(PermissionError, match="confirm_paid"):
        run_scribe_batch(
            clips=clips,
            corpus_dir=corpus,
            hypothesis_dir=tmp_path / "hyp",
            meta_dir=tmp_path / "meta",
            dry_run=False,
            confirm_paid=False,
        )


def test_dry_run_and_mocked_paid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    corpus, manifest = _fixture(tmp_path)
    clips = load_manifest_rows(manifest)
    hyp = tmp_path / "hyp"
    meta = tmp_path / "meta"

    dry = run_scribe_batch(
        clips=clips,
        corpus_dir=corpus,
        hypothesis_dir=hyp,
        meta_dir=meta,
        dry_run=True,
    )
    assert dry["api_used"] is False
    assert dry["n_dry_run"] == 1

    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key-not-real")

    def fake(path: Path, api_key: str) -> dict:
        assert api_key == "test-key-not-real"
        assert path.is_file()
        return {"text": "  Scribe text.  ", "request_id": "req_test"}

    live = run_scribe_batch(
        clips=clips,
        corpus_dir=corpus,
        hypothesis_dir=hyp,
        meta_dir=meta,
        dry_run=False,
        confirm_paid=True,
        skip_existing=False,
        max_audio_seconds=60,
        transcribe_fn=fake,
    )
    assert live["api_used"] is True
    assert live["n_ok"] == 1
    assert (hyp / "common_voice_pl_9.txt").read_text(encoding="utf-8").strip() == (
        "Scribe text."
    )
    payload = json.loads((meta / "common_voice_pl_9.json").read_text(encoding="utf-8"))
    assert "xi-api-key" not in json.dumps(payload)
    assert payload["request_id"] == "req_test"


def test_max_audio_seconds_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    corpus, manifest = _fixture(tmp_path)
    clips = load_manifest_rows(manifest)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key-not-real")
    with pytest.raises(PermissionError, match="max-audio-seconds"):
        run_scribe_batch(
            clips=clips,
            corpus_dir=corpus,
            hypothesis_dir=tmp_path / "hyp",
            meta_dir=tmp_path / "meta",
            dry_run=False,
            confirm_paid=True,
            max_audio_seconds=0.5,
            transcribe_fn=lambda *_: {"text": "x"},
        )
