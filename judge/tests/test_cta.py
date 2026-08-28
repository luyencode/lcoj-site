from django.test import TestCase, override_settings


class CtaFragmentTest(TestCase):
    def test_box_renders(self):
        from django.template.loader import render_to_string
        html = render_to_string('cta/box.html', {})
        self.assertIn('cothilaptrinh.vn/khoa-hoc', html)
        self.assertIn('zalo.me/0985188655', html)
        self.assertIn('cta-box', html)
        # Subtle design: no filled primary button, uses muted pill + cue link (library style)
        self.assertIn('cta-action', html)
        self.assertIn('cta-cue', html)
        self.assertNotIn('cta-primary', html)
        self.assertNotIn('button cta-primary', html)

    def test_bar_renders(self):
        from django.template.loader import render_to_string
        html = render_to_string('cta/bar.html', {})
        self.assertIn('cta-bar', html)
        self.assertIn('cothilaptrinh.vn/khoa-hoc', html)
        self.assertIn('cta-bar-btn', html)
        self.assertIn('cta-bar-cue', html)
        self.assertNotIn('cta-primary', html)


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class CtaHomeTest(TestCase):
    def test_home_contains_cta(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'cta-box')

    def test_home_cta_hidden_when_disabled(self):
        from django.core.cache import cache
        from judge.models import MiscConfig
        MiscConfig.objects.update_or_create(key='cta_enabled', defaults={'value': '0'})
        cache.delete('misc_config')
        try:
            response = self.client.get('/')
            self.assertNotContains(response, 'cta-box')
        finally:
            MiscConfig.objects.filter(key='cta_enabled').delete()
            cache.delete('misc_config')


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class CtaProblemListTest(TestCase):
    def test_problem_list_contains_cta(self):
        response = self.client.get('/problems/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'cta-box')

    def test_problem_list_cta_hidden_when_disabled(self):
        from django.core.cache import cache
        from judge.models import MiscConfig
        MiscConfig.objects.update_or_create(key='cta_enabled', defaults={'value': '0'})
        cache.delete('misc_config')
        try:
            response = self.client.get('/problems/')
            self.assertNotContains(response, 'cta-box')
        finally:
            MiscConfig.objects.filter(key='cta_enabled').delete()
            cache.delete('misc_config')


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class CtaProblemDetailTest(TestCase):
    fixtures = ['language_all.json']

    @classmethod
    def setUpTestData(cls):
        from judge.models.tests.util import create_problem
        cls.problem = create_problem('cta-prob', is_public=True, is_organization_private=False)

    def test_problem_detail_contains_bottom_bar_only(self):
        response = self.client.get(f'/problem/{self.problem.code}')
        self.assertEqual(response.status_code, 200)
        # Bottom bar at end of main area, not sidebar — sidebar is too narrow per feedback
        self.assertContains(response, 'cta-bar')
        self.assertNotContains(response, 'cta-box')

    def test_problem_detail_cta_hidden_when_disabled(self):
        from django.core.cache import cache
        from judge.models import MiscConfig
        MiscConfig.objects.update_or_create(key='cta_enabled', defaults={'value': '0'})
        cache.delete('misc_config')
        try:
            response = self.client.get(f'/problem/{self.problem.code}')
            self.assertNotContains(response, 'cta-bar')
        finally:
            MiscConfig.objects.filter(key='cta_enabled').delete()
            cache.delete('misc_config')

    def test_contest_list_does_not_show_problem_detail_bar(self):
        response = self.client.get('/contests/')
        self.assertEqual(response.status_code, 200)
        # home and problem list have cta-box, but contest should not have cta-bar from detail guard
        self.assertNotContains(response, 'cta-bar')


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class CtaSubmissionTest(TestCase):
    fixtures = ['language_all.json']

    @classmethod
    def setUpTestData(cls):
        from judge.models.tests.util import create_problem, create_user
        from judge.models import Language
        cls.user = create_user('cta_sub_user')
        cls.problem = create_problem('cta-sub-prob', is_public=True)
        cls.language = Language.get_python3()

    def _create_submission(self, result):
        from judge.models import Submission
        return Submission.objects.create(
            user=self.user.profile,
            problem=self.problem,
            language=self.language,
            result=result,
            status='D' if result != 'QU' else 'QU',
            case_points=1,
            case_total=1,
        )

    def test_non_ac_shows_cta(self):
        sub = self._create_submission('WA')
        self.client.force_login(self.user)
        response = self.client.get(f'/submission/{sub.id}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'cta-bar')

    def test_ac_does_not_show_cta(self):
        sub = self._create_submission('AC')
        self.client.force_login(self.user)
        response = self.client.get(f'/submission/{sub.id}')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'cta-bar')

    def test_cta_hidden_when_disabled(self):
        from django.core.cache import cache
        from judge.models import MiscConfig
        sub = self._create_submission('WA')
        MiscConfig.objects.update_or_create(key='cta_enabled', defaults={'value': '0'})
        cache.delete('misc_config')
        try:
            self.client.force_login(self.user)
            response = self.client.get(f'/submission/{sub.id}')
            self.assertNotContains(response, 'cta-bar')
        finally:
            MiscConfig.objects.filter(key='cta_enabled').delete()
            cache.delete('misc_config')
