"""Pathological ASR hypothesis auto-flag (`pathological_hyp_v1`).

Flags do **not** change primary corpus WER. See ``docs/evaluation_protocol.md``.
"""

from __future__ import annotations

import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

PATHOLOGICAL_HYP_VERSION = "pathological_hyp_v1"

_POLISH_DIACRITICS = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")
_MIN_TOKENS_FOR_FREQ = 4
_MIN_CONSECUTIVE_REPEAT = 4
_MIN_FREQ_SHARE = 0.5
_MIN_REF_CHARS_FOR_LENGTH = 12
_MAX_HYP_OVER_REF = 3.0
_MIN_HYP_OVER_REF = 0.15


@dataclass(frozen=True, slots=True)
class PathologicalFlag:
    flagged: bool
    reasons: tuple[str, ...]
    hypothesis: str
    reference: str
    n_tokens: int
    rule_version: str = PATHOLOGICAL_HYP_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _tokenize_for_pathology(text: str) -> list[str]:
    folded = unicodedata.normalize("NFC", text).casefold()
    return folded.split()


def _is_allowed_letter(ch: str) -> bool:
    if not ch.isalpha():
        return True
    if "A" <= ch <= "Z" or "a" <= ch <= "z":
        return True
    if ch in _POLISH_DIACRITICS:
        return True
    return False


def reason_repetition_loop(tokens: Sequence[str]) -> bool:
    if not tokens:
        return False
    run = 1
    for i in range(1, len(tokens)):
        if tokens[i] == tokens[i - 1]:
            run += 1
            if run >= _MIN_CONSECUTIVE_REPEAT:
                return True
        else:
            run = 1
    if len(tokens) >= _MIN_TOKENS_FOR_FREQ:
        top = Counter(tokens).most_common(1)[0][1]
        if top / len(tokens) >= _MIN_FREQ_SHARE:
            return True
    return False


def reason_unexpected_script(hypothesis: str) -> bool:
    for ch in unicodedata.normalize("NFC", hypothesis):
        if ch.isalpha() and not _is_allowed_letter(ch):
            return True
    return False


def reason_extreme_length(reference: str, hypothesis: str) -> bool:
    r = len(reference.strip())
    h = len(hypothesis.strip())
    if r < _MIN_REF_CHARS_FOR_LENGTH:
        return False
    if h > _MAX_HYP_OVER_REF * r:
        return True
    if h < _MIN_HYP_OVER_REF * r:
        return True
    return False


def flag_pathological_hypothesis(
    hypothesis: str,
    *,
    reference: str = "",
) -> PathologicalFlag:
    """Return auto-flag decision for one hypothesis string."""
    hyp = hypothesis or ""
    ref = reference or ""
    tokens = _tokenize_for_pathology(hyp)
    reasons: list[str] = []
    if reason_repetition_loop(tokens):
        reasons.append("repetition_loop")
    if reason_unexpected_script(hyp):
        reasons.append("unexpected_script")
    if reason_extreme_length(ref, hyp):
        reasons.append("extreme_length")
    return PathologicalFlag(
        flagged=bool(reasons),
        reasons=tuple(reasons),
        hypothesis=hyp,
        reference=ref,
        n_tokens=len(tokens),
    )


