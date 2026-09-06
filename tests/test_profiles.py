"""Language profile tests: pure digit, lexicon, and plan normalization."""

import pytest

from bayan.pipeline.models import LessonBeat, LessonPlan
from bayan.pipeline.profiles import (
    AVAILABLE_FONTS,
    PROFILES,
    UnknownProfileError,
    apply_lexicon,
    get_profile,
    normalize_digits,
    normalize_plan,
)
from bayan.pipeline.spine import LanguageProfile

MIXED_SENTENCE = "١٢ + 34"


def test_digits_normalize_both_directions():
    for western, arabic in zip("0123456789", "٠١٢٣٤٥٦٧٨٩", strict=True):
        assert normalize_digits(arabic, style="western") == western
        assert normalize_digits(western, style="arabic-indic") == arabic

    assert normalize_digits("١٫٥", style="western") == "1.5"
    assert normalize_digits("1.5", style="arabic-indic") == "١٫٥"

    # Mixed strings: digit runs normalize, operators and Latin words survive.
    assert normalize_digits(MIXED_SENTENCE, style="western") == "12 + 34"
    assert normalize_digits(MIXED_SENTENCE, style="arabic-indic") == "١٢ + ٣٤"
    assert normalize_digits("step1.txt", style="arabic-indic") == "step١.txt"


def test_digits_never_touch_non_digit_arabic():
    assert normalize_digits("مرحبا بكم", style="western") == "مرحبا بكم"
    assert normalize_digits("مرحبا بكم", style="arabic-indic") == "مرحبا بكم"


def test_three_profiles_exist_with_expected_shape():
    assert set(PROFILES) == {member.value for member in LanguageProfile}

    msa_western = get_profile("msa-western")
    msa_indic = get_profile("msa-arabic-indic")
    egyptian = get_profile("egyptian")

    assert msa_western.digit_style == "western"
    assert msa_indic.digit_style == "arabic-indic"
    # Locked judgment: Egyptian textbooks print Western digits.
    assert egyptian.digit_style == "western"

    for profile in (msa_western, msa_indic):
        assert profile.font == "Noto Sans Arabic"
    assert egyptian.font == "Noto Naskh Arabic"
    for profile in (msa_western, msa_indic, egyptian):
        assert profile.font in AVAILABLE_FONTS

    assert len(egyptian.lexicon) >= 5
    for key, profile in PROFILES.items():
        assert profile.name == key
    for source, dialect in egyptian.lexicon.items():
        assert source and dialect
        assert source != dialect
        assert source not in dialect


def test_unknown_profile_error_names_the_valid_choices():
    with pytest.raises(UnknownProfileError) as exc_info:
        get_profile("bogus")

    message = str(exc_info.value)
    assert "bogus" in message
    for name in sorted(PROFILES):
        assert name in message


def _plan_with(text: str) -> LessonPlan:
    return LessonPlan(
        topic="اختبار",
        beats=[LessonBeat(title="الخطوة ١", on_screen_text=text, insight_move="reveal")],
    )


def test_profile_pass_rewrites_plan_on_screen_text():
    plan = _plan_with("نلاحظ أن 12 تساوي 24")

    indic = normalize_plan(plan, "msa-arabic-indic")
    assert "١٢" in indic.beats[0].on_screen_text
    assert indic.beats[0].on_screen_text == "نلاحظ أن ١٢ تساوي ٢٤"

    western = normalize_plan(plan, "msa-western")
    assert western.beats[0].on_screen_text == "نلاحظ أن 12 تساوي 24"

    egyptian = normalize_plan(plan, "egyptian")
    assert egyptian.beats[0].on_screen_text == "هنلاحظ إن 12 تساوي 24"
    assert egyptian.profile == "egyptian"


def test_normalization_is_idempotent():
    plan = _plan_with("نلاحظ أن 12 تساوي 24، على سبيل المثال")

    once = normalize_plan(plan, "egyptian")
    twice = normalize_plan(once, "egyptian")

    assert twice.model_dump() == once.model_dump()


def test_lexicon_replaces_msa_phrases_only_in_on_screen_text():
    lexicon = get_profile("egyptian").lexicon

    assert apply_lexicon("نلاحظ أن الناتج صحيح", lexicon) == "هنلاحظ إن الناتج صحيح"
    # Numbers inside expressions are lexicon-untouched by construction.
    assert apply_lexicon("24", lexicon) == "24"


def test_preflight_digit_expectations_follow_the_profile():
    from bayan.pipeline.preflight import gates_blocked, run_gates

    code = (
        "from manim import *\n"
        "from bayan.utils.arabic_helper import ArabicText\n"
        "\n"
        "class GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        '        ArabicText("الناتج ٢٤")\n'
    )

    western_results = run_gates(code, profile="msa-western")
    assert any("msa-western" in (result.suggestion or "") for result in western_results)

    indic_results = run_gates(code, profile="msa-arabic-indic")
    assert not gates_blocked(indic_results)

    # The expectation is bidirectional: Western digits fail under Arabic-Indic.
    western_code = code.replace("الناتج ٢٤", "الناتج 24")
    indic_failure = run_gates(western_code, profile="msa-arabic-indic")
    assert any("msa-arabic-indic" in (result.suggestion or "") for result in indic_failure)


def test_coder_prompt_carries_digit_and_lexicon_rules():
    from bayan.pipeline.coder import build_coder_prompt

    plan = _plan_with("نلاحظ أن 12")

    _, egyptian_user = build_coder_prompt(plan, "egyptian", ["from manim import *"])
    assert "Western digits (0-9)" in egyptian_user
    assert "هنلاحظ إن" in egyptian_user

    _, indic_user = build_coder_prompt(plan, "msa-arabic-indic", ["from manim import *"])
    assert "Arabic-Indic digits" in indic_user
