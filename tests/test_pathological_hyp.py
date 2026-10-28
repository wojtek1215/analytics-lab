"""Unit tests for pathological_hyp_v1 auto-flag rules."""

from __future__ import annotations

from asr_benchmark.evaluation.pathological_hyp import (
    PATHOLOGICAL_HYP_VERSION,
    flag_pathological_hypothesis,
)


def test_repetition_loop_czesc() -> None:
    flag = flag_pathological_hypothesis(
        "Cześć! Cześć! Cześć! Cześć!",
        reference="Chciałbym kiedyś zostać pilotem.",
    )
    assert flag.flagged
    assert "repetition_loop" in flag.reasons
    assert flag.rule_version == PATHOLOGICAL_HYP_VERSION


def test_unexpected_script_mixed() -> None:
    flag = flag_pathological_hypothesis(
        "Jecha od tego logicznego ze şu",
        reference="Chciałbym kiedyś zostać pilotem.",
    )
    assert flag.flagged
    assert "unexpected_script" in flag.reasons


def test_hangul_flagged() -> None:
    flag = flag_pathological_hypothesis("Naw польз PRE 되면", reference="x" * 20)
    assert flag.flagged
    assert "unexpected_script" in flag.reasons


def test_normal_polish_not_flagged() -> None:
    flag = flag_pathological_hypothesis(
        "Chciałbym kiedyś zostać pilotem.",
        reference="Chciałbym kiedyś zostać pilotem.",
    )
    assert not flag.flagged
    assert flag.reasons == ()


def test_hard_lexicon_error_not_flagged() -> None:
    """Content errors without loops/scripts must stay unflagged."""
    flag = flag_pathological_hypothesis(
        "Urząd w kanali jednostronny, wspomnienia imieniem Kościoława "
        "wbrew wcześniejszym umowom.",
        reference=(
            "Rząd w Hanoi jednostronnie dysponuje mieniem kościoła "
            "wbrew wcześniejszym umowom"
        ),
    )
    assert not flag.flagged


def test_scribe_near_miss_not_flagged() -> None:
    flag = flag_pathological_hypothesis(
        "Chciałbym kiedyś zatańczyć z Piotrem.",
        reference="Chciałbym kiedyś zostać pilotem.",
    )
    assert not flag.flagged


def test_extreme_length_too_short() -> None:
    ref = "Rząd w Hanoi jednostronnie dysponuje mieniem kościoła."
    flag = flag_pathological_hypothesis("x", reference=ref)
    assert flag.flagged
    assert "extreme_length" in flag.reasons


def test_short_ref_skips_length_rule() -> None:
    flag = flag_pathological_hypothesis("hi", reference="Ala ma.")
    assert not flag.flagged
