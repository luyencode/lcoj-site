"""Shared import machinery: normalized question record, 'correct'
spec mini-syntax, and validation. Pure functions - DB only at commit time."""
import dataclasses
import re

from quiz import grading

LEVELS = ('easy', 'medium', 'hard')
TYPES = (grading.MC, grading.MA, grading.TF, grading.SA)
TF_TRUE = ('true', '1', 'dung', 'đúng')
TF_FALSE = ('false', '0', 'sai')

_CODE_RE = re.compile('^[a-z0-9]+$')


@dataclasses.dataclass
class ParsedQuestion:
    row: int
    code: str = ''
    type: str = ''
    title: str = ''
    content: str = ''
    choices: list = dataclasses.field(default_factory=list)
    choice_explanations: list = dataclasses.field(default_factory=list)
    correct: object = None
    points: float = 1.0
    category: str = ''
    level: str = 'easy'
    explanation: str = ''
    shuffle: bool = False
    ma_strategy: str = grading.MA_ALL_OR_NOTHING
    errors: list = dataclasses.field(default_factory=list)

    def as_dict(self):
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


def parse_correct_spec(qtype, spec, num_choices):
    """Parse the human 'correct' syntax. Returns (normalized_value, errors)."""
    spec = ('' if spec is None else str(spec)).strip()
    if qtype == grading.MC:
        try:
            index = int(spec) - 1
        except ValueError:
            return None, ['MC correct answer must be a choice number']
        if not 0 <= index < num_choices:
            return None, ['MC correct answer out of range 1-%d' % num_choices]
        return index, []
    if qtype == grading.TF:
        low = spec.lower()
        if low in TF_TRUE:
            return 0, []
        if low in TF_FALSE:
            return 1, []
        return None, ['TF correct answer must be true or false']
    if qtype == grading.MA:
        try:
            indices = sorted({int(token) - 1 for token in spec.split(',')
                              if token.strip()})
        except ValueError:
            return None, ['MA correct answers must be comma-separated '
                          'choice numbers']
        if not indices:
            return None, ['MA needs at least one correct choice']
        if indices[0] < 0 or indices[-1] >= num_choices:
            return None, ['MA correct answer out of range 1-%d' % num_choices]
        return indices, []
    # SA — each pipe-separated token is a regex pattern (use (?i) for case-insensitive)
    tokens = [t.strip() for t in spec.split('|') if t.strip()]
    if not tokens:
        return None, ['SA needs at least one regex pattern']
    patterns, errors = [], []
    for token in tokens:
        try:
            re.compile(token)
        except re.error as exc:
            errors.append('Invalid regex %r: %s' % (token, exc))
            continue
        patterns.append(token)
    if not patterns and not errors:
        errors.append('SA needs at least one regex pattern')
    return patterns, errors


def correct_to_spec(qtype, correct):
    """Inverse of parse_correct_spec - renders the human syntax."""
    if qtype == grading.MC:
        return str(correct + 1)
    if qtype == grading.TF:
        return 'true' if correct == 0 else 'false'
    if qtype == grading.MA:
        return ','.join(str(i + 1) for i in correct)
    # SA — list of regex pattern strings (or legacy dicts)
    parts = []
    for a in (correct or []):
        if isinstance(a, dict):
            parts.append(a.get('text', ''))
        else:
            parts.append(str(a))
    return ' | '.join(parts)


def validate_question(question):
    """Append problems to question.errors. Call after type-specific parsing."""
    if not question.code or not _CODE_RE.match(question.code):
        question.errors.append(
            'Question code is required and must match ^[a-z0-9]+$')
    if question.type not in TYPES:
        question.errors.append('Unknown question type %r' % (question.type,))
        return
    if not question.title.strip():
        question.errors.append('Missing title')
    if not question.content.strip():
        question.errors.append('Missing question content')
    if question.type in (grading.MC, grading.MA) and \
            len(question.choices) < 2:
        question.errors.append(
            '%s questions need at least 2 choices' % question.type)
    if question.correct is None:
        question.errors.append('Missing correct answer')
    if question.level not in LEVELS:
        question.errors.append('Level must be one of %s' % (LEVELS,))
    try:
        question.points = float(question.points)
    except (TypeError, ValueError):
        question.errors.append('Points must be a number')
    else:
        if question.points < 0:
            question.errors.append('Points must not be negative')
    if question.type == grading.MA and \
            question.ma_strategy not in grading.MA_STRATEGIES:
        question.errors.append(
            'MA strategy must be one of %s' % (grading.MA_STRATEGIES,))
