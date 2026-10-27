"""Offline evaluation: Polish text normalization and WER/CER metrics."""

from asr_benchmark.evaluation.alignment import AlignmentResult, EditOp, align_words
from asr_benchmark.evaluation.metrics import (
    EVALUATION_VERSION,
    ClipMetrics,
    CorpusMetrics,
    aggregate_corpus,
    compute_cer,
    compute_metrics,
    compute_wer,
)
from asr_benchmark.evaluation.normalize import (
    NORMALIZATION_VERSION,
    NUMBERS_NORMALIZATION_VERSION,
    normalize_pl_basic_v1,
    normalize_pl_numbers_v1,
)
from asr_benchmark.evaluation.taxonomy import (
    TAXONOMY_VERSION,
    summarize_tags,
    tag_alignment,
)

__all__ = [
    "EVALUATION_VERSION",
    "NORMALIZATION_VERSION",
    "NUMBERS_NORMALIZATION_VERSION",
    "TAXONOMY_VERSION",
    "AlignmentResult",
    "EditOp",
    "ClipMetrics",
    "CorpusMetrics",
    "aggregate_corpus",
    "align_words",
    "compute_cer",
    "compute_metrics",
    "compute_wer",
    "normalize_pl_basic_v1",
    "normalize_pl_numbers_v1",
    "summarize_tags",
    "tag_alignment",
]
