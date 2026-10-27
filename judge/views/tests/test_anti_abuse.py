from datetime import timedelta
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from judge.models import Judge, Language, Submission
from judge.models.tests.util import CommonDataMixin, create_problem, create_user


@override_settings(REGISTRATION_OPEN=True, DEFAULT_USER_LANGUAGE='PY3')
class RegistrationOAuthOnlyTestCase(TestCase):
    fixtures = ['language_all.json']

    def post_registration(self):
        return self.client.post(reverse('registration_register'), {
            'username': 'spambot',
            'email': 'spambot@example.com',
            'password1': 'Xk3!vR9#qLm2',
            'password2': 'Xk3!vR9#qLm2',
        })

    @override_settings(OAUTH_ONLY=True)
    def test_post_rejected_when_oauth_only(self):
        self.assertEqual(self.post_registration().status_code, 403)

    @override_settings(OAUTH_ONLY=True)
    def test_get_allowed_when_oauth_only(self):
        self.assertEqual(self.client.get(reverse('registration_register')).status_code, 200)

    @override_settings(OAUTH_ONLY=False)
    def test_post_not_rejected_without_oauth_only(self):
        self.assertNotEqual(self.post_registration().status_code, 403)


class Select2LoginRequiredTestCase(TestCase):
    def test_anonymous_forbidden(self):
        for name in ('profile_select2', 'problem_select2', 'contest_select2', 'organization_select2'):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name), {'term': 'a'}).status_code, 403)

    def test_authenticated_allowed(self):
        self.client.force_login(create_user(username='select2_user'))
        response = self.client.get(reverse('profile_select2'), {'term': 'select2'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('select2_user', response.content.decode())


class SitemapTestCase(TestCase):
    def test_usernames_not_listed(self):
        create_user(username='sitemap_user')
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('sitemap_user', response.content.decode())


@override_settings(VNOJ_SUBMISSION_RATE_LIMITS=[(timedelta(minutes=5), 3)])
class SubmissionRateLimitTestCase(CommonDataMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.language = Language.objects.get(key='PY3')
        cls.problem = create_problem(code='ratelimit', is_public=True, allowed_languages=('PY3',))
        judge = Judge.objects.create(name='ratelimit_judge', online=True, auth_key='key')
        judge.runtimes.add(cls.language)
        judge.problems.add(cls.problem)
        cls.user = create_user(username='ratelimit_user')
        cls.spammer = create_user(username='ratelimit_spammer', user_permissions=('spam_submission',))

    def make_submissions(self, user, count):
        for _ in range(count):
            # Status 'D' (done) so the queue limit (DMOJ_SUBMISSION_LIMIT) doesn't interfere
            Submission.objects.create(user=user.profile, problem=self.problem, language=self.language, status='D')

    def submit(self, user):
        self.client.force_login(user)
        with mock.patch.object(Submission, 'judge'):
            return self.client.post(reverse('problem_submit', args=[self.problem.code]), {
                'language': self.language.id,
                'source': 'print(1)',
            })

    def test_under_limit(self):
        self.make_submissions(self.user, 2)
        response = self.submit(self.user)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Submission.objects.filter(user=self.user.profile).count(), 3)

    def test_over_limit(self):
        self.make_submissions(self.user, 3)
        response = self.submit(self.user)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(Submission.objects.filter(user=self.user.profile).count(), 3)

    def test_old_submissions_not_counted(self):
        self.make_submissions(self.user, 3)
        Submission.objects.filter(user=self.user.profile).update(date=timezone.now() - timedelta(minutes=10))
        self.assertEqual(self.submit(self.user).status_code, 302)

    def test_spam_submission_permission_bypasses(self):
        self.make_submissions(self.spammer, 3)
        self.assertEqual(self.submit(self.spammer).status_code, 302)
