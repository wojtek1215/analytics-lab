"""Word-level jiwer alignment exposed as auditable edit operations."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from jiwer import process_words

from asr_benchmark.evaluation.metrics import WORD_TRANSFORM
from asr_benchmark.evaluation.normalize import (
    NORMALIZATION_VERSION,
    normalize_pl_basic_v1,
)


@dataclass(frozen=True)
class EditOp:
    """One contiguous jiwer alignment chunk that is not an equal match."""

    op: str  # substitute | delete | insert
    ref_tokens: tuple[str, ...]
    hyp_tokens: tuple[str, ...]
    ref_start: int
    ref_end: int
    hyp_start: int
    hyp_end: int
    edit_mass: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class AlignmentResult:
    """Full alignment for one reference/hypothesis pair under pl_basic_v1."""

    normalized_reference: str
    normalized_hypothesis: str
    ref_tokens: tuple[str, ...]
    hyp_tokens: tuple[str, ...]
    substitutions: int
    deletions: int
    insertions: int
    hits: int
    n_words_ref: int
    wer: float
    ops: tuple[EditOp, ...]
    normalization_version: str = NORMALIZATION_VERSION

    @property
    def total_edit_mass(self) -> int:
        return self.substitutions + self.deletions + self.insertions

    def to_dict(self) -> dict:
        return {
            "normalized_reference": self.normalized_reference,
            "normalized_hypothesis": self.normalized_hypothesis,
            "ref_tokens": list(self.ref_tokens),
            "hyp_tokens": list(self.hyp_tokens),
            "substitutions": self.substitutions,
            "deletions": self.deletions,
            "insertions": self.insertions,
            "hits": self.hits,
            "n_words_ref": self.n_words_ref,
            "wer": self.wer,
            "total_edit_mass": self.total_edit_mass,
            "normalization_version": self.normalization_version,
            "ops": [op.to_dict() for op in self.ops],
        }


def _chunk_edit_mass(op_type: str, ref_tokens: list[str], hyp_tokens: list[str]) -> int:
    if op_type == "substitute":
        # jiwer substitute chunks are equal-length pairwise substitutions
        return len(ref_tokens)
    if op_type == "insert":
        return len(hyp_tokens)
    if op_type == "delete":
        return len(ref_tokens)
    raise ValueError(f"unsupported alignment op: {op_type}")


def align_words(
    reference: str,
    hypothesis: str,
    *,
    already_normalized: bool = False,
) -> AlignmentResult:
    """Align reference vs hypothesis with the same transforms as primary WER."""
    if not isinstance(reference, str) or not isinstance(hypothesis, str):
        raise TypeError("reference and hypothesis must be str")

    if already_normalized:
        norm_ref = reference
        norm_hyp = hypothesis
    else:
        norm_ref = normalize_pl_basic_v1(reference)
        norm_hyp = normalize_pl_basic_v1(hypothesis)

    if not norm_ref.strip():
        raise ValueError(
            "reference is empty after normalization; cannot align"
        )

    out = process_words(
        norm_ref,
        norm_hyp,
        reference_transform=WORD_TRANSFORM,
        hypothesis_transform=WORD_TRANSFORM,
    )
    ref_tokens = tuple(out.references[0])
    hyp_tokens = tuple(out.hypotheses[0])
    n_words = len(ref_tokens)

    ops: list[EditOp] = []
    for chunk in out.alignments[0]:
        if chunk.type == "equal":
            continue
        # jiwer uses 'substitute' | 'insert' | 'delete'
        op_type = chunk.type
        if op_type == "replace":
            op_type = "substitute"
        rt = list(ref_tokens[chunk.ref_start_idx : chunk.ref_end_idx])
        ht = list(hyp_tokens[chunk.hyp_start_idx : chunk.hyp_end_idx])
        mass = _chunk_edit_mass(op_type, rt, ht)
        ops.append(
            EditOp(
                op=op_type,
                ref_tokens=tuple(rt),
                hyp_tokens=tuple(ht),
                ref_start=int(chunk.ref_start_idx),
                ref_end=int(chunk.ref_end_idx),
                hyp_start=int(chunk.hyp_start_idx),
                hyp_end=int(chunk.hyp_end_idx),
                edit_mass=mass,
            )
        )

    result = AlignmentResult(
        normalized_reference=norm_ref,
        normalized_hypothesis=norm_hyp,
        ref_tokens=ref_tokens,
        hyp_tokens=hyp_tokens,
        substitutions=int(out.substitutions),
        deletions=int(out.deletions),
        insertions=int(out.insertions),
        hits=int(out.hits),
        n_words_ref=n_words,
        wer=float(out.wer),
        ops=tuple(ops),
    )

    mass_sum = sum(op.edit_mass for op in result.ops)
    expected = result.total_edit_mass
    if mass_sum != expected:
        raise AssertionError(
            f"alignment edit_mass sum {mass_sum} != S+D+I {expected}"
        )
    return result


def assert_alignment_matches_counts(
    alignment: AlignmentResult,
    *,
    substitutions: int,
    deletions: int,
    insertions: int,
    n_words_ref: int,
    wer: float,
    abs_tol: float = 1e-9,
) -> None:
    """Verify alignment aggregates match an existing metrics record."""
    if alignment.substitutions != substitutions:
        raise AssertionError(
            f"S mismatch: alignment={alignment.substitutions} expected={substitutions}"
        )
    if alignment.deletions != deletions:
        raise AssertionError(
            f"D mismatch: alignment={alignment.deletions} expected={deletions}"
        )
    if alignment.insertions != insertions:
        raise AssertionError(
            f"I mismatch: alignment={alignment.insertions} expected={insertions}"
        )
    if alignment.n_words_ref != n_words_ref:
        raise AssertionError(
            f"N mismatch: alignment={alignment.n_words_ref} expected={n_words_ref}"
        )
    if abs(alignment.wer - wer) > abs_tol:
        raise AssertionError(
            f"WER mismatch: alignment={alignment.wer} expected={wer}"
        )
    if abs(alignment.wer - (alignment.total_edit_mass / n_words_ref)) > abs_tol:
        raise AssertionError("WER != (S+D+I)/N on alignment result")
