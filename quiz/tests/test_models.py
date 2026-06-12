from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.test import TestCase

from quiz.models import Quiz, QuizCategory, QuizQuestion
from quiz.tests.util import (create_organization, create_question, create_quiz,
                             create_user)


class QuizQuestionTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = create_user(
            username='staff', user_permissions=('edit_all_quiz',))
        cls.teacher = create_user(
            username='teacher', user_permissions=('edit_own_quiz',))
        cls.other_teacher = create_user(
            username='other_teacher', user_permissions=('edit_own_quiz',))
        cls.student = create_user(username='student')
        cls.category = QuizCategory.objects.create(
            name='Python basics', slug='python-basics')
        cls.question = create_question(
            title='loops', category=cls.category,
            authors=(cls.teacher.profile,))

    def test_str(self):
        # create_question auto-generates code from title: 'loops' -> code='loops'
        self.assertEqual(str(self.question), 'loops: loops')

    def test_grade_delegates_to_grading_engine(self):
        self.assertEqual(self.question.grade(0), (1.0, True))
        self.assertEqual(self.question.grade(1), (0.0, False))

    def test_editable_by_author_and_staff_only(self):
        self.assertTrue(self.question.is_editable_by(self.teacher))
        self.assertTrue(self.question.is_editable_by(self.staff))
        self.assertFalse(self.question.is_editable_by(self.other_teacher))
        self.assertFalse(self.question.is_editable_by(self.student))
        self.assertFalse(self.question.is_editable_by(AnonymousUser()))

    def test_curator_can_edit(self):
        self.question.curators.add(self.other_teacher.profile)
        self.assertTrue(self.question.is_editable_by(self.other_teacher))

    def test_bank_visibility(self):
        self.assertTrue(self.question.is_visible_in_bank(self.teacher))
        self.assertTrue(self.question.is_visible_in_bank(self.staff))
        self.assertFalse(self.question.is_visible_in_bank(self.other_teacher))
        self.question.is_public = True
        self.assertTrue(self.question.is_visible_in_bank(self.other_teacher))
        self.assertFalse(self.question.is_visible_in_bank(self.student))


class QuizAccessTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = create_user(
            username='qstaff', user_permissions=('edit_all_quiz',))
        cls.author = create_user(
            username='qauthor', user_permissions=('edit_own_quiz',))
        cls.tester = create_user(username='qtester')
        cls.student = create_user(username='qstudent')
        cls.org_member = create_user(username='qorguser')
        cls.org = create_organization(name='testorg', admins=())
        cls.org_member.profile.organizations.add(cls.org)

        cls.public = create_quiz(code='public')
        cls.private = create_quiz(
            code='private', is_public=False,
            authors=(cls.author.profile,), testers=(cls.tester.profile,))
        cls.org_quiz = create_quiz(
            code='orgquiz', is_organization_private=True,
            organizations=(cls.org,))

    def test_public_quiz_accessible_to_everyone(self):
        self.assertTrue(self.public.is_accessible_by(AnonymousUser()))
        self.assertTrue(self.public.is_accessible_by(self.student))

    def test_private_quiz_access(self):
        self.assertFalse(self.private.is_accessible_by(self.student))
        self.assertFalse(self.private.is_accessible_by(AnonymousUser()))
        self.assertTrue(self.private.is_accessible_by(self.author))
        self.assertTrue(self.private.is_accessible_by(self.tester))
        self.assertTrue(self.private.is_accessible_by(self.staff))

    def test_org_private_quiz_access(self):
        self.assertTrue(self.org_quiz.is_accessible_by(self.org_member))
        self.assertFalse(self.org_quiz.is_accessible_by(self.student))
        self.assertFalse(self.org_quiz.is_accessible_by(AnonymousUser()))

    def test_editable_by(self):
        self.assertTrue(self.private.is_editable_by(self.author))
        self.assertTrue(self.private.is_editable_by(self.staff))
        self.assertFalse(self.private.is_editable_by(self.tester))
        self.assertFalse(self.private.is_editable_by(self.student))

    def test_get_visible_quizzes_matrix(self):
        def codes(user):
            return set(Quiz.get_visible_quizzes(user).values_list(
                'code', flat=True))

        self.assertEqual(codes(AnonymousUser()), {'public'})
        self.assertEqual(codes(self.student), {'public'})
        self.assertEqual(codes(self.org_member), {'public', 'orgquiz'})
        self.assertEqual(codes(self.tester), {'public', 'private'})
        self.assertEqual(codes(self.author), {'public', 'private'})
        self.assertEqual(codes(self.staff), {'public', 'private', 'orgquiz'})

    def test_total_points(self):
        question_a = create_question(title='qa')
        question_b = create_question(title='qb')
        quiz = create_quiz(
            code='points', questions=((question_a, 1.5), (question_b, 2.0)))
        self.assertEqual(quiz.total_points, 3.5)
        self.assertEqual(create_quiz(code='nopoints').total_points, 0.0)


class QuizQuestionCodeTest(TestCase):
    def _make(self, code, **kwargs):
        defaults = {
            'type': 'MC', 'title': code, 'content': 'body',
            'choices': ['a', 'b'], 'correct_answers': 0,
        }
        defaults.update(kwargs)
        return QuizQuestion(code=code, **defaults)

    def test_valid_code_accepted(self):
        q = self._make('py101q1')
        q.full_clean()  # should not raise

    def test_code_required(self):
        q = QuizQuestion(
            type='MC', title='t', content='b',
            choices=['a', 'b'], correct_answers=0)
        with self.assertRaises(ValidationError):
            q.full_clean()

    def test_invalid_code_rejected(self):
        for bad in ('has_underscore', 'Has-Upper', 'has space', ''):
            with self.subTest(code=bad):
                q = self._make(bad)
                with self.assertRaises(ValidationError):
                    q.full_clean()

    def test_duplicate_code_rejected(self):
        from django.db import IntegrityError
        QuizQuestion.objects.create(
            code='dupcode', type='MC', title='dup',
            content='body', choices=['a', 'b'], correct_answers=0)
        q = self._make('dupcode', title='dup2')
        with self.assertRaises(IntegrityError):
            q.save()

    def test_str_includes_code(self):
        q = self._make('mycode')
        q.title = 'My title'
        self.assertEqual(str(q), 'mycode: My title')


class QuizCodeValidatorTest(TestCase):
    def test_underscore_rejected_by_new_validator(self):
        from django.core.exceptions import ValidationError
        q = Quiz(
            code='has_underscore', name='test',
        )
        with self.assertRaises(ValidationError):
            q.full_clean()

    def test_lowercase_alphanumeric_accepted(self):
        q = Quiz(code='validcode123', name='test')
        q.full_clean()  # should not raise