def summarize_pathological_flags(
    rows: Sequence[Mapping[str, Any]],
    *,
    primary_corpus_by_model: Mapping[str, Mapping[str, Any]] | None = None,
    sensitivity_corpus_by_model: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build report payload from per-(model, clip) flag rows."""
    by_model: dict[str, dict[str, Any]] = {}
    for row in rows:
        mid = str(row["model_id"])
        bucket = by_model.setdefault(
            mid,
            {
                "n_scored": 0,
                "n_flagged": 0,
                "flagged_clip_ids": [],
            },
        )
        bucket["n_scored"] += 1
        if row.get("flagged"):
            bucket["n_flagged"] += 1
            bucket["flagged_clip_ids"].append(row["clip_id"])

    for mid, bucket in by_model.items():
        if primary_corpus_by_model and mid in primary_corpus_by_model:
            bucket["primary_wer"] = primary_corpus_by_model[mid].get("wer")
            bucket["primary_n_clips"] = primary_corpus_by_model[mid].get("n_clips")
            bucket["primary_n_words_ref"] = primary_corpus_by_model[mid].get(
                "n_words_ref"
            )
        if sensitivity_corpus_by_model and mid in sensitivity_corpus_by_model:
            sens = sensitivity_corpus_by_model[mid]
            bucket["sensitivity_excluding_flagged"] = sens
            bucket["pathology_excluded_wer"] = sens.get("wer")
        elif bucket["n_flagged"] == 0 and primary_corpus_by_model:
            # Identical to primary when nothing flagged
            prim = primary_corpus_by_model.get(mid)
            if prim is not None:
                bucket["sensitivity_excluding_flagged"] = {
                    **dict(prim),
                    "note": "identical_to_primary_no_flags",
                }
                bucket["pathology_excluded_wer"] = prim.get("wer")

        prim_w = bucket.get("primary_wer")
        excl_w = bucket.get("pathology_excluded_wer")
        if isinstance(prim_w, (int, float)) and isinstance(excl_w, (int, float)):
            # Positive => headline is higher (worse) than pathology-excluded view
            bucket["pathology_impact_pp"] = round(100.0 * (prim_w - excl_w), 2)
        else:
            bucket["pathology_impact_pp"] = None

    return {
        "rule_version": PATHOLOGICAL_HYP_VERSION,
        "changes_primary_wer": False,
        "finding": (
            "Pathology impact estimates how much catastrophic ASR collapse "
            "inflates the headline WER, while keeping those clips in the "
            "primary score for transparency."
        ),
        "by_model": by_model,
        "rows": list(rows),
    }


def render_pathological_md(payload: Mapping[str, Any]) -> str:
    lines = [
        f"# Pathology impact — `{payload.get('cohort_id', '')}`",
        "",
        f"**Rule:** `{payload.get('rule_version', PATHOLOGICAL_HYP_VERSION)}`",
        "",
        str(
            payload.get("finding")
            or (
                "Pathology impact estimates how much catastrophic ASR collapse "
                "inflates the headline WER, while keeping those clips in the "
                "primary score for transparency."
            )
        ),
        "",
        "- **Primary corpus WER** — headline (all clips).",
        "- **Pathology-excluded WER** — sensitivity after dropping auto-flagged "
        "clips for that model only.",
        "- **Pathology impact (pp)** — primary − pathology-excluded, in "
        "percentage points (positive ⇒ flagged collapses worsen the headline).",
        "",
        "## Summary",
        "",
        "| Model | Flagged / scored | Primary WER | Pathology-excluded WER | Pathology impact (pp) |",
        "|---|---:|---:|---:|---:|",
    ]
    by_model = payload.get("by_model") or {}
    for mid, bucket in by_model.items():
        prim = bucket.get("primary_wer")
        sens = bucket.get("pathology_excluded_wer")
        if sens is None:
            sens = (bucket.get("sensitivity_excluding_flagged") or {}).get("wer")
        impact = bucket.get("pathology_impact_pp")
        prim_s = f"{100 * prim:.1f}%" if isinstance(prim, (int, float)) else "—"
        sens_s = f"{100 * sens:.1f}%" if isinstance(sens, (int, float)) else "—"
        impact_s = f"{impact:+.2f}" if isinstance(impact, (int, float)) else "—"
        lines.append(
            f"| `{mid}` | {bucket.get('n_flagged', 0)}/{bucket.get('n_scored', 0)} | "
            f"{prim_s} | {sens_s} | {impact_s} |"
        )

    flagged_rows = [r for r in (payload.get("rows") or []) if r.get("flagged")]
    lines.extend(["", "## Flagged clips", ""])
    if not flagged_rows:
        lines.append("_No hypotheses matched pathological_hyp_v1._")
        lines.append("")
        return "\n".join(lines)

    for row in flagged_rows:
        reasons = ", ".join(f"`{x}`" for x in row.get("reasons") or [])
        lines.append(f"### `{row['clip_id']}` — `{row['model_id']}`")
        lines.append("")
        lines.append(f"- **Reasons:** {reasons}")
        lines.append(f"- **Reference:** {row.get('reference', '')}")
        lines.append(f"- **Hypothesis:** {row.get('hypothesis', '')}")
        lines.append("")
    return "\n".join(lines)
