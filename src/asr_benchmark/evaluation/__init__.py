"""Offline evaluation: Polish text normalization and WER/CER metrics."""

from asr_benchmark.evaluation.alignment import AlignmentResult, EditOp, align_words
from asr_benchmark.evaluation.metrics import (
    EVALUATION_VERSION,
    EVALUATION_VERSION_V2,
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
from asr_benchmark.evaluation.normalize_v2 import (
    EVALUATION_PROTOCOL,
    WER_NORMALIZATION_VERSION,
    normalize_pl_wer_v1,
    normalize_with_trace,
)
from asr_benchmark.evaluation.taxonomy import (
    TAXONOMY_VERSION,
    summarize_tags,
    tag_alignment,
)
from asr_benchmark.evaluation.taxonomy_v2 import (
    TAXONOMY_VERSION as TAXONOMY_VERSION_V2,
)
from asr_benchmark.evaluation.taxonomy_v2 import (
    summarize_tags_v2,
    tag_alignment_v2,
)

__all__ = [
    "EVALUATION_PROTOCOL",
    "EVALUATION_VERSION",
    "EVALUATION_VERSION_V2",
    "NORMALIZATION_VERSION",
    "NUMBERS_NORMALIZATION_VERSION",
    "TAXONOMY_VERSION",
    "TAXONOMY_VERSION_V2",
    "WER_NORMALIZATION_VERSION",
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
    "normalize_pl_wer_v1",
    "normalize_with_trace",
    "summarize_tags",
    "summarize_tags_v2",
    "tag_alignment",
    "tag_alignment_v2",
]
