"""Error taxonomy for ``polish_asr_eval_v2`` (exploratory; not primary WER).

Separates Levenshtein operations from semantic interpretation. Exclusive
primary categories account for edit mass; secondary tags may overlap and are
labeled as such. All labels are ``auto_inferred`` unless a human review file
supplies overrides.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass

from asr_benchmark.evaluation.alignment import AlignmentResult, EditOp
from asr_benchmark.evaluation.normalize_v2 import (
    WER_NORMALIZATION_VERSION,
    is_pl_wer_number_token,
)

TAXONOMY_VERSION = "taxonomy_v2"

# Exclusive primary categories
CAT_NUMBER_FORMAT = "number_format"
CAT_UNIT_FORMAT = "unit_format"
CAT_PROPER_NAME_FORMAT = "proper_name_format"
CAT_PROPER_NAME_RECOGNITION = "proper_name_recognition"
CAT_LEXICAL = "lexical_substitution"
CAT_MORPHOLOGY = "morphology"
CAT_HOMOPHONE = "homophone_ambiguity"
CAT_DELETION = "deletion"
CAT_INSERTION = "insertion"
CAT_HALLUCINATION = "potential_hallucination"
CAT_UNCLEAR = "unclear"

PRIMARY_CATEGORIES = frozenset(
    {
        CAT_NUMBER_FORMAT,
        CAT_UNIT_FORMAT,
        CAT_PROPER_NAME_FORMAT,
        CAT_PROPER_NAME_RECOGNITION,
        CAT_LEXICAL,
        CAT_MORPHOLOGY,
        CAT_HOMOPHONE,
        CAT_DELETION,
        CAT_INSERTION,
        CAT_HALLUCINATION,
        CAT_UNCLEAR,
    }
)

IMPACT_EQUIVALENT = "equivalent_formatting"
IMPACT_CONTENT = "content_difference"
IMPACT_UNDETERMINED = "undetermined"

REVIEW_AUTO = "auto_inferred"
REVIEW_HUMAN = "human_reviewed"

_HOMOPHONE_PAIRS = frozenset({frozenset({"morze", "może"})})

_FORMAT_BRAND_TOKENS = frozenset(
    {
        "chatgpt",
        "chat",
        "gpt",
        "elevenlabs",
        "eleven",
        "labs",
        "github",
        "git",
        "hub",
        "whisper",
    }
)

# Spelling variants that must NOT be treated as format-only.
_BRAND_MISSPELL_TOKENS = frozenset({"hap", "githab", "gitbhub"})

_UNIT_WORDS = frozenset(
    {
        "złoty",
        "złote",
        "złotych",
        "zł",
        "pln",
        "euro",
        "eur",
        "dolar",
        "dolary",
        "dolarów",
        "usd",
        "kilogram",
        "kilogramy",
        "kilogramów",
        "kg",
        "gram",
        "gramy",
        "gramów",
        "kilometr",
        "kilometry",
        "kilometrów",
        "km",
        "procent",
        "procenty",
        "procentów",
    }
)

_TRAILING_HALLUCINATION = frozenset({"koniec", "dziękuje", "uwagę", "uwaga"})


@dataclass(frozen=True)
class TaggedEditV2:
    """One alignment chunk with v2 taxonomy labels."""

    op: str
    ref_tokens: tuple[str, ...]
    hyp_tokens: tuple[str, ...]
    ref_start: int
    ref_end: int
    hyp_start: int
    hyp_end: int
    edit_mass: int
    primary_category: str
    secondary_tags: tuple[str, ...]
    semantic_impact: str
    review_status: str
    rationale: str
    normalization_version: str = WER_NORMALIZATION_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


def _char_similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    # Simple ratio via longest common subsequence length / max len
    la, lb = len(a), len(b)
    dp = [0] * (lb + 1)
    for ca in a:
        prev = 0
        for j, cb in enumerate(b, start=1):
            cur = dp[j]
            if ca == cb:
                dp[j] = prev + 1
            else:
                dp[j] = max(dp[j], dp[j - 1])
            prev = cur
    return dp[lb] / max(la, lb)


def _is_homophone(ref: tuple[str, ...], hyp: tuple[str, ...]) -> bool:
    if len(ref) == 1 and len(hyp) == 1:
        return frozenset({ref[0], hyp[0]}) in _HOMOPHONE_PAIRS
    if frozenset(ref) in _HOMOPHONE_PAIRS and frozenset(hyp) in _HOMOPHONE_PAIRS:
        return True
    return False


def _all_numberish(tokens: tuple[str, ...]) -> bool:
    return bool(tokens) and all(is_pl_wer_number_token(t) for t in tokens)


def _any_numberish(tokens: tuple[str, ...]) -> bool:
    return any(is_pl_wer_number_token(t) for t in tokens)


def _all_unit(tokens: tuple[str, ...]) -> bool:
    return bool(tokens) and all(t in _UNIT_WORDS for t in tokens)


def _any_misspell_brand(tokens: tuple[str, ...]) -> bool:
    return any(t in _BRAND_MISSPELL_TOKENS for t in tokens)


def _all_format_brand(tokens: tuple[str, ...]) -> bool:
    return bool(tokens) and all(t in _FORMAT_BRAND_TOKENS for t in tokens)


def _any_format_brand(tokens: tuple[str, ...]) -> bool:
    return any(t in _FORMAT_BRAND_TOKENS for t in tokens)


def _morphology_pair(ref: tuple[str, ...], hyp: tuple[str, ...]) -> bool:
    if len(ref) != 1 or len(hyp) != 1:
        return False
    a, b = ref[0], hyp[0]
    if a == b:
        return False
    if _is_homophone(ref, hyp):
        return False
    # Same stem-ish: high char overlap, short length delta
    if abs(len(a) - len(b)) > 3:
        return False
    return _char_similarity(a, b) >= 0.75


def _trailing_hallucination(op: EditOp, alignment: AlignmentResult) -> bool:
    if op.op != "insert" or op.ref_tokens:
        return False
    if op.hyp_end != len(alignment.hyp_tokens) and op.ref_start < len(alignment.ref_tokens):
        # Only trailing inserts at/after end of reference
        if op.ref_start < len(alignment.ref_tokens):
            return False
    if op.ref_start < len(alignment.ref_tokens):
        return False
    return any(t in _TRAILING_HALLUCINATION for t in op.hyp_tokens)


def _nearby_misspell_context(op: EditOp, alignment: AlignmentResult) -> bool:
    """True when a brand misspelling token sits in/near this edit span."""
    window = (
        alignment.ref_tokens[max(0, op.ref_start - 1) : min(len(alignment.ref_tokens), op.ref_end + 1)]
        + alignment.hyp_tokens[max(0, op.hyp_start - 1) : min(len(alignment.hyp_tokens), op.hyp_end + 1)]
    )
    return _any_misspell_brand(tuple(window)) or _any_misspell_brand(op.ref_tokens + op.hyp_tokens)


def tag_edit_op_v2(op: EditOp, alignment: AlignmentResult) -> TaggedEditV2:
    """Assign exclusive primary category + optional secondary tags."""
    ref_t = op.ref_tokens
    hyp_t = op.hyp_tokens
    all_toks = ref_t + hyp_t
    secondary: list[str] = []
    rationale_parts: list[str] = []
    misspell_ctx = _nearby_misspell_context(op, alignment)

    primary: str
    impact: str

    if _trailing_hallucination(op, alignment):
        primary = CAT_HALLUCINATION
        impact = IMPACT_CONTENT
        secondary.append(CAT_INSERTION)
        rationale_parts.append(
            "Trailing insertion matching closed hallucination token list; "
            "not acoustically verified in this pipeline."
        )
    elif op.op == "insert" and not ref_t:
        if _all_numberish(hyp_t):
            primary = CAT_NUMBER_FORMAT
            impact = IMPACT_EQUIVALENT
            rationale_parts.append("Insertion of number-format tokens only.")
        elif _all_unit(hyp_t):
            primary = CAT_UNIT_FORMAT
            impact = IMPACT_EQUIVALENT
            rationale_parts.append("Insertion of unit-format tokens only.")
        elif _any_misspell_brand(hyp_t):
            primary = CAT_PROPER_NAME_RECOGNITION
            impact = IMPACT_CONTENT
            rationale_parts.append("Brand misspelling token in insertion.")
        elif _all_format_brand(hyp_t):
            primary = CAT_PROPER_NAME_FORMAT
            impact = IMPACT_EQUIVALENT
            rationale_parts.append("Brand tokenization insertion.")
        else:
            primary = CAT_INSERTION
            impact = IMPACT_UNDETERMINED
            rationale_parts.append("Generic insertion.")
    elif op.op == "delete" and not hyp_t:
        if misspell_ctx or _any_misspell_brand(ref_t):
            primary = CAT_PROPER_NAME_RECOGNITION
            impact = IMPACT_CONTENT
            rationale_parts.append(
                "Deletion of brand-misspelling token (e.g. hap) near a name span."
            )
        elif _all_numberish(ref_t):
            primary = CAT_NUMBER_FORMAT
            impact = IMPACT_EQUIVALENT
            rationale_parts.append("Deletion of number-format tokens only.")
        elif _all_unit(ref_t):
            primary = CAT_UNIT_FORMAT
            impact = IMPACT_EQUIVALENT
            rationale_parts.append("Deletion of unit-format tokens only.")
        else:
            primary = CAT_DELETION
            impact = IMPACT_CONTENT
            rationale_parts.append("Reference token deleted.")
    elif op.op == "substitute":
        if _is_homophone(ref_t, hyp_t):
            primary = CAT_HOMOPHONE
            impact = IMPACT_CONTENT
            rationale_parts.append(
                "Closed homophone pair (morze/może); acoustically ambiguous, "
                "kept distinct in WER."
            )
        elif _any_misspell_brand(all_toks) or (
            misspell_ctx and (_any_format_brand(all_toks) or "github" in all_toks)
        ):
            primary = CAT_PROPER_NAME_RECOGNITION
            impact = IMPACT_CONTENT
            rationale_parts.append(
                "Brand spelling difference involving a misspelling token "
                "(e.g. git hap / githab); not format-only."
            )
        elif _all_format_brand(all_toks) and not misspell_ctx:
            primary = CAT_PROPER_NAME_FORMAT
            impact = IMPACT_EQUIVALENT
            rationale_parts.append("Brand surface tokenization only.")
        elif _all_unit(all_toks):
            primary = CAT_UNIT_FORMAT
            impact = IMPACT_EQUIVALENT
            rationale_parts.append("Unit abbreviation vs full form.")
        elif _all_numberish(all_toks):
            primary = CAT_NUMBER_FORMAT
            impact = IMPACT_EQUIVALENT
            rationale_parts.append("Numeric format difference.")
        elif _morphology_pair(ref_t, hyp_t):
            primary = CAT_MORPHOLOGY
            impact = IMPACT_CONTENT
            rationale_parts.append(
                "High character overlap substitution; treated as morphology "
                "(auto heuristic)."
            )
        elif len(ref_t) == 1 and len(hyp_t) == 1:
            primary = CAT_LEXICAL
            impact = IMPACT_CONTENT
            rationale_parts.append("Single-token lexical substitution.")
        else:
            # Mixed chunk
            primary = CAT_UNCLEAR
            impact = IMPACT_UNDETERMINED
            rationale_parts.append(
                "Mixed or multi-token substitution; automatic label uncertain."
            )
            if _any_numberish(all_toks):
                secondary.append(CAT_NUMBER_FORMAT)
            if _any_format_brand(all_toks):
                secondary.append(CAT_PROPER_NAME_FORMAT)
    else:
        primary = CAT_UNCLEAR
        impact = IMPACT_UNDETERMINED
        rationale_parts.append(f"Unhandled op={op.op}")

    # Extra brand misspell check for substitute github vs githab / git hap
    if op.op == "substitute" and primary not in {
        CAT_PROPER_NAME_RECOGNITION,
        CAT_HOMOPHONE,
    }:
        joined_ref = " ".join(ref_t)
        joined_hyp = " ".join(hyp_t)
        misspell_spans = {"git hap", "githab", "hap"}
        brand_ok = {"github", "git hub"}
        if (joined_ref in misspell_spans or joined_hyp in misspell_spans) and (
            joined_ref in brand_ok
            or joined_hyp in brand_ok
            or "github" in ref_t
            or "github" in hyp_t
            or "git" in ref_t
            or "git" in hyp_t
        ):
            primary = CAT_PROPER_NAME_RECOGNITION
            impact = IMPACT_CONTENT
            rationale_parts = [
                "Brand misspelling vs canonical form (Git Hap / GitHab / GitHub)."
            ]

    return TaggedEditV2(
        op=op.op,
        ref_tokens=ref_t,
        hyp_tokens=hyp_t,
        ref_start=op.ref_start,
        ref_end=op.ref_end,
        hyp_start=op.hyp_start,
        hyp_end=op.hyp_end,
        edit_mass=op.edit_mass,
        primary_category=primary,
        secondary_tags=tuple(secondary),
        semantic_impact=impact,
        review_status=REVIEW_AUTO,
        rationale="; ".join(rationale_parts),
        normalization_version=alignment.normalization_version,
    )


def tag_alignment_v2(alignment: AlignmentResult) -> list[TaggedEditV2]:
    tagged = [tag_edit_op_v2(op, alignment) for op in alignment.ops]
    mass = sum(t.edit_mass for t in tagged)
    if mass != alignment.total_edit_mass:
        raise AssertionError(
            f"tagged mass {mass} != alignment S+D+I {alignment.total_edit_mass}"
        )
    return tagged


def summarize_tags_v2(tagged: list[TaggedEditV2]) -> dict:
    by_primary: Counter[str] = Counter()
    by_impact: Counter[str] = Counter()
    by_secondary: Counter[str] = Counter()
    total = sum(t.edit_mass for t in tagged)
    for t in tagged:
        by_primary[t.primary_category] += t.edit_mass
        by_impact[t.semantic_impact] += t.edit_mass
        for s in t.secondary_tags:
            by_secondary[s] += t.edit_mass

    exclusive_sum = sum(by_primary.values())
    if exclusive_sum != total:
        raise AssertionError(
            f"exclusive primary mass {exclusive_sum} != total {total}"
        )

    def _pct(n: int) -> float | None:
        return (n / total) if total else None

    return {
        "taxonomy_version": TAXONOMY_VERSION,
        "total_edit_mass": total,
        "mass_by_primary_category": dict(by_primary),
        "pct_by_primary_category": {k: _pct(v) for k, v in by_primary.items()},
        "mass_by_semantic_impact": dict(by_impact),
        "pct_by_semantic_impact": {k: _pct(v) for k, v in by_impact.items()},
        "secondary_tag_mass_overlapping": dict(by_secondary),
        "secondary_note": (
            "Secondary tag masses may overlap with primary mass and must not "
            "be summed into exclusive totals."
        ),
        "review_status": REVIEW_AUTO,
    }


def reconcile_taxonomy_with_metrics(
    tagged: list[TaggedEditV2],
    *,
    substitutions: int,
    deletions: int,
    insertions: int,
) -> None:
    """Raise if exclusive taxonomy mass disagrees with WER S/D/I."""
    s = sum(t.edit_mass for t in tagged if t.op == "substitute")
    d = sum(t.edit_mass for t in tagged if t.op == "delete")
    i = sum(t.edit_mass for t in tagged if t.op == "insert")
    if s != substitutions or d != deletions or i != insertions:
        raise AssertionError(
            f"taxonomy S/D/I={s}/{d}/{i} != metrics {substitutions}/{deletions}/{insertions}"
        )
