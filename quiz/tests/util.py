import re as _re

from judge.models.tests.util import create_organization, create_user  # noqa: F401
from quiz.models import Quiz, QuizCategory, QuizQuestion, QuizQuestionLink


def create_question(title='question', qtype='MC', code=None, **kwargs):
    if code is None:
        base = _re.sub('[^a-z0-9]', '', title.lower()) or 'q1'
        code = base
        suffix = 2
        while QuizQuestion.objects.filter(code=code).exists():
            code = f'{base}{suffix}'
            suffix += 1
    defaults = {
        'content': 'Body of %s' % title,
        'choices': [
            {'text': 'a', 'explanation': ''},
            {'text': 'b', 'explanation': ''},
            {'text': 'c', 'explanation': ''},
            {'text': 'd', 'explanation': ''},
        ],
        'correct_answers': 0,
    }
    defaults.update(kwargs)
    authors = defaults.pop('authors', ())
    curators = defaults.pop('curators', ())
    question = QuizQuestion.objects.create(
        code=code, title=title, type=qtype, **defaults)
    question.authors.set(authors)
    question.curators.set(curators)
    return question


def create_quiz(code='quiz1', questions=(), **kwargs):
    defaults = {'name': code, 'is_public': True}
    defaults.update(kwargs)
    for field in ('authors', 'curators', 'testers', 'organizations'):
        defaults.pop(field, None)
    quiz = Quiz.objects.create(code=code, **defaults)
    for field in ('authors', 'curators', 'testers', 'organizations'):
        if field in kwargs:
            getattr(quiz, field).set(kwargs[field])
    for order, (question, points) in enumerate(questions):
        QuizQuestionLink.objects.create(
            quiz=quiz, question=question, points=points, order=order)
    return quiz
