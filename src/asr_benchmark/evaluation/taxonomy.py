"""Heuristic ASR error taxonomy (exploratory; not part of primary WER)."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass

from asr_benchmark.evaluation.alignment import AlignmentResult, EditOp
from asr_benchmark.evaluation.normalize import (
    is_pl_number_token,
    normalize_pl_numbers_v1,
)

TAXONOMY_VERSION = "taxonomy_v0"

TAG_NUMBER_FORMAT = "number_format"
TAG_PROPER_NAME = "proper_name"
TAG_LEXICAL = "lexical"
TAG_HOMOPHONE = "homophone"
TAG_INSERTION_EXTRA = "insertion_extra"
TAG_AMBIGUOUS = "ambiguous"

CONTENT_FORMAT_ONLY = "format_only"
CONTENT_CHANGING = "content_changing"
CONTENT_UNCLEAR = "unclear"

# Closed lists for v0 — do not expand against holdout errors.
_PROPER_NAME_TOKENS = frozenset(
    {
        "chatgpt",
        "chat",
        "gpt",
        "elevenlabs",
        "eleven",
        "labs",
        "github",
        "git",
        "hap",
        "githab",
        "whisper",  # brand in the smoke script; keep listed explicitly
    }
)

_HOMOPHONE_PAIRS = frozenset({frozenset({"morze", "może"})})

_TRAILING_HALLUCINATION_TOKENS = frozenset({"koniec", "dziękuje", "uwagę", "uwaga"})


@dataclass(frozen=True)
class TaggedEdit:
    """EditOp plus taxonomy_v0 labels."""

    op: str
    ref_tokens: tuple[str, ...]
    hyp_tokens: tuple[str, ...]
    ref_start: int
    ref_end: int
    hyp_start: int
    hyp_end: int
    edit_mass: int
    tag: str
    content_impact: str
    notes: str
    numbers_span_resolved: bool | None

    def to_dict(self) -> dict:
        return asdict(self)


def _all_numberish(tokens: tuple[str, ...]) -> bool:
    return bool(tokens) and all(is_pl_number_token(t) for t in tokens)


def _any_numberish(tokens: tuple[str, ...]) -> bool:
    return any(is_pl_number_token(t) for t in tokens)


def _all_proper(tokens: tuple[str, ...]) -> bool:
    return bool(tokens) and all(t in _PROPER_NAME_TOKENS for t in tokens)


def _any_proper(tokens: tuple[str, ...]) -> bool:
    return any(t in _PROPER_NAME_TOKENS for t in tokens)


def _is_homophone_swap(ref_tokens: tuple[str, ...], hyp_tokens: tuple[str, ...]) -> bool:
    if len(ref_tokens) != 1 or len(hyp_tokens) != 1:
        # Also allow contiguous 2-token swaps of the known pair only when sets match.
        if frozenset(ref_tokens) in _HOMOPHONE_PAIRS and frozenset(hyp_tokens) in _HOMOPHONE_PAIRS:
            return True
        return False
    return frozenset({ref_tokens[0], hyp_tokens[0]}) in _HOMOPHONE_PAIRS


def _numbers_resolve_chunk(
    alignment: AlignmentResult,
    op: EditOp,
) -> bool | None:
    """True if applying pl_numbers_v1 to full texts removes this local disagreement.

    Auxiliary signal only; failures return None.
    """
    try:
        # Rebuild local windows from basic-normalized tokens, then numbers-normalize
        # the joined full strings and see whether token sequences match at the
        # approximate locus. Simpler check: if the chunk tokens are numberish on
        # both sides OR one side digits and the other number words.
        ref_n = _any_numberish(op.ref_tokens)
        hyp_n = _any_numberish(op.hyp_tokens)
        if not (ref_n or hyp_n):
            return False
        full_ref = normalize_pl_numbers_v1(alignment.normalized_reference)
        full_hyp = normalize_pl_numbers_v1(alignment.normalized_hypothesis)
        # If whole-string numbers normalization equalizes texts, number formatting
        # explains the global gap; for mixed chunks still mark resolved=False locally.
        if full_ref == full_hyp:
            return True
        # Local: both sides numberish → treat as format-resolved candidate
        if _all_numberish(op.ref_tokens) and _all_numberish(op.hyp_tokens):
            return True
        if (not op.ref_tokens and _all_numberish(op.hyp_tokens)) or (
            not op.hyp_tokens and _all_numberish(op.ref_tokens)
        ):
            return True
        return False
    except Exception:
        return None


def _content_impact(tag: str, notes: str) -> str:
    if tag == TAG_NUMBER_FORMAT:
        return CONTENT_FORMAT_ONLY
    if tag == TAG_PROPER_NAME:
        return CONTENT_FORMAT_ONLY
    if tag in {TAG_LEXICAL, TAG_HOMOPHONE}:
        return CONTENT_CHANGING
    if tag == TAG_INSERTION_EXTRA:
        if "hallucination_trailing" in notes:
            return CONTENT_CHANGING
        return CONTENT_UNCLEAR
    return CONTENT_UNCLEAR


def tag_edit_op(op: EditOp, alignment: AlignmentResult) -> TaggedEdit:
    """Assign a single taxonomy_v0 tag to one alignment chunk."""
    notes_parts: list[str] = []
    numbers_resolved = _numbers_resolve_chunk(alignment, op)

    ref_t = op.ref_tokens
    hyp_t = op.hyp_tokens
    all_toks = ref_t + hyp_t
    num_flags = [is_pl_number_token(t) for t in all_toks]
    mixed_number = bool(all_toks) and any(num_flags) and not all(num_flags)
    pure_number = bool(all_toks) and all(num_flags)

    pure_proper = (
        bool(all_toks)
        and _all_proper(all_toks)
        and (bool(ref_t) or bool(hyp_t))
    )
    mixed_proper = _any_proper(all_toks) and not pure_proper

    tag: str

    if op.op == "insert" and not ref_t:
        if pure_number or (numbers_resolved and _all_numberish(hyp_t)):
            tag = TAG_NUMBER_FORMAT
        elif pure_proper:
            tag = TAG_PROPER_NAME
        elif mixed_number or mixed_proper:
            tag = TAG_AMBIGUOUS
            notes_parts.append("mixed signals on insertion span")
        else:
            tag = TAG_INSERTION_EXTRA
            # Trailing hallucination heuristic: insert at/after end of reference
            if op.ref_start >= len(alignment.ref_tokens) or op.ref_start == len(
                alignment.ref_tokens
            ):
                if any(t in _TRAILING_HALLUCINATION_TOKENS for t in hyp_t):
                    notes_parts.append("hallucination_trailing")
            elif any(t in _TRAILING_HALLUCINATION_TOKENS for t in hyp_t) and op.ref_start >= max(
                0, len(alignment.ref_tokens) - 1
            ):
                notes_parts.append("hallucination_trailing")
            if hyp_t and hyp_t[-1] in _TRAILING_HALLUCINATION_TOKENS and op.hyp_end == len(
                alignment.hyp_tokens
            ):
                if "hallucination_trailing" not in notes_parts:
                    notes_parts.append("hallucination_trailing")
    elif op.op == "delete" and not hyp_t:
        if pure_number:
            tag = TAG_NUMBER_FORMAT
        elif pure_proper:
            tag = TAG_PROPER_NAME
        elif mixed_number or mixed_proper:
            tag = TAG_AMBIGUOUS
            notes_parts.append("mixed signals on deletion span")
        else:
            tag = TAG_LEXICAL
    elif op.op == "substitute":
        if _is_homophone_swap(ref_t, hyp_t):
            tag = TAG_HOMOPHONE
            notes_parts.append("closed homophone list (morze/może)")
        elif pure_number or (
            numbers_resolved and _any_numberish(all_toks) and not mixed_proper
            and not mixed_number
        ):
            tag = TAG_NUMBER_FORMAT
        elif pure_proper:
            tag = TAG_PROPER_NAME
        elif mixed_number or mixed_proper:
            tag = TAG_AMBIGUOUS
            notes_parts.append("mixed number/name/lexical tokens in one chunk")
        else:
            tag = TAG_LEXICAL
    else:
        tag = TAG_AMBIGUOUS
        notes_parts.append(f"unhandled op={op.op}")

    if numbers_resolved is True and tag == TAG_NUMBER_FORMAT:
        notes_parts.append("pl_numbers_v1_signal")
    elif numbers_resolved is True and tag == TAG_AMBIGUOUS and mixed_number:
        notes_parts.append("pl_numbers_v1_partial")

    notes = "; ".join(notes_parts)
    impact = _content_impact(tag, notes)

    return TaggedEdit(
        op=op.op,
        ref_tokens=ref_t,
        hyp_tokens=hyp_t,
        ref_start=op.ref_start,
        ref_end=op.ref_end,
        hyp_start=op.hyp_start,
        hyp_end=op.hyp_end,
        edit_mass=op.edit_mass,
        tag=tag,
        content_impact=impact,
        notes=notes,
        numbers_span_resolved=numbers_resolved,
    )


def tag_alignment(alignment: AlignmentResult) -> list[TaggedEdit]:
    tagged = [tag_edit_op(op, alignment) for op in alignment.ops]
    mass = sum(t.edit_mass for t in tagged)
    if mass != alignment.total_edit_mass:
        raise AssertionError(
            f"tagged mass {mass} != alignment S+D+I {alignment.total_edit_mass}"
        )
    return tagged


def summarize_tags(tagged: list[TaggedEdit]) -> dict:
    by_tag: Counter[str] = Counter()
    by_impact: Counter[str] = Counter()
    total = sum(t.edit_mass for t in tagged)
    for t in tagged:
        by_tag[t.tag] += t.edit_mass
        by_impact[t.content_impact] += t.edit_mass

    def _pct(n: int) -> float | None:
        return (n / total) if total else None

    return {
        "taxonomy_version": TAXONOMY_VERSION,
        "total_edit_mass": total,
        "mass_by_tag": dict(by_tag),
        "pct_by_tag": {k: _pct(v) for k, v in by_tag.items()},
        "mass_by_content_impact": dict(by_impact),
        "pct_by_content_impact": {k: _pct(v) for k, v in by_impact.items()},
    }
