"""Tests for taxonomy_v0 heuristics."""

from __future__ import annotations

from pathlib import Path

import pytest

from asr_benchmark.evaluation.alignment import align_words
from asr_benchmark.evaluation.taxonomy import (
    TAG_AMBIGUOUS,
    TAG_HOMOPHONE,
    TAG_INSERTION_EXTRA,
    TAG_NUMBER_FORMAT,
    TAG_PROPER_NAME,
    summarize_tags,
    tag_alignment,
)

ROOT = Path(__file__).resolve().parents[1]


def test_number_format_year_span() -> None:
    al = align_words("2026", "dwa tysiące dwudziestym szóstym")
    tagged = tag_alignment(al)
    assert sum(t.edit_mass for t in tagged) == al.total_edit_mass
    assert all(t.tag == TAG_NUMBER_FORMAT for t in tagged)


def test_proper_name_chatgpt_split() -> None:
    al = align_words("czy chatgpt zastąpi", "czy chat gpt zastąpi")
    tagged = tag_alignment(al)
    assert tagged
    assert any(t.tag == TAG_PROPER_NAME for t in tagged)
    assert sum(t.edit_mass for t in tagged) == al.total_edit_mass


def test_homophone_morze_moze() -> None:
    al = align_words("morze", "może")
    tagged = tag_alignment(al)
    assert len(tagged) == 1
    assert tagged[0].tag == TAG_HOMOPHONE
    assert tagged[0].content_impact == "content_changing"


def test_trailing_koniec_insertion() -> None:
    al = align_words(
        "czy naprawdę możemy ufać automatyzacji",
        "czy naprawdę możemy ufać automatyzacji koniec",
    )
    tagged = tag_alignment(al)
    assert any(t.tag == TAG_INSERTION_EXTRA for t in tagged)
    trailing = [t for t in tagged if t.tag == TAG_INSERTION_EXTRA]
    assert trailing
    assert any("hallucination_trailing" in t.notes for t in trailing)


def test_ambiguous_mixed_number_and_lexical() -> None:
    # Morphology + number expansion often lands as mixed / ambiguous.
    al = align_words(
        "wyniosła 97,5 procent",
        "wynosiła dziewięćdziesiąt siedem przecinek pięć procent",
    )
    tagged = tag_alignment(al)
    assert sum(t.edit_mass for t in tagged) == al.total_edit_mass
    tags = {t.tag for t in tagged}
    assert TAG_AMBIGUOUS in tags or TAG_NUMBER_FORMAT in tags


def test_summary_mass_percentages() -> None:
    al = align_words("ala ma kota", "ala ma psa")
    tagged = tag_alignment(al)
    summary = summarize_tags(tagged)
    assert summary["total_edit_mass"] == 1
    assert abs(sum(summary["pct_by_tag"].values()) - 1.0) < 1e-9


def test_smoke_taxonomy_mass_equals_sdi() -> None:
    ref_path = ROOT / "data/raw/test_pl_reference.txt"
    scribe_path = ROOT / "results/smoke/scribe.txt"
    whisper_path = ROOT / "results/smoke/whisper.txt"
    if not ref_path.is_file() or not scribe_path.is_file() or not whisper_path.is_file():
        pytest.skip("smoke artifacts not present")

    ref = ref_path.read_text(encoding="utf-8").strip()
    for path in (scribe_path, whisper_path):
        hyp = path.read_text(encoding="utf-8").strip()
        al = align_words(ref, hyp)
        tagged = tag_alignment(al)
        assert sum(t.edit_mass for t in tagged) == al.total_edit_mass
        summary = summarize_tags(tagged)
        assert summary["total_edit_mass"] == al.total_edit_mass
