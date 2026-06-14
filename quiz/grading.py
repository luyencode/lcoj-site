"""Pure grading functions for quiz answers.

No database or Django model imports - everything here is unit-testable
standalone and is re-run verbatim by regrading.

Answer formats by question type:
  MC/TF - int choice index (TF: 0 = True, 1 = False) or None
  MA    - list of int choice indices or None
  SA    - str or None
"""
import re

MC = 'MC'
MA = 'MA'
TF = 'TF'
SA = 'SA'

MA_ALL_OR_NOTHING = 'all_or_nothing'
MA_PARTIAL_CREDIT = 'partial_credit'
MA_RIGHT_MINUS_WRONG = 'right_minus_wrong'
MA_CORRECT_ONLY = 'correct_only'

MA_STRATEGIES = (MA_ALL_OR_NOTHING, MA_PARTIAL_CREDIT, MA_RIGHT_MINUS_WRONG, MA_CORRECT_ONLY)


def grade(question_type, choices, correct_answers, ma_strategy, answer):
    """Grade one answer. Returns (ratio, is_correct) with ratio in [0, 1]."""
    if question_type in (MC, TF):
        return _grade_single(correct_answers, answer)
    if question_type == MA:
        return _grade_multiple(choices, correct_answers, ma_strategy, answer)
    if question_type == SA:
        return _grade_short_answer(correct_answers, answer)
    raise ValueError('unknown question type: %r' % (question_type,))


def _grade_single(correct_answers, answer):
    if answer is None or correct_answers is None:
        return 0.0, False
    if int(answer) == int(correct_answers):
        return 1.0, True
    return 0.0, False


def _grade_multiple(choices, correct_answers, ma_strategy, answer):
    correct_set = {int(i) for i in (correct_answers or [])}
    selected = {int(i) for i in (answer or [])}
    if not correct_set or not selected:
        return 0.0, False
    wrong_set = set(range(len(choices or []))) - correct_set
    cs = len(selected & correct_set)
    ws = len(selected & wrong_set)
    if ma_strategy == MA_PARTIAL_CREDIT:
        penalty = ws / len(wrong_set) if wrong_set else 0.0
        ratio = max(0.0, cs / len(correct_set) - penalty)
    elif ma_strategy == MA_RIGHT_MINUS_WRONG:
        ratio = max(0.0, (cs - ws) / len(correct_set))
    elif ma_strategy == MA_CORRECT_ONLY:
        ratio = cs / len(correct_set)
    else:  # all_or_nothing, also the fallback for unknown values
        ratio = 1.0 if selected == correct_set else 0.0
    return ratio, ratio == 1.0


def _grade_short_answer(correct_answers, answer):
    """SA correct_answers is a list of regex pattern strings.
    Any pattern that fully matches the trimmed answer scores full marks."""
    text = (answer or '').strip()
    if not text:
        return 0.0, False
    for pattern in correct_answers or []:
        # Backward-compat: old format stored dicts with text/is_regex/case_sensitive
        if isinstance(pattern, dict):
            expected = (pattern.get('text') or '').strip()
            flags = 0 if pattern.get('case_sensitive') else re.IGNORECASE
            try:
                if pattern.get('is_regex'):
                    if re.fullmatch(expected, text, flags):
                        return 1.0, True
                elif flags == 0:
                    if text == expected:
                        return 1.0, True
                elif text.lower() == expected.lower():
                    return 1.0, True
            except re.error:
                continue
        else:
            try:
                if re.fullmatch(str(pattern), text):
                    return 1.0, True
            except re.error:
                continue
    return 0.0, False
