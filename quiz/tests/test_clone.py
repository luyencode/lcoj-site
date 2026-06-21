from django.test import TestCase
from django.utils import timezone

from quiz.models import Quiz, QuizQuestionLink
from quiz.tests.util import create_organization, create_question, create_quiz, create_user


class QuizCloneModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cloner = create_user(username='cloner', user_permissions=('edit_own_quiz',))
        cls.other_editor = create_user(username='othercloner', user_permissions=('edit_own_quiz',))
        cls.org = create_organization(name='cloneorg', admins=())
        cls.q1 = create_question(title='clone q1', code='cloneq1')
        cls.q2 = create_question(title='clone q2', code='cloneq2')
        cls.quiz = create_quiz(
            code='clonesrc',
            name='Source Quiz',
            description='A description',
            time_limit=45,
            max_attempts=2,
            shuffle_questions=True,
            result_feedback='score_only',
            integrity_monitoring=False,
            is_organization_private=True,
            is_public=True,
            start_time=timezone.now(),
            end_time=timezone.now(),
            authors=(cls.cloner.profile,),
            curators=(cls.other_editor.profile,),
            testers=(),
            organizations=(cls.org,),
            questions=((cls.q1, 2.5), (cls.q2, 1.0)),
        )

    def test_clone_copies_scalar_fields(self):
        clone = self.quiz.clone(self.cloner.profile)
        self.assertEqual(clone.description, 'A description')
        self.assertEqual(clone.time_limit, 45)
        self.assertEqual(clone.max_attempts, 2)
        self.assertTrue(clone.shuffle_questions)
        self.assertEqual(clone.result_feedback, 'score_only')
        self.assertFalse(clone.integrity_monitoring)
        self.assertTrue(clone.is_organization_private)

    def test_clone_resets_public_and_times(self):
        clone = self.quiz.clone(self.cloner.profile)
        self.assertFalse(clone.is_public)
        self.assertIsNone(clone.start_time)
        self.assertIsNone(clone.end_time)

    def test_clone_name_prefixed(self):
        clone = self.quiz.clone(self.cloner.profile)
        self.assertEqual(clone.name, 'Copy of Source Quiz')

    def test_clone_copies_question_links(self):
        clone = self.quiz.clone(self.cloner.profile)
        links = list(clone.question_links.order_by('order'))
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0].points, 2.5)
        self.assertEqual(links[1].points, 1.0)
        self.assertEqual(links[0].order, 0)
        self.assertEqual(links[1].order, 1)

    def test_clone_question_links_are_shallow(self):
        clone = self.quiz.clone(self.cloner.profile)
        clone_qids = set(clone.question_links.values_list('question_id', flat=True))
        src_qids = set(self.quiz.question_links.values_list('question_id', flat=True))
        self.assertEqual(clone_qids, src_qids)

    def test_clone_author_is_cloner(self):
        clone = self.quiz.clone(self.cloner.profile)
        self.assertEqual(list(clone.authors.all()), [self.cloner.profile])

    def test_clone_copies_m2m(self):
        clone = self.quiz.clone(self.cloner.profile)
        self.assertIn(self.org, clone.organizations.all())
        self.assertIn(self.other_editor.profile, clone.curators.all())

    def test_clone_code_first_suffix(self):
        clone = self.quiz.clone(self.cloner.profile)
        self.assertEqual(clone.code, 'clonesrc2')

    def test_clone_code_skips_taken_suffixes(self):
        base = create_quiz(code='clonesrck', authors=(self.cloner.profile,))
        create_quiz(code='clonesrck2')
        create_quiz(code='clonesrck3')
        clone = base.clone(self.cloner.profile)
        self.assertEqual(clone.code, 'clonesrck4')

    def test_clone_code_exhausted_raises(self):
        base = create_quiz(code='clonesrce', authors=(self.cloner.profile,))
        for i in range(2, 10):
            create_quiz(code=f'clonesrce{i}')
        with self.assertRaises(ValueError):
            base.clone(self.cloner.profile)
