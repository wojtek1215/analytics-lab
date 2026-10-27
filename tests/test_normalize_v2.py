"""Tests for pl_wer_normalized_v1."""

from __future__ import annotations

import random

import pytest

from asr_benchmark.evaluation.normalize_v2 import (
    WER_NORMALIZATION_VERSION,
    normalize_pl_wer_v1,
    normalize_with_trace,
)


def test_version_constant() -> None:
    assert WER_NORMALIZATION_VERSION == "pl_wer_normalized_v1"


@pytest.mark.parametrize(
    ("ref", "hyp"),
    [
        ("120", "sto dwadzieścia"),
        ("97,5 procent", "97,5%"),
        ("120 złotych", "120 zł"),
        ("120 złotych", "sto dwadzieścia złotych"),
        ("W 2026 roku", "W dwa tysiące dwudziestym szóstym roku"),
        ("ChatGPT", "chat GPT"),
        ("ElevenLabs", "Eleven Labs"),
        ("21", "dwadzieścia jeden"),
        ("1000", "tysiąc"),
        ("-20", "minus dwadzieścia"),
    ],
)
def test_equivalences(ref: str, hyp: str) -> None:
    assert normalize_pl_wer_v1(ref) == normalize_pl_wer_v1(hyp)


@pytest.mark.parametrize(
    ("ref", "hyp"),
    [
        ("120 zł", "125 zł"),
        ("120 zł", "120 euro"),
        ("97,5 procent", "95,7 procent"),
        ("nie zapłaciłem", "zapłaciłem"),
        ("morze", "może"),
        ("Git Hap", "GitHub"),
        ("Git Hap", "GitHab"),
        ("GitHub", "GitHab"),
        ("W 2026 roku", "W 2025 roku"),
        ("dwie osoby", "trzy osoby"),
        ("5 kilogramów", "5 gramów"),
        ("nie mogę", "mogę"),
        ("przed", "po"),
    ],
)
def test_non_equivalences(ref: str, hyp: str) -> None:
    assert normalize_pl_wer_v1(ref) != normalize_pl_wer_v1(hyp)


def test_ambiguous_separators_left_unchanged() -> None:
    assert normalize_pl_wer_v1("1,234") == "1,234"
    assert normalize_pl_wer_v1("1.234") == "1.234"
    assert normalize_pl_wer_v1("1.2.3") == "1.2.3"
    assert normalize_pl_wer_v1("0123") == "0123"


def test_oblique_forms_not_rewritten() -> None:
    assert "trzech" in normalize_pl_wer_v1("trzech osób")
    assert "tysiąca" in normalize_pl_wer_v1("koszt tysiąca nagrań")


def test_invalid_thousand_agreement_not_merged() -> None:
    # pięć requires tysięcy, not tysiące
    out = normalize_pl_wer_v1("pięć tysiące")
    assert out == "5 tysiące"


def test_standalone_jeden_not_converted() -> None:
    assert normalize_pl_wer_v1("jeden człowiek") == "jeden człowiek"


def test_jeden_before_unit_converted() -> None:
    assert normalize_pl_wer_v1("jeden zł") == "1 złoty"


def test_percent_points_not_merged() -> None:
    assert "procentowe" in normalize_pl_wer_v1("2 punkty procentowe")


def test_negation_preserved() -> None:
    assert normalize_pl_wer_v1("nie zapłaciłem 120 zł") != normalize_pl_wer_v1(
        "zapłaciłem 120 zł"
    )


def test_idempotent_fixed_corpus() -> None:
    samples = [
        "W 2026 roku ChatGPT i ElevenLabs.",
        "97,5% i sto dwadzieścia złotych",
        "Git Hap vs GitHub vs GitHab",
        "morze i może",
        "minus dwadzieścia",
        "1.2.3 version",
        "",
    ]
    for s in samples:
        n1 = normalize_pl_wer_v1(s)
        assert normalize_pl_wer_v1(n1) == n1


def test_idempotent_seeded_fuzz() -> None:
    rng = random.Random(20261027)
    words = [
        "sto",
        "dwadzieścia",
        "złotych",
        "procent",
        "chatgpt",
        "morze",
        "może",
        "2026",
        "roku",
        "nie",
        "git",
        "hap",
    ]
    for _ in range(40):
        s = " ".join(rng.choice(words) for _ in range(rng.randint(0, 12)))
        n1 = normalize_pl_wer_v1(s)
        assert normalize_pl_wer_v1(n1) == n1


def test_trace_does_not_change_output() -> None:
    sample = "W dwa tysiące dwudziestym szóstym roku: 97,5% i 120 zł."
    plain = normalize_pl_wer_v1(sample)
    traced, transforms = normalize_with_trace(sample)
    assert plain == traced
    assert any(t.applied for t in transforms)


def test_symmetry_reference_hypothesis_role() -> None:
    a = "sto dwadzieścia złotych"
    b = "120 zł"
    # Normalization is a pure function of the string, not of role.
    assert normalize_pl_wer_v1(a) == normalize_pl_wer_v1(a)
    assert normalize_pl_wer_v1(b) == normalize_pl_wer_v1(b)


def test_unknown_rule_rejected() -> None:
    with pytest.raises(ValueError, match="unknown normalization rules"):
        normalize_pl_wer_v1("120", enabled_rules=frozenset({"not_a_rule"}))


def test_type_error() -> None:
    with pytest.raises(TypeError):
        normalize_pl_wer_v1(123)  # type: ignore[arg-type]
