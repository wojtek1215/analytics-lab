"""Polish WER-normalized profile ``pl_wer_normalized_v1`` (protocol polish_asr_eval_v2).

Deterministic, symmetric, model-independent. No LLM. Builds on frozen
``pl_basic_v1`` after a pre-punctuation symbol pass, then applies versioned
token rules for numbers, years, percent, units, and unambiguous brand spacing.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass

from asr_benchmark.evaluation.normalize import normalize_pl_basic_v1

WER_NORMALIZATION_VERSION = "pl_wer_normalized_v1"
EVALUATION_PROTOCOL = "polish_asr_eval_v2"

RULE_PERCENT = "percent_symbol"
RULE_CURRENCY_SYMBOL = "currency_symbol"
RULE_MINUS = "minus_sign"
RULE_CARDINAL = "spelled_cardinal"
RULE_DECIMAL = "spelled_decimal"
RULE_DIGIT_DECIMAL = "digit_decimal_unify"
RULE_YEAR = "year_ordinal"
RULE_UNIT = "unit_abbrev"
RULE_BRAND = "brand_tokenize"

ALL_RULES: frozenset[str] = frozenset(
    {
        RULE_PERCENT,
        RULE_CURRENCY_SYMBOL,
        RULE_MINUS,
        RULE_CARDINAL,
        RULE_DECIMAL,
        RULE_DIGIT_DECIMAL,
        RULE_YEAR,
        RULE_UNIT,
        RULE_BRAND,
    }
)

_WHITESPACE_RE = re.compile(r"\s+")
_DECIMAL_WORD = "przecinek"

# Nominative / citation forms only (oblique left untouched).
_NOM_UNITS: dict[str, int] = {
    "zero": 0,
    "jeden": 1,
    "jedna": 1,
    "jedno": 1,
    "dwa": 2,
    "dwie": 2,
    "trzy": 3,
    "cztery": 4,
    "pięć": 5,
    "sześć": 6,
    "siedem": 7,
    "osiem": 8,
    "dziewięć": 9,
}

_NOM_TEENS: dict[str, int] = {
    "dziesięć": 10,
    "jedenaście": 11,
    "dwanaście": 12,
    "trzynaście": 13,
    "czternaście": 14,
    "piętnaście": 15,
    "szesnaście": 16,
    "siedemnaście": 17,
    "osiemnaście": 18,
    "dziewiętnaście": 19,
}

_NOM_TENS: dict[str, int] = {
    "dwadzieścia": 20,
    "trzydzieści": 30,
    "czterdzieści": 40,
    "pięćdziesiąt": 50,
    "sześćdziesiąt": 60,
    "siedemdziesiąt": 70,
    "osiemdziesiąt": 80,
    "dziewięćdziesiąt": 90,
}

_NOM_HUNDREDS: dict[str, int] = {
    "sto": 100,
    "dwieście": 200,
    "trzysta": 300,
    "czterysta": 400,
    "pięćset": 500,
    "sześćset": 600,
    "siedemset": 700,
    "osiemset": 800,
    "dziewięćset": 900,
}

_THOUSAND_FORMS = frozenset({"tysiąc", "tysiące", "tysięcy"})
_MILLION_FORMS = frozenset({"milion", "miliony", "milionów"})
_BILLION_FORMS = frozenset({"miliard", "miliardy", "miliardów"})

_YEAR_WORDS = frozenset({"rok", "roku", "rokiem"})

# Year ordinals: all common case/gender forms → same digit (documented collapse).
_YEAR_ORDINAL_UNITS: dict[str, int] = {
    "pierwszy": 1,
    "pierwszego": 1,
    "pierwszym": 1,
    "pierwsza": 1,
    "pierwszej": 1,
    "pierwszą": 1,
    "drugi": 2,
    "drugiego": 2,
    "drugim": 2,
    "druga": 2,
    "drugiej": 2,
    "drugą": 2,
    "trzeci": 3,
    "trzeciego": 3,
    "trzecim": 3,
    "trzecia": 3,
    "trzeciej": 3,
    "trzecią": 3,
    "czwarty": 4,
    "czwartego": 4,
    "czwartym": 4,
    "czwarta": 4,
    "czwartej": 4,
    "czwartą": 4,
    "piąty": 5,
    "piątego": 5,
    "piątym": 5,
    "piąta": 5,
    "piątej": 5,
    "piątą": 5,
    "szósty": 6,
    "szóstego": 6,
    "szóstym": 6,
    "szósta": 6,
    "szóstej": 6,
    "szóstą": 6,
    "siódmy": 7,
    "siódmego": 7,
    "siódmym": 7,
    "siódma": 7,
    "siódmej": 7,
    "siódmą": 7,
    "ósmy": 8,
    "ósmego": 8,
    "ósmym": 8,
    "ósma": 8,
    "ósmej": 8,
    "ósmą": 8,
    "dziewiąty": 9,
    "dziewiątego": 9,
    "dziewiątym": 9,
    "dziewiąta": 9,
    "dziewiątej": 9,
    "dziewiątą": 9,
}

_YEAR_ORDINAL_TENS: dict[str, int] = {
    "dziesiąty": 10,
    "dziesiątego": 10,
    "dziesiątym": 10,
    "dziesiąta": 10,
    "dziesiątej": 10,
    "dziesiątą": 10,
    "dwudziesty": 20,
    "dwudziestego": 20,
    "dwudziestym": 20,
    "dwudziesta": 20,
    "dwudziestej": 20,
    "dwudziestą": 20,
    "trzydziesty": 30,
    "trzydziestego": 30,
    "trzydziestym": 30,
    "trzydziesta": 30,
    "trzydziestej": 30,
    "trzydziestą": 30,
    "czterdziesty": 40,
    "czterdziestego": 40,
    "czterdziestym": 40,
    "czterdziesta": 40,
    "czterdziestej": 40,
    "czterdziestą": 40,
    "pięćdziesiąty": 50,
    "pięćdziesiątego": 50,
    "pięćdziesiątym": 50,
    "pięćdziesiąta": 50,
    "pięćdziesiątej": 50,
    "pięćdziesiątą": 50,
    "sześćdziesiąty": 60,
    "sześćdziesiątego": 60,
    "sześćdziesiątym": 60,
    "sześćdziesiąta": 60,
    "sześćdziesiątej": 60,
    "sześćdziesiątą": 60,
    "siedemdziesiąty": 70,
    "siedemdziesiątego": 70,
    "siedemdziesiątym": 70,
    "siedemdziesiąta": 70,
    "siedemdziesiątej": 70,
    "siedemdziesiątą": 70,
    "osiemdziesiąty": 80,
    "osiemdziesiątego": 80,
    "osiemdziesiątym": 80,
    "osiemdziesiąta": 80,
    "osiemdziesiątej": 80,
    "osiemdziesiątą": 80,
    "dziewięćdziesiąty": 90,
    "dziewięćdziesiątego": 90,
    "dziewięćdziesiątym": 90,
    "dziewięćdziesiąta": 90,
    "dziewięćdziesiątej": 90,
    "dziewięćdziesiątą": 90,
}

# Oblique / unsupported forms: leave unchanged (trace skip).
_OBLIQUE_NUMBERISH = frozenset(
    {
        "jednego",
        "jednemu",
        "jednym",
        "jednej",
        "jedną",
        "dwóch",
        "dwóm",
        "dwoma",
        "dwu",
        "trzech",
        "trzem",
        "trzema",
        "czterech",
        "czterem",
        "czterema",
        "pięciu",
        "sześciu",
        "siedmiu",
        "ośmiu",
        "dziewięciu",
        "dziesięciu",
        "jedenastu",
        "dwunastu",
        "trzynastu",
        "czternastu",
        "piętnastu",
        "szesnastu",
        "siedemnastu",
        "osiemnastu",
        "dziewiętnastu",
        "dwudziestu",
        "trzydziestu",
        "czterdziestu",
        "pięćdziesięciu",
        "sześćdziesięciu",
        "siedemdziesięciu",
        "osiemdziesięciu",
        "dziewięćdziesięciu",
        "stu",
        "dwustu",
        "trzystu",
        "czterystu",
        "pięciuset",
        "sześciuset",
        "siedmiuset",
        "ośmiuset",
        "dziewięciuset",
        "tysiąca",
        "tysiącom",
        "tysiącami",
        "tysiącach",
    }
)

_STANDALONE_ONE = frozenset({"jeden", "jedna", "jedno"})

# Abbreviation → (singular, paucal, genitive_plural)
_UNIT_ABBREVS: dict[str, tuple[str, str, str]] = {
    "zł": ("złoty", "złote", "złotych"),
    "pln": ("złoty", "złote", "złotych"),
    "eur": ("euro", "euro", "euro"),
    "€": ("euro", "euro", "euro"),
    "usd": ("dolar", "dolary", "dolarów"),
    "$": ("dolar", "dolary", "dolarów"),
    "kg": ("kilogram", "kilogramy", "kilogramów"),
    "g": ("gram", "gramy", "gramów"),
    "km": ("kilometr", "kilometry", "kilometrów"),
}

_BRAND_BIGRAMS: dict[tuple[str, str], str] = {
    ("chat", "gpt"): "chatgpt",
    ("eleven", "labs"): "elevenlabs",
    ("git", "hub"): "github",
}

_DIGIT_RE = re.compile(r"^\d+(?:[.,]\d+)?$")
_INT_RE = re.compile(r"^\d+$")
_LEADING_ZERO_RE = re.compile(r"^0\d")
_MULTI_DOT_RE = re.compile(r"^\d+(?:\.\d+){2,}$")
_PHONEISH_RE = re.compile(r"^\d{3,}(?:[-\s]\d{2,})+$")

_PERCENT_RE = re.compile(r"%")
_MINUS_BEFORE_DIGIT_RE = re.compile(r"(?<!\w)[-−–—](?=\d)")
_CURRENCY_SYMBOL_RE = re.compile(r"[€$]")


@dataclass(frozen=True)
class Transformation:
    """One normalization rule application or deliberate skip."""

    rule_id: str
    category: str
    input_span: str
    output_span: str
    applied: bool
    skip_reason: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _polish_noun_form(n: float | int, forms: tuple[str, str, str]) -> str:
    """Select singular / paucal / genitive-plural for a Polish count noun."""
    singular, paucal, genitive = forms
    if isinstance(n, float) and not n.is_integer():
        return genitive
    value = int(n)
    if value == 1:
        return singular
    mod100 = value % 100
    mod10 = value % 10
    if mod100 in (12, 13, 14):
        return genitive
    if mod10 in (2, 3, 4):
        return paucal
    return genitive


def _scale_form(n: int, forms: tuple[str, str, str]) -> str:
    return _polish_noun_form(n, forms)


def _parse_below_thousand(tokens: list[str], start: int) -> tuple[int | None, int]:
    """Parse nominative cardinal < 1000. Returns (value, end_index)."""
    i = start
    total = 0
    consumed = False

    if i < len(tokens) and tokens[i] in _NOM_HUNDREDS:
        total += _NOM_HUNDREDS[tokens[i]]
        i += 1
        consumed = True

    if i < len(tokens) and tokens[i] in _NOM_TEENS:
        total += _NOM_TEENS[tokens[i]]
        i += 1
        return total, i

    if i < len(tokens) and tokens[i] in _NOM_TENS:
        total += _NOM_TENS[tokens[i]]
        i += 1
        consumed = True
        if i < len(tokens) and tokens[i] in _NOM_UNITS and tokens[i] not in _STANDALONE_ONE:
            # Allow jeden after tens: dwadzieścia jeden
            total += _NOM_UNITS[tokens[i]]
            i += 1
        elif i < len(tokens) and tokens[i] in _STANDALONE_ONE:
            total += _NOM_UNITS[tokens[i]]
            i += 1
        return total, i

    if i < len(tokens) and tokens[i] in _NOM_UNITS:
        total += _NOM_UNITS[tokens[i]]
        i += 1
        consumed = True

    if not consumed:
        return None, start
    return total, i


def _expected_scale_marker(n: int, kind: str) -> str:
    if kind == "thousand":
        forms = ("tysiąc", "tysiące", "tysięcy")
    elif kind == "million":
        forms = ("milion", "miliony", "milionów")
    else:
        forms = ("miliard", "miliardy", "miliardów")
    return _scale_form(n, forms)


def _try_scale(
    tokens: list[str], start: int, kind: str, markers: frozenset[str]
) -> tuple[int | None, int]:
    """Parse [below_thousand] + agreeing scale marker, or bare singular scale."""
    if start >= len(tokens):
        return None, start

    # Bare singular scale word → 1 * scale
    if tokens[start] in markers:
        expected = _expected_scale_marker(1, kind)
        if tokens[start] != expected:
            return None, start
        scale = {"thousand": 1000, "million": 1_000_000, "billion": 1_000_000_000}[kind]
        return scale, start + 1

    small, j = _parse_below_thousand(tokens, start)
    if small is None or j >= len(tokens) or tokens[j] not in markers:
        return None, start
    expected = _expected_scale_marker(small, kind)
    if tokens[j] != expected:
        return None, start
    scale = {"thousand": 1000, "million": 1_000_000, "billion": 1_000_000_000}[kind]
    return small * scale, j + 1


def _parse_cardinal_phrase(
    tokens: list[str],
    start: int,
    *,
    allow_standalone_one: bool,
) -> tuple[str | None, int]:
    """Parse a nominative cardinal (optionally with przecinek decimal)."""
    i = start
    value = 0
    saw_any = False

    for kind, markers in (
        ("billion", _BILLION_FORMS),
        ("million", _MILLION_FORMS),
        ("thousand", _THOUSAND_FORMS),
    ):
        scaled, j = _try_scale(tokens, i, kind, markers)
        if scaled is not None:
            value += scaled
            i = j
            saw_any = True
            # Only one scale group of each kind; continue to smaller scales.
            # After a successful scale, try next smaller kinds from new i.

    rest, j = _parse_below_thousand(tokens, i)
    if rest is not None:
        # Reject duplicated unit-like tails: "dwa dwa"
        if saw_any is False and rest is not None:
            pass
        value += rest
        i = j
        saw_any = True

    if not saw_any:
        return None, start

    # Standalone "jeden"/"jedna"/"jedno" only when allowed (unit context / larger).
    if (
        not allow_standalone_one
        and i - start == 1
        and tokens[start] in _STANDALONE_ONE
        and value == 1
    ):
        return None, start

    # Decimal: … przecinek <below 1000 nominative>
    if i < len(tokens) and tokens[i] == _DECIMAL_WORD:
        frac, j = _parse_below_thousand(tokens, i + 1)
        if frac is None:
            return None, start
        return f"{value},{frac}", j

    return str(value), i


def _parse_year_ordinal_tail(tokens: list[str], start: int) -> tuple[int | None, int]:
    """Parse ordinal tens + optional ordinal unit (year reading)."""
    i = start
    total = 0
    consumed = False

    if i < len(tokens) and tokens[i] in _YEAR_ORDINAL_TENS:
        total += _YEAR_ORDINAL_TENS[tokens[i]]
        i += 1
        consumed = True
        if i < len(tokens) and tokens[i] in _YEAR_ORDINAL_UNITS:
            total += _YEAR_ORDINAL_UNITS[tokens[i]]
            i += 1
        return total, i

    if i < len(tokens) and tokens[i] in _YEAR_ORDINAL_UNITS:
        total += _YEAR_ORDINAL_UNITS[tokens[i]]
        i += 1
        return total, i

    if not consumed:
        return None, start
    return total, i


def _try_parse_year(tokens: list[str], start: int) -> tuple[str | None, int]:
    """Parse spelled year when followed by rok/roku/rokiem."""
    # Need a year word somewhere after the numeric phrase.
    # Pattern: [thousands scale] [ordinal tail] YEAR_WORD
    i = start
    value = 0
    saw = False

    scaled, j = _try_scale(tokens, i, "thousand", _THOUSAND_FORMS)
    if scaled is not None:
        value += scaled
        i = j
        saw = True
    else:
        # Also allow "dwa tysiące" style already handled by _try_scale
        pass

    ord_val, j = _parse_year_ordinal_tail(tokens, i)
    if ord_val is not None:
        value += ord_val
        i = j
        saw = True

    if not saw:
        return None, start
    if not (1000 <= value <= 2999):
        return None, start
    if i >= len(tokens) or tokens[i] not in _YEAR_WORDS:
        return None, start
    # Consume through year word? Keep year word; only replace the number span.
    return str(value), i


def _looks_ambiguous_digit_token(tok: str) -> bool:
    if _MULTI_DOT_RE.fullmatch(tok):
        return True
    if _LEADING_ZERO_RE.match(tok):
        return True
    # Thousands-like: exactly one separator and 3 fractional digits
    if re.fullmatch(r"\d{1,3}[.,]\d{3}", tok):
        return True
    return False


def _unify_digit_decimal(tok: str) -> str | None:
    """Rewrite single-dot decimals (non-thousands-like) to Polish comma."""
    if _looks_ambiguous_digit_token(tok):
        return None
    m = re.fullmatch(r"(\d+)\.(\d{1,2}|\d{4,})", tok)
    if not m:
        return None
    return f"{m.group(1)},{m.group(2)}"


def _next_is_supported_unit(tokens: list[str], index: int) -> bool:
    return index < len(tokens) and tokens[index] in _UNIT_ABBREVS


def _pre_symbol_pass(
    text: str,
    enabled: frozenset[str],
    trace: list[Transformation],
) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.casefold()

    if RULE_PERCENT in enabled:
        if _PERCENT_RE.search(text):
            new = _PERCENT_RE.sub(" procent ", text)
            if new != text:
                trace.append(
                    Transformation(
                        rule_id=RULE_PERCENT,
                        category="percent",
                        input_span="%",
                        output_span="procent",
                        applied=True,
                    )
                )
                text = new

    if RULE_CURRENCY_SYMBOL in enabled:
        def _curr_sub(m: re.Match[str]) -> str:
            sym = m.group(0)
            out = {"€": " eur ", "$": " usd "}[sym]
            trace.append(
                Transformation(
                    rule_id=RULE_CURRENCY_SYMBOL,
                    category="unit",
                    input_span=sym,
                    output_span=out.strip(),
                    applied=True,
                )
            )
            return out

        text = _CURRENCY_SYMBOL_RE.sub(_curr_sub, text)

    if RULE_MINUS in enabled:
        if _MINUS_BEFORE_DIGIT_RE.search(text):
            new = _MINUS_BEFORE_DIGIT_RE.sub(" minus ", text)
            if new != text:
                trace.append(
                    Transformation(
                        rule_id=RULE_MINUS,
                        category="number",
                        input_span="-",
                        output_span="minus",
                        applied=True,
                    )
                )
                text = new

    return _WHITESPACE_RE.sub(" ", text).strip()


def _rewrite_tokens(
    tokens: list[str],
    enabled: frozenset[str],
    trace: list[Transformation],
) -> list[str]:
    out: list[str] = []
    i = 0
    n = len(tokens)

    while i < n:
        tok = tokens[i]

        # Oblique skip notice (once per token)
        if tok in _OBLIQUE_NUMBERISH:
            trace.append(
                Transformation(
                    rule_id=RULE_CARDINAL,
                    category="number",
                    input_span=tok,
                    output_span=tok,
                    applied=False,
                    skip_reason="oblique_or_unsupported_form",
                )
            )
            out.append(tok)
            i += 1
            continue

        # Brand bigrams
        if RULE_BRAND in enabled and i + 1 < n:
            pair = (tok, tokens[i + 1])
            if pair in _BRAND_BIGRAMS:
                canon = _BRAND_BIGRAMS[pair]
                span = f"{tok} {tokens[i + 1]}"
                trace.append(
                    Transformation(
                        rule_id=RULE_BRAND,
                        category="brand",
                        input_span=span,
                        output_span=canon,
                        applied=True,
                    )
                )
                out.append(canon)
                i += 2
                continue

        # Digit tokens: optional decimal unify
        if _DIGIT_RE.fullmatch(tok) or _MULTI_DOT_RE.fullmatch(tok):
            if RULE_DIGIT_DECIMAL in enabled:
                unified = _unify_digit_decimal(tok)
                if unified is not None and unified != tok:
                    trace.append(
                        Transformation(
                            rule_id=RULE_DIGIT_DECIMAL,
                            category="number",
                            input_span=tok,
                            output_span=unified,
                            applied=True,
                        )
                    )
                    out.append(unified)
                    i += 1
                    continue
                if _looks_ambiguous_digit_token(tok):
                    trace.append(
                        Transformation(
                            rule_id=RULE_DIGIT_DECIMAL,
                            category="number",
                            input_span=tok,
                            output_span=tok,
                            applied=False,
                            skip_reason="ambiguous_separator_or_leading_zero",
                        )
                    )
            out.append(tok)
            i += 1
            continue

        # Year phrase (before generic cardinal)
        if RULE_YEAR in enabled:
            year_tok, j = _try_parse_year(tokens, i)
            if year_tok is not None and j > i:
                span = " ".join(tokens[i:j])
                trace.append(
                    Transformation(
                        rule_id=RULE_YEAR,
                        category="number",
                        input_span=span,
                        output_span=year_tok,
                        applied=True,
                    )
                )
                out.append(year_tok)
                i = j
                continue

        # Spelled cardinal / decimal
        if RULE_CARDINAL in enabled or RULE_DECIMAL in enabled:
            allow_one = _next_is_supported_unit(tokens, i + 1)
            rewritten, j = _parse_cardinal_phrase(
                tokens, i, allow_standalone_one=True
            )
            if rewritten is not None and j > i:
                # Reject bare nominative "jeden/jedna/jedno" unless a unit follows.
                if (
                    j == i + 1
                    and tokens[i] in _STANDALONE_ONE
                    and not allow_one
                ):
                    rewritten = None
                else:
                    span = " ".join(tokens[i:j])
                    is_decimal = "," in rewritten
                    rule = RULE_DECIMAL if is_decimal else RULE_CARDINAL
                    if rule not in enabled:
                        out.append(tok)
                        i += 1
                        continue
                    trace.append(
                        Transformation(
                            rule_id=rule,
                            category="number",
                            input_span=span,
                            output_span=rewritten,
                            applied=True,
                        )
                    )
                    out.append(rewritten)
                    i = j
                    continue

        # Unit abbreviations after a numeric token
        if RULE_UNIT in enabled and tok in _UNIT_ABBREVS and out:
            prev = out[-1]
            num_match = re.fullmatch(r"(\d+)(?:[,.](\d+))?", prev)
            if num_match:
                whole = int(num_match.group(1))
                frac = num_match.group(2)
                amount: float | int
                if frac:
                    amount = float(f"{whole}.{frac}")
                else:
                    amount = whole
                expansion = _polish_noun_form(amount, _UNIT_ABBREVS[tok])
                trace.append(
                    Transformation(
                        rule_id=RULE_UNIT,
                        category="unit",
                        input_span=tok,
                        output_span=expansion,
                        applied=True,
                    )
                )
                out.append(expansion)
                i += 1
                continue

        out.append(tok)
        i += 1

    return out


def normalize_with_trace(
    text: str,
    *,
    enabled_rules: frozenset[str] | set[str] | None = None,
) -> tuple[str, list[Transformation]]:
    """Normalize text and return ``(normalized, transformations)``.

    The transformation list does not affect the normalized string beyond the
    rules that produced it; scoring must use the returned string only.
    """
    if not isinstance(text, str):
        raise TypeError(f"expected str, got {type(text).__name__}")

    enabled = frozenset(enabled_rules) if enabled_rules is not None else ALL_RULES
    unknown = enabled - ALL_RULES
    if unknown:
        raise ValueError(f"unknown normalization rules: {sorted(unknown)}")

    trace: list[Transformation] = []
    pre = _pre_symbol_pass(text, enabled, trace)
    # Frozen basic pass (idempotent w.r.t. NFC/casefold already applied).
    basic = normalize_pl_basic_v1(pre)
    tokens = basic.split() if basic else []
    rewritten = _rewrite_tokens(tokens, enabled, trace)
    out = _WHITESPACE_RE.sub(" ", " ".join(rewritten)).strip()
    return out, trace


def normalize_pl_wer_v1(
    text: str,
    *,
    enabled_rules: frozenset[str] | set[str] | None = None,
) -> str:
    """Primary v2 normalizer. Single code path via ``normalize_with_trace``."""
    normalized, _trace = normalize_with_trace(text, enabled_rules=enabled_rules)
    return normalized


def is_pl_wer_number_token(token: str) -> bool:
    """True if token is digit-like or a nominative number lexicon entry."""
    if _DIGIT_RE.fullmatch(token):
        return True
    if token == _DECIMAL_WORD:
        return True
    if token in _NOM_UNITS or token in _NOM_TEENS or token in _NOM_TENS:
        return True
    if token in _NOM_HUNDREDS or token in _THOUSAND_FORMS:
        return True
    if token in _MILLION_FORMS or token in _BILLION_FORMS:
        return True
    if token in _YEAR_ORDINAL_UNITS or token in _YEAR_ORDINAL_TENS:
        return True
    if token == "minus":
        return True
    return False
