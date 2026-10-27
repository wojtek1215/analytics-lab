"""WER/CER computation via jiwer on already-normalized text."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from jiwer import process_characters, process_words
from jiwer.transforms import (
    Compose,
    ReduceToListOfListOfChars,
    ReduceToListOfListOfWords,
    RemoveMultipleSpaces,
    Strip,
)

from asr_benchmark.evaluation.normalize import (
    NORMALIZATION_VERSION,
    NUMBERS_NORMALIZATION_VERSION,
    normalize_pl_basic_v1,
    normalize_pl_numbers_v1,
)
from asr_benchmark.evaluation.normalize_v2 import (
    WER_NORMALIZATION_VERSION,
    normalize_pl_wer_v1,
)

_NORMALIZERS = {
    NORMALIZATION_VERSION: normalize_pl_basic_v1,
    NUMBERS_NORMALIZATION_VERSION: normalize_pl_numbers_v1,
    WER_NORMALIZATION_VERSION: normalize_pl_wer_v1,
}

EVALUATION_VERSION = "1.0.0"
EVALUATION_VERSION_V2 = "2.0.0"

# Pre-normalized text: tokenize only — do not re-apply case/punct transforms.
# Public alias kept stable for alignment diagnostics (must stay in sync).
WORD_TRANSFORM = Compose(
    [RemoveMultipleSpaces(), Strip(), ReduceToListOfListOfWords()]
)
_WORD_TRANSFORM = WORD_TRANSFORM
_CHAR_TRANSFORM = Compose(
    [RemoveMultipleSpaces(), Strip(), ReduceToListOfListOfChars()]
)


class EmptyReferenceError(ValueError):
    """Raised when the reference is empty after normalization."""


@dataclass(frozen=True)
class ClipMetrics:
    """Per-clip WER/CER and edit counts after ``pl_basic_v1`` normalization."""

    clip_id: str
    model_id: str
    reference: str
    hypothesis: str
    normalized_reference: str
    normalized_hypothesis: str
    wer: float
    cer: float
    substitutions: int
    deletions: int
    insertions: int
    hits: int
    n_words_ref: int
    n_chars_ref: int
    char_substitutions: int
    char_deletions: int
    char_insertions: int
    normalization_version: str = NORMALIZATION_VERSION
    evaluation_version: str = EVALUATION_VERSION
    status: str = "ok"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class CorpusMetrics:
    """Corpus-level aggregates: sum(errors) / sum(reference units)."""

    n_clips: int
    wer: float
    cer: float
    substitutions: int
    deletions: int
    insertions: int
    n_words_ref: int
    n_chars_ref: int
    char_substitutions: int
    char_deletions: int
    char_insertions: int
    normalization_version: str = NORMALIZATION_VERSION
    evaluation_version: str = EVALUATION_VERSION

    def to_dict(self) -> dict:
        return asdict(self)


def _require_nonempty_reference(normalized_reference: str) -> None:
    if not normalized_reference.strip():
        raise EmptyReferenceError(
            "reference is empty after normalization; cannot compute WER/CER"
        )


def compute_wer(normalized_reference: str, normalized_hypothesis: str) -> dict:
    """Word error rate and S/D/I/N on pre-normalized strings."""
    _require_nonempty_reference(normalized_reference)
    out = process_words(
        normalized_reference,
        normalized_hypothesis,
        reference_transform=_WORD_TRANSFORM,
        hypothesis_transform=_WORD_TRANSFORM,
    )
    n_words = sum(len(sent) for sent in out.references)
    return {
        "wer": float(out.wer),
        "substitutions": int(out.substitutions),
        "deletions": int(out.deletions),
        "insertions": int(out.insertions),
        "hits": int(out.hits),
        "n_words_ref": int(n_words),
    }


def compute_cer(normalized_reference: str, normalized_hypothesis: str) -> dict:
    """Character error rate on pre-normalized strings (spaces count as chars)."""
    _require_nonempty_reference(normalized_reference)
    out = process_characters(
        normalized_reference,
        normalized_hypothesis,
        reference_transform=_CHAR_TRANSFORM,
        hypothesis_transform=_CHAR_TRANSFORM,
    )
    n_chars = sum(len(sent) for sent in out.references)
    return {
        "cer": float(out.cer),
        "char_substitutions": int(out.substitutions),
        "char_deletions": int(out.deletions),
        "char_insertions": int(out.insertions),
        "n_chars_ref": int(n_chars),
    }


def compute_metrics(
    reference: str,
    hypothesis: str,
    *,
    clip_id: str = "clip",
    model_id: str = "model",
    normalization_version: str = NORMALIZATION_VERSION,
    evaluation_version: str = EVALUATION_VERSION,
) -> ClipMetrics:
    """Normalize both sides and compute WER/CER.

    Default ``normalization_version`` is ``pl_basic_v1`` (legacy primary).
    ``pl_numbers_v1`` is sensitivity-only. ``pl_wer_normalized_v1`` is the
    v2 primary profile (pass ``evaluation_version=EVALUATION_VERSION_V2``).
    """
    if not isinstance(reference, str) or not isinstance(hypothesis, str):
        raise TypeError("reference and hypothesis must be str")

    try:
        normalizer = _NORMALIZERS[normalization_version]
    except KeyError as exc:
        known = ", ".join(sorted(_NORMALIZERS))
        raise ValueError(
            f"unknown normalization_version={normalization_version!r}; known: {known}"
        ) from exc

    norm_ref = normalizer(reference)
    norm_hyp = normalizer(hypothesis)
    _require_nonempty_reference(norm_ref)

    word = compute_wer(norm_ref, norm_hyp)
    char = compute_cer(norm_ref, norm_hyp)

    return ClipMetrics(
        clip_id=clip_id,
        model_id=model_id,
        reference=reference,
        hypothesis=hypothesis,
        normalized_reference=norm_ref,
        normalized_hypothesis=norm_hyp,
        wer=word["wer"],
        cer=char["cer"],
        substitutions=word["substitutions"],
        deletions=word["deletions"],
        insertions=word["insertions"],
        hits=word["hits"],
        n_words_ref=word["n_words_ref"],
        n_chars_ref=char["n_chars_ref"],
        char_substitutions=char["char_substitutions"],
        char_deletions=char["char_deletions"],
        char_insertions=char["char_insertions"],
        normalization_version=normalization_version,
        evaluation_version=evaluation_version,
    )


def aggregate_corpus(clips: list[ClipMetrics]) -> CorpusMetrics:
    """Corpus WER/CER = sum of edit ops / sum of reference units (not mean %)."""
    if not clips:
        raise ValueError("cannot aggregate an empty clip list")

    norm_versions = {c.normalization_version for c in clips}
    if len(norm_versions) != 1:
        raise ValueError(f"mixed normalization versions: {sorted(norm_versions)}")

    eval_versions = {c.evaluation_version for c in clips}
    if len(eval_versions) != 1:
        raise ValueError(f"mixed evaluation versions: {sorted(eval_versions)}")

    s = sum(c.substitutions for c in clips)
    d = sum(c.deletions for c in clips)
    i = sum(c.insertions for c in clips)
    n_words = sum(c.n_words_ref for c in clips)
    cs = sum(c.char_substitutions for c in clips)
    cd = sum(c.char_deletions for c in clips)
    ci = sum(c.char_insertions for c in clips)
    n_chars = sum(c.n_chars_ref for c in clips)

    if n_words == 0:
        raise EmptyReferenceError("corpus has zero reference words")
    if n_chars == 0:
        raise EmptyReferenceError("corpus has zero reference characters")

    return CorpusMetrics(
        n_clips=len(clips),
        wer=(s + d + i) / n_words,
        cer=(cs + cd + ci) / n_chars,
        substitutions=s,
        deletions=d,
        insertions=i,
        n_words_ref=n_words,
        n_chars_ref=n_chars,
        char_substitutions=cs,
        char_deletions=cd,
        char_insertions=ci,
        normalization_version=clips[0].normalization_version,
        evaluation_version=clips[0].evaluation_version,
    )
