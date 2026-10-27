"""Tests for taxonomy_v2 heuristics and reconciliation."""

from __future__ import annotations

from asr_benchmark.evaluation.alignment import align_words
from asr_benchmark.evaluation.normalize_v2 import WER_NORMALIZATION_VERSION
from asr_benchmark.evaluation.taxonomy_v2 import (
    CAT_HALLUCINATION,
    CAT_HOMOPHONE,
    CAT_MORPHOLOGY,
    CAT_PROPER_NAME_RECOGNITION,
    CAT_UNIT_FORMAT,
    IMPACT_CONTENT,
    IMPACT_EQUIVALENT,
    reconcile_taxonomy_with_metrics,
    summarize_tags_v2,
    tag_alignment_v2,
)


def _tag(ref: str, hyp: str):
    al = align_words(ref, hyp, normalization_version=WER_NORMALIZATION_VERSION)
    tagged = tag_alignment_v2(al)
    reconcile_taxonomy_with_metrics(
        tagged,
        substitutions=al.substitutions,
        deletions=al.deletions,
        insertions=al.insertions,
    )
    return al, tagged


def test_mass_reconciliation() -> None:
    al, tagged = _tag(
        "dokładność wyniosła 97,5 procent",
        "dokładność wynosiła 97,5 procent KONIEC!",
    )
    assert sum(t.edit_mass for t in tagged) == al.total_edit_mass
    summary = summarize_tags_v2(tagged)
    assert summary["total_edit_mass"] == al.total_edit_mass


def test_unit_format_equivalent() -> None:
    # Under v2 these should already match after normalization → no edits.
    al, tagged = _tag("120 złotych", "120 zł")
    assert al.total_edit_mass == 0
    assert tagged == []


def test_morphology_wyniosla_wynosila() -> None:
    al, tagged = _tag("wyniosła", "wynosiła")
    assert al.total_edit_mass >= 1
    assert any(t.primary_category == CAT_MORPHOLOGY for t in tagged)


def test_homophone_preserved() -> None:
    al, tagged = _tag("morze", "może")
    assert al.wer > 0
    assert any(t.primary_category == CAT_HOMOPHONE for t in tagged)
    assert all(
        t.semantic_impact == IMPACT_CONTENT
        for t in tagged
        if t.primary_category == CAT_HOMOPHONE
    )


def test_git_hap_not_format_only() -> None:
    al, tagged = _tag("git hap", "github")
    assert al.wer > 0
    assert any(t.primary_category == CAT_PROPER_NAME_RECOGNITION for t in tagged)
    assert all(
        t.semantic_impact != IMPACT_EQUIVALENT
        for t in tagged
        if t.primary_category == CAT_PROPER_NAME_RECOGNITION
    )


def test_trailing_koniec_hallucination() -> None:
    al, tagged = _tag(
        "czy naprawdę możemy ufać automatyzacji",
        "czy naprawdę możemy ufać automatyzacji KONIEC!",
    )
    assert any(t.primary_category == CAT_HALLUCINATION for t in tagged)
    assert any("koniec" in t.hyp_tokens for t in tagged)
