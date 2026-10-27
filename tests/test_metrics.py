"""Unit tests for WER/CER and corpus aggregation."""

from __future__ import annotations

import pytest

from asr_benchmark.evaluation.metrics import (
    EVALUATION_VERSION,
    ClipMetrics,
    EmptyReferenceError,
    aggregate_corpus,
    compute_metrics,
    compute_wer,
)
from asr_benchmark.evaluation.normalize import (
    NUMBERS_NORMALIZATION_VERSION,
    normalize_pl_basic_v1,
)


def test_punctuation_case_zero_error() -> None:
    m = compute_metrics("„Zażółć gęślą jaźń!”", "zażółć gęślą jaźń")
    assert m.wer == 0.0
    assert m.cer == 0.0
    assert m.substitutions == m.deletions == m.insertions == 0


def test_diacritic_mismatch_is_error() -> None:
    m = compute_metrics("łaska", "laska")
    assert m.wer == 1.0
    assert m.cer > 0.0


def test_substitution() -> None:
    m = compute_metrics("ala ma kota", "ala ma psa")
    assert m.substitutions == 1
    assert m.deletions == 0
    assert m.insertions == 0
    assert m.n_words_ref == 3
    assert m.wer == pytest.approx(1 / 3)


def test_deletion() -> None:
    m = compute_metrics("ala ma kota", "ala kota")
    assert m.deletions == 1
    assert m.substitutions == 0
    assert m.insertions == 0
    assert m.wer == pytest.approx(1 / 3)


def test_insertion() -> None:
    m = compute_metrics("ala ma kota", "ala ma dużego kota")
    assert m.insertions == 1
    assert m.substitutions == 0
    assert m.deletions == 0
    assert m.wer == pytest.approx(1 / 3)


def test_numbers_not_equivalent_in_pl_basic_v1() -> None:
    m = compute_metrics("2026", "dwa tysiące dwudziesty szósty")
    assert m.wer != 0.0
    assert m.wer > 0.0


def test_empty_reference_raises() -> None:
    with pytest.raises(EmptyReferenceError):
        compute_metrics("", "hipoteza")
    with pytest.raises(EmptyReferenceError):
        compute_metrics("!!!", "hipoteza")
    with pytest.raises(EmptyReferenceError):
        compute_wer("", "x")


def test_corpus_aggregation_differs_from_unweighted_mean() -> None:
    # Clip A: 1/1 = 100% WER (short)
    a = compute_metrics("tak", "nie", clip_id="a", model_id="m")
    # Clip B: 0/3 = 0% WER (longer)
    b = compute_metrics("ala ma kota", "ala ma kota", clip_id="b", model_id="m")

    corpus = aggregate_corpus([a, b])
    unweighted_mean = (a.wer + b.wer) / 2
    assert corpus.n_words_ref == 4
    assert corpus.wer == pytest.approx(1 / 4)
    assert corpus.wer != pytest.approx(unweighted_mean)


def test_missing_pair_handled_by_caller_coverage() -> None:
    # Evaluator scores only provided pairs; absence is a reporting concern.
    only = compute_metrics("ala ma kota", "ala ma kota", clip_id="x", model_id="scribe_v2")
    assert only.status == "ok"
    corpus = aggregate_corpus([only])
    assert corpus.n_clips == 1


def test_determinism_of_metrics() -> None:
    ref = "W 2026 roku sztuczna inteligencja."
    hyp = "W dwa tysiące dwudziestym szóstym roku sztuczna inteligencja."
    m1 = compute_metrics(ref, hyp, clip_id="t", model_id="m")
    m2 = compute_metrics(ref, hyp, clip_id="t", model_id="m")
    assert m1 == m2
    assert normalize_pl_basic_v1(ref) == m1.normalized_reference


def test_aggregate_rejects_mixed_evaluation_version() -> None:
    a = compute_metrics("ala ma kota", "ala ma kota", clip_id="a", model_id="m")
    b = compute_metrics("ala ma psa", "ala ma psa", clip_id="b", model_id="m")
    b_mixed = ClipMetrics(
        **{
            **b.to_dict(),
            "evaluation_version": "0.0.0-mixed",
        }
    )
    assert a.evaluation_version == EVALUATION_VERSION
    with pytest.raises(ValueError, match="mixed evaluation versions"):
        aggregate_corpus([a, b_mixed])


def test_aggregate_rejects_mixed_normalization_version() -> None:
    a = compute_metrics("2026", "2026", clip_id="a", model_id="m")
    b = compute_metrics(
        "2026",
        "2026",
        clip_id="b",
        model_id="m",
        normalization_version=NUMBERS_NORMALIZATION_VERSION,
    )
    with pytest.raises(ValueError, match="mixed normalization versions"):
        aggregate_corpus([a, b])


def test_pl_numbers_sensitivity_zero_wer_for_spelled_year() -> None:
    # Sensitivity only — primary scoring remains pl_basic_v1.
    basic = compute_metrics(
        "2026",
        "dwa tysiące dwudziestym szóstym",
        normalization_version="pl_basic_v1",
    )
    numbers = compute_metrics(
        "2026",
        "dwa tysiące dwudziestym szóstym",
        normalization_version=NUMBERS_NORMALIZATION_VERSION,
    )
    assert basic.wer > 0.0
    assert numbers.wer == 0.0
    assert numbers.normalization_version == NUMBERS_NORMALIZATION_VERSION
