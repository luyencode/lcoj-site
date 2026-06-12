"""JSON import format: a list of question objects with explicit fields."""
import json

from quiz import grading
from quiz.importers.base import ParsedQuestion, validate_question


def parse(data):
    """bytes -> list[ParsedQuestion]. File-level failures yield one errored row."""
    try:
        payload = json.loads(data.decode('utf-8'))
    except (UnicodeDecodeError, ValueError) as exc:
        broken = ParsedQuestion(row=0)
        broken.errors.append('Invalid JSON file: %s' % exc)
        return [broken]
    if not isinstance(payload, list):
        broken = ParsedQuestion(row=0)
        broken.errors.append('JSON root must be a list of question objects')
        return [broken]
    questions = []
    for index, entry in enumerate(payload, start=1):
        question = ParsedQuestion(row=index)
        questions.append(question)
        if not isinstance(entry, dict):
            question.errors.append('Entry must be an object')
            continue
        question.code = str(entry.get('code', '') or '').strip()
        question.type = str(entry.get('type', '')).upper()
        question.title = str(entry.get('title', ''))
        question.content = str(entry.get('content', ''))
        question.choices = [str(c) for c in entry.get('choices') or []]
        question.points = entry.get('points', 1.0)
        question.category = str(entry.get('category', '') or '')
        question.level = str(entry.get('level', 'easy') or 'easy')
        question.explanation = str(entry.get('explanation', '') or '')
        question.shuffle = bool(entry.get('shuffle', False))
        question.ma_strategy = str(entry.get(
            'ma_strategy', grading.MA_ALL_OR_NOTHING))
        question.correct = _normalize_correct(question, entry.get('correct'))
        validate_question(question)
    return questions


def _normalize_correct(question, correct):
    if correct is None:
        return None
    if question.type == grading.TF:
        if isinstance(correct, bool):
            return 0 if correct else 1
        question.errors.append('TF correct must be true or false')
        return None
    if question.type == grading.MC:
        if isinstance(correct, int) and \
                0 <= correct < len(question.choices):
            return correct
        question.errors.append('MC correct must be a 0-based choice index')
        return None
    if question.type == grading.MA:
        if isinstance(correct, list) and correct and \
                all(isinstance(i, int) and
                    0 <= i < len(question.choices) for i in correct):
            return sorted(set(correct))
        question.errors.append(
            'MA correct must be a non-empty list of 0-based indices')
        return None
    # SA
    accepted = []
    for item in correct if isinstance(correct, list) else [correct]:
        if isinstance(item, str):
            accepted.append({'text': item, 'case_sensitive': False,
                             'is_regex': False})
        elif isinstance(item, dict) and 'text' in item:
            accepted.append({
                'text': str(item['text']),
                'case_sensitive': bool(item.get('case_sensitive', False)),
                'is_regex': bool(item.get('is_regex', False))})
        else:
            question.errors.append(
                'SA accepted answers must be strings or {text, ...} objects')
            return None
    return accepted
