"""Versioned Polish text normalizers for ASR evaluation."""

from __future__ import annotations

import re
import unicodedata

NORMALIZATION_VERSION = "pl_basic_v1"
NUMBERS_NORMALIZATION_VERSION = "pl_numbers_v1"

# Private-use placeholders so decimal separators survive punctuation stripping.
_DECIMAL_COMMA = "\ue000"
_DECIMAL_DOT = "\ue001"

_WHITESPACE_RE = re.compile(r"\s+")
_DIGIT_COMMA_DIGIT_RE = re.compile(r"(?<=\d),(?=\d)")
_DIGIT_DOT_DIGIT_RE = re.compile(r"(?<=\d)\.(?=\d)")
_DIGIT_DECIMAL_DOT_RE = re.compile(r"(\d+)\.(\d+)")

# ---------------------------------------------------------------------------
# pl_numbers_v1: limited spelled-number lexicon (casefolded, after pl_basic_v1)
# Intentionally collapses common case/gender forms for sensitivity analysis.
# See docs/evaluation_protocol.md for inflection limitations.
# ---------------------------------------------------------------------------

_UNITS: dict[str, int] = {
    "zero": 0,
    "jeden": 1,
    "jednego": 1,
    "jednemu": 1,
    "jednym": 1,
    "jedną": 1,
    "jednej": 1,
    "jedno": 1,
    "jedna": 1,
    "dwa": 2,
    "dwóch": 2,
    "dwóm": 2,
    "dwoma": 2,
    "dwie": 2,
    "dwu": 2,
    "trzy": 3,
    "trzech": 3,
    "trzem": 3,
    "trzema": 3,
    "cztery": 4,
    "czterech": 4,
    "czterem": 4,
    "czterema": 4,
    "pięć": 5,
    "pięciu": 5,
    "sześć": 6,
    "sześciu": 6,
    "siedem": 7,
    "siedmiu": 7,
    "osiem": 8,
    "ośmiu": 8,
    "dziewięć": 9,
    "dziewięciu": 9,
}

