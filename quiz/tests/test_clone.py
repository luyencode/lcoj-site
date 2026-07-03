from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from quiz.models import Quiz
from quiz.tests.util import create_organization, create_question, create_quiz, create_user


class QuizCloneModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cloner = create_user(username='cloner', user_permissions=('edit_own_quiz',))
        cls.other_editor = create_user(username='othercloner', user_permissions=('edit_own_quiz',))
        cls.tester = create_user(username='clonetester')
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
            testers=(cls.tester.profile,),
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
        self.assertIn(self.tester.profile, clone.testers.all())

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


class QuizCloneViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = create_user(
            username='cloneviewauthor', user_permissions=('edit_own_quiz',))
        cls.stranger = create_user(
            username='clonestranger', user_permissions=('edit_own_quiz',))
        cls.q = create_question(title='view clone q', code='viewcloneq')
        cls.quiz = create_quiz(
            code='viewclonesrc',
            authors=(cls.author.profile,),
            questions=((cls.q, 1.0),),
        )

    def test_clone_post_redirects_to_edit(self):
        self.client.force_login(self.author)
        resp = self.client.post(
            reverse('quiz_clone', kwargs={'quiz': 'viewclonesrc'}))
        self.assertRedirects(
            resp, reverse('quiz_edit', kwargs={'quiz': 'viewclonesrc2'}))

    def test_clone_creates_quiz_and_links(self):
        self.client.force_login(self.author)
        self.client.post(reverse('quiz_clone', kwargs={'quiz': 'viewclonesrc'}))
        clone = Quiz.objects.get(code='viewclonesrc2')
        self.assertEqual(clone.question_links.count(), 1)

    def test_clone_non_editor_returns_404(self):
        self.client.force_login(self.stranger)
        resp = self.client.post(
            reverse('quiz_clone', kwargs={'quiz': 'viewclonesrc'}))
        self.assertEqual(resp.status_code, 404)

    def test_clone_get_returns_405(self):
        self.client.force_login(self.author)
        resp = self.client.get(
            reverse('quiz_clone', kwargs={'quiz': 'viewclonesrc'}))
        self.assertEqual(resp.status_code, 405)
