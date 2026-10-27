"""Unit tests for pl_basic_v1 and pl_numbers_v1 normalization."""

from __future__ import annotations

from asr_benchmark.evaluation.normalize import (
    NORMALIZATION_VERSION,
    NUMBERS_NORMALIZATION_VERSION,
    normalize_pl_basic_v1,
    normalize_pl_numbers_v1,
)


def test_normalization_version_constant() -> None:
    assert NORMALIZATION_VERSION == "pl_basic_v1"
    assert NUMBERS_NORMALIZATION_VERSION == "pl_numbers_v1"


def test_punctuation_and_casefold() -> None:
    assert normalize_pl_basic_v1("„Zażółć gęślą jaźń!”") == "zażółć gęślą jaźń"
    assert normalize_pl_basic_v1("zażółć gęślą jaźń") == "zażółć gęślą jaźń"


def test_diacritics_preserved_semantically() -> None:
    assert normalize_pl_basic_v1("łaska") != normalize_pl_basic_v1("laska")
    assert normalize_pl_basic_v1("łaska") == "łaska"
    assert normalize_pl_basic_v1("laska") == "laska"


def test_digits_preserved_not_spelled() -> None:
    assert "2026" in normalize_pl_basic_v1("W 2026 roku")
    assert normalize_pl_basic_v1("2026") != normalize_pl_basic_v1(
        "dwa tysiące dwudziesty szósty"
    )


def test_decimal_comma_kept_as_one_token_piece() -> None:
    # Decimal comma must not become a word break.
    assert normalize_pl_basic_v1("97,5 procent") == "97,5 procent"


def test_decimal_dot_kept_as_one_token_piece() -> None:
    # ASCII decimal point between digits must also survive punctuation stripping.
    assert normalize_pl_basic_v1("97.5") == "97.5"
    assert normalize_pl_basic_v1("wyniosła 97.5 procent") == "wyniosła 97.5 procent"
    # Sentence-final period after a bare integer is not a decimal separator.
    assert normalize_pl_basic_v1("120.") == "120"


def test_hyphen_and_quotes_become_separators() -> None:
    assert normalize_pl_basic_v1("GPT-6") == "gpt 6"
    assert normalize_pl_basic_v1("„Git Hap”") == "git hap"


def test_whitespace_collapsed() -> None:
    assert normalize_pl_basic_v1("  ala   ma\tkota  ") == "ala ma kota"


def test_determinism() -> None:
    sample = "Czy ChatGPT i ElevenLabs? 97,5% — GitHub."
    assert normalize_pl_basic_v1(sample) == normalize_pl_basic_v1(sample)


def test_pl_numbers_unifies_digit_and_spelled_year() -> None:
    digit = normalize_pl_numbers_v1("W 2026 roku")
    spelled_nom = normalize_pl_numbers_v1("W dwa tysiące dwudziesty szósty roku")
    spelled_loc = normalize_pl_numbers_v1("W dwa tysiące dwudziestym szóstym roku")
    assert digit == "w 2026 roku"
    assert spelled_nom == digit
    assert spelled_loc == digit  # inflection collapsed by design (sensitivity)


def test_pl_numbers_unifies_decimals() -> None:
    assert normalize_pl_numbers_v1("97.5 procent") == "97,5 procent"
    assert normalize_pl_numbers_v1("97,5 procent") == "97,5 procent"
    spelled = normalize_pl_numbers_v1(
        "dziewięćdziesiąt siedem przecinek pięć procent"
    )
    assert spelled == "97,5 procent"


def test_pl_numbers_simple_cardinal() -> None:
    assert normalize_pl_numbers_v1("sto dwadzieścia złotych") == "120 złotych"
    assert normalize_pl_numbers_v1("120 złotych") == "120 złotych"


def test_pl_numbers_does_not_rewrite_non_numbers() -> None:
    assert normalize_pl_numbers_v1("algorytm pomylił słowa morze i może") == (
        "algorytm pomylił słowa morze i może"
    )


def test_pl_numbers_determinism() -> None:
    sample = "W dwa tysiące dwudziestym szóstym roku: 97,5% i sto dwadzieścia."
    assert normalize_pl_numbers_v1(sample) == normalize_pl_numbers_v1(sample)
