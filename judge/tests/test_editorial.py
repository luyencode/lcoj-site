from django.test import TestCase, override_settings
from django.urls import reverse

from judge.models import Language, ProblemEditorialReveal, Submission
from judge.models.tests.util import CommonDataMixin, create_problem, create_solution


@override_settings(VNOJ_CP_EDITORIAL_REVEAL=5)
class ProblemEditorialTestCase(CommonDataMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.problem = create_problem(code='editorial', is_public=True)
        cls.solution = create_solution(
            problem=cls.problem,
            content='This is the editorial body.',
        )
        cls.url = reverse('problem_editorial', args=[cls.problem.code])

    def setUp(self):
        self.profile = self.users['normal'].profile
        self.profile.refresh_from_db()

    def test_unsolved_editorial_reveal_is_tracked_once(self):
        self.client.force_login(self.users['normal'])

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['should_gate_editorial'])
        self.assertTrue(response.context['should_track_editorial_reveal'])
        self.assertTrue(response.context['can_reveal_editorial'])
        self.assertContains(response, 'Reveal solution')

        payload = self.client.post(self.url).json()
        self.assertTrue(payload['tracked'])
        self.assertFalse(payload['already_revealed'])
        self.assertEqual(payload['penalty'], 5)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.contribution_points, -5)
        self.assertEqual(ProblemEditorialReveal.objects.filter(profile=self.profile, problem=self.problem).count(), 1)

        payload = self.client.post(self.url).json()
        self.assertTrue(payload['tracked'])
        self.assertTrue(payload['already_revealed'])

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.contribution_points, -5)
        self.assertEqual(ProblemEditorialReveal.objects.filter(profile=self.profile, problem=self.problem).count(), 1)

    def test_reveal_penalty_survives_contribution_recalculation(self):
        self.client.force_login(self.users['normal'])
        self.client.post(self.url)

        self.profile.refresh_from_db()
        self.profile.contribution_points = 999
        self.profile.save(update_fields=['contribution_points'])

        self.assertEqual(self.profile.calculate_contribution_points(), -5)

    def test_negative_contribution_score_blocks_first_reveal(self):
        self.profile.contribution_points = -1
        self.profile.save(update_fields=['contribution_points'])
        self.client.force_login(self.users['normal'])

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['should_gate_editorial'])
        self.assertFalse(response.context['can_reveal_editorial'])
        self.assertEqual(response.context['editorial_reveal_block_reason'], 'negative_contribution_points')
        self.assertContains(response, 'You cannot reveal this editorial while your contribution score is negative.')
        self.assertNotContains(response, 'Reveal solution')

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'negative_contribution_points')

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.contribution_points, -1)
        self.assertFalse(ProblemEditorialReveal.objects.filter(profile=self.profile, problem=self.problem).exists())

    def test_revealed_editorial_stays_visible_even_if_score_turns_negative(self):
        self.client.force_login(self.users['normal'])
        self.client.post(self.url)

        self.profile.refresh_from_db()
        self.profile.contribution_points = -10
        self.profile.save(update_fields=['contribution_points'])

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['has_revealed_editorial'])
        self.assertFalse(response.context['should_gate_editorial'])
        self.assertNotContains(response, 'Reveal solution')

    def test_anonymous_user_cannot_reveal_editorial(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['should_gate_editorial'])
        self.assertFalse(response.context['can_reveal_editorial'])
        self.assertEqual(response.context['editorial_reveal_block_reason'], 'login_required')
        self.assertContains(response, 'You must log in to reveal this editorial.')
        self.assertContains(response, reverse('auth_login'))
        self.assertNotContains(response, 'Reveal solution')

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'login_required')

    def test_solved_user_is_not_gated_or_penalized(self):
        Submission.objects.create(
            user=self.profile,
            problem=self.problem,
            language=Language.get_python3(),
            result='AC',
            status='D',
            case_points=1,
            case_total=1,
        )
        self.client.force_login(self.users['normal'])

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['has_solved_problem'])
        self.assertFalse(response.context['should_gate_editorial'])
        self.assertFalse(response.context['should_track_editorial_reveal'])
        self.assertNotContains(response, 'Reveal solution')

        payload = self.client.post(self.url).json()
        self.assertFalse(payload['tracked'])
        self.assertTrue(payload['already_revealed'])

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.contribution_points, 0)
        self.assertFalse(ProblemEditorialReveal.objects.filter(profile=self.profile, problem=self.problem).exists())
