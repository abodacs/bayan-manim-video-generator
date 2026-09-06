"""Language profiles: digit style, Arabic font, and dialect lexicon as data.

Three profiles ship today (``msa-western`` default, ``msa-arabic-indic``,
``egyptian``); adding a fourth is a data addition, not a code change. The
profile pass is pure: plan + profile name in, normalized plan out. It only
swaps digits and lexicon phrases -- shaping and bidi stay in the Arabic
helper at render time.

The ``egyptian`` profile deliberately uses Western digits: Egyptian
textbooks predominantly print Western digits (locked judgment; revisit only
with teacher-review evidence).
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, Field

from bayan.pipeline.models import LessonPlan

WESTERN_DIGITS: Final[str] = "0123456789"
ARABIC_INDIC_DIGITS: Final[str] = "\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669"
ARABIC_DECIMAL_SEPARATOR: Final[str] = "\u066b"
WESTERN_DECIMAL_SEPARATOR: Final[str] = "."

# Both families ship in the container image via the Debian fonts-noto-core
# package; keep this list in sync with the Dockerfile.
AVAILABLE_FONTS: Final[tuple[str, ...]] = ("Noto Sans Arabic", "Noto Naskh Arabic")


class DigitStyle(StrEnum):
    """The digit family a profile renders numbers with."""

    western = "western"
    arabic_indic = "arabic-indic"


class LanguageProfile(BaseModel):
    """Typed profile data: name, digit style, font, and dialect lexicon."""

    name: str
    digit_style: DigitStyle
    font: str
    lexicon: dict[str, str] = Field(default_factory=dict)

    @property
    def expected_digits(self) -> str:
        """The digit characters this profile expects in on-screen text."""
        return WESTERN_DIGITS if self.digit_style is DigitStyle.western else ARABIC_INDIC_DIGITS


# MSA -> Egyptian pedagogical phrase mappings, applied to on-screen text only.
EGYPTIAN_LEXICON: Final[dict[str, str]] = {
    "نلاحظ أن": "هنلاحظ إن",
    "يمكن أن نكتب": "ممكن نكتب",
    "ما هي قيمة": "إيه قيمة",
    "لدينا": "عندنا",
    "إذن": "يبقى",
    "على سبيل المثال": "مثلاً",
}

PROFILES: Final[dict[str, LanguageProfile]] = {
    "msa-western": LanguageProfile(
        name="msa-western",
        digit_style=DigitStyle.western,
        font="Noto Sans Arabic",
    ),
    "msa-arabic-indic": LanguageProfile(
        name="msa-arabic-indic",
        digit_style=DigitStyle.arabic_indic,
        font="Noto Sans Arabic",
    ),
    "egyptian": LanguageProfile(
        name="egyptian",
        digit_style=DigitStyle.western,
        font="Noto Naskh Arabic",
        lexicon=EGYPTIAN_LEXICON,
    ),
}


class UnknownProfileError(ValueError):
    """The profile name is not one of the known profiles."""

    def __init__(self, name: str) -> None:
        known = ", ".join(sorted(PROFILES))
        super().__init__(f"Unknown language profile {name!r}. Known profiles: {known}.")
        self.name = name


def get_profile(name: str) -> LanguageProfile:
    """Return the typed profile for ``name``; unknown names raise a typed error."""
    try:
        return PROFILES[name]
    except KeyError:
        raise UnknownProfileError(name) from None


def normalize_digits(text: str, *, style: DigitStyle) -> str:
    """Convert digits between Western and Arabic-Indic, both directions.

    Non-digit characters are never touched. Moving toward Arabic-Indic turns
    a decimal point into ``٫`` only between two digits, so sentences and
    identifiers keep their periods.
    """
    if style == DigitStyle.western:
        table = str.maketrans(
            dict(zip(ARABIC_INDIC_DIGITS, WESTERN_DIGITS, strict=True))
            | {ARABIC_DECIMAL_SEPARATOR: WESTERN_DECIMAL_SEPARATOR}
        )
        return text.translate(table)

    table = str.maketrans(dict(zip(WESTERN_DIGITS, ARABIC_INDIC_DIGITS, strict=True)))
    text = text.translate(table)
    return re.sub(r"(?<=\d)\.(?=\d)", ARABIC_DECIMAL_SEPARATOR, text)


def apply_lexicon(text: str, lexicon: dict[str, str]) -> str:
    """Apply MSA -> dialect phrase mappings to on-screen text."""
    for source, replacement in lexicon.items():
        text = text.replace(source, replacement)
    return text


def normalize_plan(plan: LessonPlan, profile_name: str) -> LessonPlan:
    """Normalize a validated plan's on-screen text for the profile (pure)."""
    profile = get_profile(profile_name)
    beats = [
        beat.model_copy(
            update={
                "on_screen_text": apply_lexicon(
                    normalize_digits(beat.on_screen_text, style=profile.digit_style),
                    profile.lexicon,
                )
            }
        )
        for beat in plan.beats
    ]
    return plan.model_copy(update={"beats": beats, "profile": profile.name})


def digit_rule(profile: LanguageProfile) -> str:
    """The coder-prompt sentence describing the profile's digit style."""
    if profile.digit_style is DigitStyle.western:
        return "Digits: write numbers with Western digits (0-9)."
    return "Digits: write numbers with Arabic-Indic digits (\u0660-\u0669)."


def lexicon_rule(profile: LanguageProfile) -> str:
    """The coder-prompt sentence describing the profile's dialect phrasing."""
    if not profile.lexicon:
        return "Phrasing: use Modern Standard Arabic."
    mappings = "; ".join(f"{source} -> {dialect}" for source, dialect in profile.lexicon.items())
    return f"Phrasing: prefer these dialect phrasings in on-screen text: {mappings}."
