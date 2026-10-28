"""Offline cohort scoring tests (fixture texts; no STT/API)."""

from __future__ import annotations

import csv
from pathlib import Path

from asr_benchmark.evaluation.cohort import evaluate_manifest_cohort


def test_evaluate_mini_cohort(tmp_path: Path) -> None:
    manifest = tmp_path / "qa.csv"
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
                "clip_id": "clip_a",
                "path": "a.mp3",
                "audio_relative": "clips/a.mp3",
                "sentence": "Wszystko bierze dosłownie.",
                "duration_ms": "1000",
            }
        )
        writer.writerow(
            {
                "split": "qa",
                "clip_id": "clip_b",
                "path": "b.mp3",
                "audio_relative": "clips/b.mp3",
                "sentence": "Ala ma kota.",
                "duration_ms": "1000",
            }
        )

    cohort = tmp_path / "qa"
    scribe = cohort / "hypotheses" / "scribe"
    whisper = cohort / "hypotheses" / "whisper"
    scribe.mkdir(parents=True)
    whisper.mkdir(parents=True)
    (scribe / "clip_a.txt").write_text("Wszystko bierze dosłownie.\n", encoding="utf-8")
    (whisper / "clip_a.txt").write_text("Wszystko bierze do słowa.\n", encoding="utf-8")
    (scribe / "clip_b.txt").write_text("Ala ma kota.\n", encoding="utf-8")
    (whisper / "clip_b.txt").write_text("Ala ma kota.\n", encoding="utf-8")

    payload, paths = evaluate_manifest_cohort(
        manifest=manifest,
        cohort_dir=cohort,
        cohort_id="mini_qa",
    )
    assert payload["n_missing_hypotheses"] == 0
    assert paths["report"].is_file()
    assert paths["hard_cases_md"].is_file()
    scribe_wer = payload["corpus"]["scribe_v2"]["pl_wer_normalized_v1"]["wer"]
    whisper_wer = payload["corpus"]["whisper-large-v3-turbo"]["pl_wer_normalized_v1"][
        "wer"
    ]
    assert scribe_wer < whisper_wer
