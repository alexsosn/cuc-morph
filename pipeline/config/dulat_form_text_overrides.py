"""Overrides for known DULAT form-text parsing inconsistencies."""

from __future__ import annotations

LOOKUP_NORMALIZE = str.maketrans(
    {
        "ʿ": "ʕ",
        "ˤ": "ʕ",
        "ả": "a",
        "ỉ": "i",
        "ủ": "u",
    }
)


def _norm_text(value: str) -> str:
    return (value or "").strip().translate(LOOKUP_NORMALIZE).lower()


def _norm_homonym(value: str) -> str:
    return (value or "").strip().upper()


_FORM_TEXT_ALIAS_OVERRIDES: dict[tuple[str, str, str], tuple[str, ...]] = {
    # /l-s-m/: DULAT form-table parser stores `tslmn`, while attested surface
    # and lexical description use `tlsmn`.
    ("/l-s-m/", "", "tslmn"): ("tlsmn",),
}


def expand_dulat_form_texts(
    *,
    lemma: str,
    homonym: str,
    form_text: str,
) -> tuple[str, ...]:
    """Return source form text plus any curated alias overrides."""
    source = (form_text or "").strip()
    if not source:
        return tuple()
    key = (_norm_text(lemma), _norm_homonym(homonym), _norm_text(source))
    aliases = _FORM_TEXT_ALIAS_OVERRIDES.get(key, tuple())
    out: list[str] = [source]
    for alias in aliases:
        value = (alias or "").strip()
        if value and value not in out:
            out.append(value)
    return tuple(out)