# Ordinal-ish stems used in year readings (dwudziesty szósty / dwudziestym szóstym).
_ORDINAL_UNITS: dict[str, int] = {
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

_TEENS: dict[str, int] = {
    "dziesięć": 10,
    "dziesięciu": 10,
    "jedenaście": 11,
    "jedenastu": 11,
    "dwanaście": 12,
    "dwunastu": 12,
    "trzynaście": 13,
    "trzynastu": 13,
    "czternaście": 14,
    "czternastu": 14,
    "piętnaście": 15,
    "piętnastu": 15,
    "szesnaście": 16,
    "szesnastu": 16,
    "siedemnaście": 17,
    "siedemnastu": 17,
    "osiemnaście": 18,
    "osiemnastu": 18,
    "dziewiętnaście": 19,
    "dziewiętnastu": 19,
}

_TENS: dict[str, int] = {
    "dwadzieścia": 20,
    "dwudziestu": 20,
    "dwudziesty": 20,
    "dwudziestego": 20,
    "dwudziestym": 20,
    "dwudziesta": 20,
    "dwudziestej": 20,
    "dwudziestą": 20,
    "trzydzieści": 30,
    "trzydziestu": 30,
    "trzydziesty": 30,
    "trzydziestego": 30,
    "trzydziestym": 30,
    "trzydziesta": 30,
    "trzydziestej": 30,
    "trzydziestą": 30,
    "czterdzieści": 40,
    "czterdziestu": 40,
    "czterdziesty": 40,
    "czterdziestego": 40,
    "czterdziestym": 40,
    "czterdziesta": 40,
    "czterdziestej": 40,
    "czterdziestą": 40,
    "pięćdziesiąt": 50,
    "pięćdziesięciu": 50,
    "pięćdziesiąty": 50,
    "pięćdziesiątego": 50,
    "pięćdziesiątym": 50,
    "pięćdziesiąta": 50,
    "pięćdziesiątej": 50,
    "pięćdziesiątą": 50,
    "sześćdziesiąt": 60,
    "sześćdziesięciu": 60,
    "sześćdziesiąty": 60,
    "sześćdziesiątego": 60,
    "sześćdziesiątym": 60,
    "sześćdziesiąta": 60,
    "sześćdziesiątej": 60,
    "sześćdziesiątą": 60,
    "siedemdziesiąt": 70,
    "siedemdziesięciu": 70,
    "siedemdziesiąty": 70,
    "siedemdziesiątego": 70,
    "siedemdziesiątym": 70,
    "siedemdziesiąta": 70,
    "siedemdziesiątej": 70,
    "siedemdziesiątą": 70,
    "osiemdziesiąt": 80,
    "osiemdziesięciu": 80,
    "osiemdziesiąty": 80,
    "osiemdziesiątego": 80,
    "osiemdziesiątym": 80,
    "osiemdziesiąta": 80,
    "osiemdziesiątej": 80,
    "osiemdziesiątą": 80,
    "dziewięćdziesiąt": 90,
    "dziewięćdziesięciu": 90,
    "dziewięćdziesiąty": 90,
    "dziewięćdziesiątego": 90,
    "dziewięćdziesiątym": 90,
    "dziewięćdziesiąta": 90,
    "dziewięćdziesiątej": 90,
    "dziewięćdziesiątą": 90,
}

_HUNDREDS: dict[str, int] = {
    "sto": 100,
    "stu": 100,
    "dwieście": 200,
    "dwustu": 200,
    "trzysta": 300,
    "trzystu": 300,
    "czterysta": 400,
    "czterystu": 400,
    "pięćset": 500,
    "pięciuset": 500,
    "sześćset": 600,
    "sześciuset": 600,
    "siedemset": 700,
    "siedmiuset": 700,
    "osiemset": 800,
    "ośmiuset": 800,
    "dziewięćset": 900,
    "dziewięciuset": 900,
}

_THOUSAND_MARKERS = frozenset({"tysiąc", "tysiące", "tysięcy", "tysiąca", "tysiącom", "tysiącami", "tysiącach"})
_DECIMAL_WORD = "przecinek"

_SMALL_VALUE_WORDS: dict[str, int] = {}
_SMALL_VALUE_WORDS.update(_UNITS)
_SMALL_VALUE_WORDS.update(_ORDINAL_UNITS)
_SMALL_VALUE_WORDS.update(_TEENS)
_SMALL_VALUE_WORDS.update(_TENS)
_SMALL_VALUE_WORDS.update(_HUNDREDS)

_DIGIT_TOKEN_RE = re.compile(r"^\d+(?:[.,]\d+)?$")


def is_pl_number_token(token: str) -> bool:
    """True if token is a digit form or in the ``pl_numbers_v1`` lexicon."""
    if _DIGIT_TOKEN_RE.fullmatch(token):
        return True
    if token == _DECIMAL_WORD:
        return True
    if token in _SMALL_VALUE_WORDS or token in _THOUSAND_MARKERS:
        return True
    return False


def normalize_pl_basic_v1(text: str) -> str:
    """Normalize text with the frozen ``pl_basic_v1`` protocol.

    Steps (deterministic, no side effects):
    1. Unicode NFC
    2. ``casefold``
    3. Protect decimal separators between digits (``97,5`` / ``97.5``)
    4. Replace Unicode punctuation (category ``P*``) with spaces
    5. Collapse whitespace and strip
    6. Restore protected decimal separators

    Preserves Polish diacritics and digit characters. Does **not** equate
    digit forms with spelled-out numbers (``2026`` ≠ ``dwa tysiące ...``).
    """
    if not isinstance(text, str):
        raise TypeError(f"expected str, got {type(text).__name__}")

    text = unicodedata.normalize("NFC", text)
    text = text.casefold()

    text = _DIGIT_COMMA_DIGIT_RE.sub(_DECIMAL_COMMA, text)
    text = _DIGIT_DOT_DIGIT_RE.sub(_DECIMAL_DOT, text)

    chars: list[str] = []
    for ch in text:
        if unicodedata.category(ch).startswith("P"):
            chars.append(" ")
        else:
            chars.append(ch)
    text = "".join(chars)

    text = text.replace(_DECIMAL_COMMA, ",").replace(_DECIMAL_DOT, ".")
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def _parse_below_thousand(tokens: list[str], start: int) -> tuple[int | None, int]:
    """Parse a number < 1000 starting at ``start``. Returns (value, end_index)."""
    i = start
    total = 0
    consumed = False

    if i < len(tokens) and tokens[i] in _HUNDREDS:
        total += _HUNDREDS[tokens[i]]
        i += 1
        consumed = True

    if i < len(tokens) and tokens[i] in _TEENS:
        total += _TEENS[tokens[i]]
        i += 1
        consumed = True
        return total, i

    if i < len(tokens) and tokens[i] in _TENS:
        total += _TENS[tokens[i]]
        i += 1
        consumed = True
        if i < len(tokens) and tokens[i] in _UNITS:
            total += _UNITS[tokens[i]]
            i += 1
        elif i < len(tokens) and tokens[i] in _ORDINAL_UNITS:
            total += _ORDINAL_UNITS[tokens[i]]
            i += 1
        return total, i

    if i < len(tokens) and tokens[i] in _UNITS:
        total += _UNITS[tokens[i]]
        i += 1
        consumed = True
    elif i < len(tokens) and tokens[i] in _ORDINAL_UNITS:
        total += _ORDINAL_UNITS[tokens[i]]
        i += 1
        consumed = True

    if not consumed:
        return None, start
    return total, i


def _parse_number_phrase(tokens: list[str], start: int) -> tuple[str | None, int]:
    """Parse a spelled number (optionally with ``przecinek`` decimals) → digit token."""
    i = start
    value = 0
    saw_any = False

    # Optional thousands: [small] tysiąc(e)
    thousands_part, j = _parse_below_thousand(tokens, i)
    if (
        thousands_part is not None
        and j < len(tokens)
        and tokens[j] in _THOUSAND_MARKERS
    ):
        value += thousands_part * 1000
        i = j + 1
        saw_any = True
    elif i < len(tokens) and tokens[i] in _THOUSAND_MARKERS:
        # bare "tysiąc" ≈ 1000
        value += 1000
        i += 1
        saw_any = True

    rest, j = _parse_below_thousand(tokens, i)
    if rest is not None:
        value += rest
        i = j
        saw_any = True

    if not saw_any:
        return None, start

    # Decimal: … przecinek <below 1000>
    if i < len(tokens) and tokens[i] == _DECIMAL_WORD:
        frac, j = _parse_below_thousand(tokens, i + 1)
        if frac is None:
            return None, start
        # Canonical Polish decimal comma; keep fractional digits as spoken magnitude
        # e.g. pięć → 5, pięćdziesiąt → 50 (not padded).
        digit = f"{value},{frac}"
        return digit, j

    return str(value), i


def _rewrite_spelled_numbers(text: str) -> str:
    tokens = text.split()
    out: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        # Keep existing digit tokens (possibly with decimal comma/dot).
        if re.fullmatch(r"\d+(?:[.,]\d+)?", tok):
            out.append(tok)
            i += 1
            continue

        if tok in _SMALL_VALUE_WORDS or tok in _THOUSAND_MARKERS:
            rewritten, j = _parse_number_phrase(tokens, i)
            if rewritten is not None and j > i:
                out.append(rewritten)
                i = j
                continue

        out.append(tok)
        i += 1

    return " ".join(out)


def normalize_pl_numbers_v1(text: str) -> str:
    """Sensitivity normalizer: ``pl_basic_v1`` + limited digit↔word unification.

    Not the primary scoring profile. Applied identically to reference and
    hypothesis. Deterministic; no LLM.

    Extra steps after ``pl_basic_v1``:
    1. Unify digit decimals ``97.5`` → ``97,5``
    2. Rewrite covered spelled cardinals / year-like ordinals to digits
    3. Rewrite ``… przecinek …`` decimals to ``N,M``
    4. Collapse whitespace

    **Inflection note:** common case/gender forms of covered number words are
    mapped to the same digit (e.g. ``dwudziesty`` / ``dwudziestym`` → ``20``).
    That hides morphological mistakes inside number phrases on purpose for
    format-sensitivity analysis — see protocol docs.
    """
    text = normalize_pl_basic_v1(text)
    text = _DIGIT_DECIMAL_DOT_RE.sub(r"\1,\2", text)
    text = _rewrite_spelled_numbers(text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text
