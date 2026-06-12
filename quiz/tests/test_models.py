from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

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


class Select2CodeSearchTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.editor = create_user(
            username='s2editor', user_permissions=('edit_own_quiz',))
        cls.question = create_question(
            title='Python loops', code='pyloops1',
            authors=(cls.editor.profile,))

    def test_search_by_code_prefix(self):
        self.client.force_login(self.editor)
        resp = self.client.get(
            reverse('quiz_question_select2'), {'term': 'pyloops'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        ids = [r['id'] for r in data['results']]
        self.assertIn(self.question.id, ids)

    def test_result_text_includes_code(self):
        self.client.force_login(self.editor)
        resp = self.client.get(
            reverse('quiz_question_select2'), {'term': 'pyloops1'})
        data = resp.json()
        result = next(r for r in data['results']
                      if r['id'] == self.question.id)
        self.assertIn('pyloops1', result['text'])


class QuestionBankCodeSearchTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.editor = create_user(
            username='bankcodeeditor', user_permissions=('edit_own_quiz',))
        cls.question = create_question(
            title='Mutable types', code='muttype1',
            authors=(cls.editor.profile,))
        cls.other = create_question(
            title='Immutable types', code='immtype1',
            authors=(cls.editor.profile,))

    def test_bank_search_by_code(self):
        self.client.force_login(self.editor)
        resp = self.client.get(
            reverse('quiz_question_bank'), {'search': 'muttype1'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'muttype1')
        self.assertNotContains(resp, 'immtype1')


class QuizNoCategoryLevelTest(TestCase):
    def test_quiz_has_no_category_field(self):
        self.assertFalse(hasattr(Quiz, 'category'))

    def test_quiz_has_no_level_field(self):
        self.assertFalse(hasattr(Quiz, 'level'))

    def test_create_quiz_without_category_level(self):
        quiz = Quiz.objects.create(code='testnocatlvl', name='Test')
        self.assertEqual(quiz.name, 'Test')


class QuizListNoCategoryLevelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.quiz = create_quiz(code='listtest1')

    def test_list_renders_without_category_level_filters(self):
        resp = self.client.get(reverse('quiz_list'))
        self.assertEqual(resp.status_code, 200)
        # Category and level filter dropdowns must be gone
        self.assertNotContains(resp, 'name="category"')
        self.assertNotContains(resp, 'name="level"')
        # Quiz name still appears
        self.assertContains(resp, 'listtest1')


class QuizEditDynamicFormsetTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.editor = create_user(
            username='dyneditor', user_permissions=('edit_own_quiz',))
        cls.q1 = create_question(title='dyn q1', code='dynq1',
                                  authors=(cls.editor.profile,))
        cls.q2 = create_question(title='dyn q2', code='dynq2',
                                  authors=(cls.editor.profile,))
        cls.quiz = create_quiz(code='dynquiz1',
                               questions=((cls.q1, 2.0), (cls.q2, 1.0)))
        cls.quiz.authors.add(cls.editor.profile)

    def test_create_page_has_empty_formset_and_template_row(self):
        self.client.force_login(self.editor)
        resp = self.client.get(reverse('quiz_create'))
        self.assertEqual(resp.status_code, 200)
        # No pre-filled rows (extra=0)
        self.assertNotContains(resp, 'question_links-0-question')
        # Management form present
        self.assertContains(resp, 'id_question_links-TOTAL_FORMS')
        # Template row for JS cloning
        self.assertContains(resp, '__prefix__')
        # Add button
        self.assertContains(resp, 'add-question-btn')

    def test_create_quiz_with_questions_via_post(self):
        self.client.force_login(self.editor)
        resp = self.client.post(reverse('quiz_create'), {
            'code': 'postquiz1',
            'name': 'Post Quiz',
            'result_feedback': 'full',
            'question_links-TOTAL_FORMS': '2',
            'question_links-INITIAL_FORMS': '0',
            'question_links-MIN_NUM_FORMS': '0',
            'question_links-MAX_NUM_FORMS': '1000',
            'question_links-0-question': self.q1.id,
            'question_links-0-points': '2.0',
            'question_links-0-order': '1',
            'question_links-1-question': self.q2.id,
            'question_links-1-points': '1.0',
            'question_links-1-order': '2',
        })
        self.assertEqual(resp.status_code, 302)
        quiz = Quiz.objects.get(code='postquiz1')
        self.assertEqual(quiz.question_links.count(), 2)
        self.assertEqual(
            list(quiz.question_links.order_by('order')
                 .values_list('question_id', flat=True)),
            [self.q1.id, self.q2.id])

    def test_edit_page_shows_existing_question_rows(self):
        self.client.force_login(self.editor)
        resp = self.client.get(reverse('quiz_edit', kwargs={'quiz': 'dynquiz1'}))
        self.assertEqual(resp.status_code, 200)
        # Existing rows rendered
        self.assertContains(resp, 'question_links-0-question')
        self.assertContains(resp, 'question_links-1-question')
        # Template row still present for adding new questions
        self.assertContains(resp, '__prefix__')
