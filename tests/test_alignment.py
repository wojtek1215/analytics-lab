"""Tests for jiwer alignment edit-mass consistency."""

from __future__ import annotations

from pathlib import Path

import pytest

from asr_benchmark.evaluation.alignment import (
    align_words,
    assert_alignment_matches_counts,
)
from asr_benchmark.evaluation.metrics import compute_metrics

ROOT = Path(__file__).resolve().parents[1]


def test_substitution_chunk_mass() -> None:
    al = align_words("ala ma kota", "ala ma psa")
    assert al.substitutions == 1
    assert al.total_edit_mass == 1
    assert sum(op.edit_mass for op in al.ops) == 1
    assert al.ops[0].op == "substitute"
    assert al.ops[0].ref_tokens == ("kota",)
    assert al.ops[0].hyp_tokens == ("psa",)


def test_deletion_and_insertion_mass() -> None:
    deleted = align_words("ala ma kota", "ala kota")
    assert deleted.deletions == 1
    assert deleted.ops[0].op == "delete"
    assert deleted.total_edit_mass == 1

    inserted = align_words("ala ma kota", "ala ma dużego kota")
    assert inserted.insertions == 1
    assert inserted.ops[0].op == "insert"
    assert inserted.total_edit_mass == 1


def test_alignment_matches_compute_metrics() -> None:
    ref = "W 2026 roku sztuczna inteligencja."
    hyp = "W dwa tysiące dwudziestym szóstym roku sztuczna inteligencja."
    m = compute_metrics(ref, hyp)
    al = align_words(ref, hyp)
    assert_alignment_matches_counts(
        al,
        substitutions=m.substitutions,
        deletions=m.deletions,
        insertions=m.insertions,
        n_words_ref=m.n_words_ref,
        wer=m.wer,
    )


def test_smoke_alignment_matches_saved_metrics() -> None:
    ref_path = ROOT / "data/raw/test_pl_reference.txt"
    scribe_path = ROOT / "results/smoke/scribe.txt"
    whisper_path = ROOT / "results/smoke/whisper.txt"
    if not ref_path.is_file() or not scribe_path.is_file() or not whisper_path.is_file():
        pytest.skip("smoke artifacts not present")

    ref = ref_path.read_text(encoding="utf-8").strip()
    for model_id, path in [
        ("scribe_v2", scribe_path),
        ("whisper-large-v3-turbo", whisper_path),
    ]:
        hyp = path.read_text(encoding="utf-8").strip()
        m = compute_metrics(ref, hyp, model_id=model_id)
        al = align_words(ref, hyp)
        assert_alignment_matches_counts(
            al,
            substitutions=m.substitutions,
            deletions=m.deletions,
            insertions=m.insertions,
            n_words_ref=m.n_words_ref,
            wer=m.wer,
        )
        assert al.total_edit_mass == m.substitutions + m.deletions + m.insertions
