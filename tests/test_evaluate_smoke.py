"""Integration checks for smoke evaluation reporting (offline, no STT)."""

from __future__ import annotations

from pathlib import Path

from asr_benchmark.evaluation.metrics import aggregate_corpus, compute_metrics
from asr_benchmark.evaluation.reporting import (
    build_smoke_payload,
    write_json,
    write_markdown,
)


def test_smoke_report_roundtrip(tmp_path: Path) -> None:
    reference = (
        "W 2026 roku sztuczna inteligencja zmienia sposób, w jaki pracujemy."
    )
    scribe = (
        "W dwa tysiące dwudziestym szóstym roku sztuczna inteligencja "
        "zmienia sposób, w jaki pracujemy."
    )
    whisper = reference

    clips = [
        compute_metrics(reference, scribe, clip_id="test_pl", model_id="scribe_v2"),
        compute_metrics(
            reference, whisper, clip_id="test_pl", model_id="whisper-large-v3-turbo"
        ),
    ]
    corpus = {c.model_id: aggregate_corpus([c]) for c in clips}
    payload = build_smoke_payload(
        clip_id="test_pl", clips=clips, corpus_by_model=corpus
    )

    json_path = tmp_path / "smoke_pl_basic_v1.json"
    md_path = tmp_path / "smoke_comparison.md"
    write_json(json_path, payload)
    write_markdown(md_path, payload)

    assert json_path.is_file()
    md = md_path.read_text(encoding="utf-8")
    assert "pl_basic_v1" in md
    assert "scribe_v2" in md
    assert "whisper-large-v3-turbo" in md
    assert clips[0].wer > clips[1].wer  # number expansion costs Scribe more here
