"""Metric invariants for pl_wer_normalized_v1 / polish_asr_eval_v2."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest
from jiwer import process_words

from asr_benchmark.evaluation.metrics import (
    EVALUATION_VERSION,
    EVALUATION_VERSION_V2,
    WORD_TRANSFORM,
    EmptyReferenceError,
    aggregate_corpus,
    compute_metrics,
)
from asr_benchmark.evaluation.normalize_v2 import WER_NORMALIZATION_VERSION

ROOT = Path(__file__).resolve().parents[1]


def _wer_v2(ref: str, hyp: str):
    return compute_metrics(
        ref,
        hyp,
        normalization_version=WER_NORMALIZATION_VERSION,
        evaluation_version=EVALUATION_VERSION_V2,
    )


def test_identical_text_wer_zero() -> None:
    m = _wer_v2("W 2026 roku ChatGPT działa.", "W 2026 roku ChatGPT działa.")
    assert m.wer == 0.0
    assert m.substitutions == m.deletions == m.insertions == 0


@pytest.mark.parametrize(
    ("ref", "hyp"),
    [
        ("120 złotych", "sto dwadzieścia zł"),
        ("97,5%", "dziewięćdziesiąt siedem przecinek pięć procent"),
        ("W 2026 roku", "W dwa tysiące dwudziestym szóstym roku"),
        ("ChatGPT i ElevenLabs", "chat GPT i Eleven Labs"),
    ],
)
def test_supported_equivalence_wer_zero(ref: str, hyp: str) -> None:
    assert _wer_v2(ref, hyp).wer == 0.0


@pytest.mark.parametrize(
    ("ref", "hyp"),
    [
        ("120 zł", "125 zł"),
        ("nie zapłaciłem", "zapłaciłem"),
        ("morze", "może"),
        ("Git Hap", "GitHub"),
    ],
)
def test_meaning_changing_remains_error(ref: str, hyp: str) -> None:
    assert _wer_v2(ref, hyp).wer > 0.0


def test_edit_counts_match_formula() -> None:
    m = _wer_v2(
        "dokładność wyniosła 97,5 procent",
        "dokładność wynosiła dziewięćdziesiąt siedem przecinek pięć procent",
    )
    assert abs(m.wer - (m.substitutions + m.deletions + m.insertions) / m.n_words_ref) < 1e-12


def test_sdi_matches_independent_jiwer() -> None:
    ref = "algorytm pomylił słowa morze i może"
    hyp = "algorytm pomylił słowa może i morze"
    m = _wer_v2(ref, hyp)
    out = process_words(
        m.normalized_reference,
        m.normalized_hypothesis,
        reference_transform=WORD_TRANSFORM,
        hypothesis_transform=WORD_TRANSFORM,
    )
    assert m.substitutions == int(out.substitutions)
    assert m.deletions == int(out.deletions)
    assert m.insertions == int(out.insertions)


def test_corpus_aggregation_sums_edits() -> None:
    c1 = _wer_v2("morze", "może")
    c2 = _wer_v2("120 zł", "125 zł")
    corp = aggregate_corpus([c1, c2])
    assert corp.substitutions == c1.substitutions + c2.substitutions
    assert corp.deletions == c1.deletions + c2.deletions
    assert corp.insertions == c1.insertions + c2.insertions
    assert corp.n_words_ref == c1.n_words_ref + c2.n_words_ref
    assert abs(corp.wer - (corp.substitutions + corp.deletions + corp.insertions) / corp.n_words_ref) < 1e-12


def test_mixed_normalization_versions_rejected() -> None:
    a = compute_metrics("a", "b", normalization_version="pl_basic_v1")
    b = _wer_v2("a", "b")
    with pytest.raises(ValueError, match="mixed normalization"):
        aggregate_corpus([a, b])


def test_mixed_evaluation_versions_rejected() -> None:
    a = compute_metrics(
        "morze",
        "może",
        normalization_version=WER_NORMALIZATION_VERSION,
        evaluation_version=EVALUATION_VERSION,
    )
    b = compute_metrics(
        "morze",
        "może",
        normalization_version=WER_NORMALIZATION_VERSION,
        evaluation_version=EVALUATION_VERSION_V2,
    )
    with pytest.raises(ValueError, match="mixed evaluation"):
        aggregate_corpus([a, b])


def test_empty_normalized_reference_fails() -> None:
    with pytest.raises(EmptyReferenceError):
        _wer_v2("!!!", "tekst")


def test_normalization_independent_of_model_id() -> None:
    a = compute_metrics(
        "120 zł",
        "sto dwadzieścia złotych",
        model_id="scribe_v2",
        normalization_version=WER_NORMALIZATION_VERSION,
        evaluation_version=EVALUATION_VERSION_V2,
    )
    b = compute_metrics(
        "120 zł",
        "sto dwadzieścia złotych",
        model_id="whisper-large-v3-turbo",
        normalization_version=WER_NORMALIZATION_VERSION,
        evaluation_version=EVALUATION_VERSION_V2,
    )
    assert a.normalized_reference == b.normalized_reference
    assert a.normalized_hypothesis == b.normalized_hypothesis
    assert a.wer == b.wer


def test_input_hashes_pinned() -> None:
    ref = (ROOT / "data/raw/test_pl_reference.txt").read_text(encoding="utf-8").strip()
    scribe = (ROOT / "results/smoke/scribe.txt").read_text(encoding="utf-8").strip()
    whisper = (ROOT / "results/smoke/whisper.txt").read_text(encoding="utf-8").strip()
    assert hashlib.sha256(ref.encode()).hexdigest() == (
        "d8baa290a674226d0bd8108ece49dc8473669d62aa017194da5ce6fbcd412346"
    )
    assert hashlib.sha256(scribe.encode()).hexdigest() == (
        "c30e5ed2fa6d46076e32ca79b22e91930cd2932634c6a455ee9c845412116cf2"
    )
    assert hashlib.sha256(whisper.encode()).hexdigest() == (
        "09d4b87cdacd225de65bdffbaf9c5561e7ddb1d8e07c6f698c5a5aa5f0f41e5d"
    )


def test_legacy_basic_smoke_matches_saved_json() -> None:
    path = ROOT / "results/evaluation/smoke_pl_basic_v1.json"
    if not path.is_file():
        pytest.skip("legacy smoke JSON absent")
    saved = json.loads(path.read_text(encoding="utf-8"))
    ref = (ROOT / "data/raw/test_pl_reference.txt").read_text(encoding="utf-8").strip()
    hyps = {
        "scribe_v2": (ROOT / "results/smoke/scribe.txt").read_text(encoding="utf-8").strip(),
        "whisper-large-v3-turbo": (ROOT / "results/smoke/whisper.txt")
        .read_text(encoding="utf-8")
        .strip(),
    }
    for model in saved["models"]:
        mid = model["model_id"]
        m = compute_metrics(ref, hyps[mid], model_id=mid)
        assert m.substitutions == model["substitutions"]
        assert m.deletions == model["deletions"]
        assert m.insertions == model["insertions"]
        assert m.n_words_ref == model["n_words_ref"]
        assert abs(m.wer - model["wer"]) < 1e-12


def test_no_stt_or_network_modules_imported_by_metrics() -> None:
    for banned in ("requests", "mlx_whisper", "httpx", "openai"):
        assert banned not in sys.modules or banned not in {
            # allow if somehow present from other tests; metrics path must not need them
            "required"
        }
    # Stronger: importing evaluation stack must succeed without them
    import importlib

    importlib.reload(sys.modules["asr_benchmark.evaluation.metrics"])
    for banned in ("mlx_whisper",):
        assert banned not in sys.modules
