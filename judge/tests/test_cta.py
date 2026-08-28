from django.test import TestCase, override_settings


class CtaFragmentTest(TestCase):
    def test_box_renders(self):
        from django.template.loader import render_to_string
        html = render_to_string('cta/box.html', {})
        self.assertIn('cothilaptrinh.vn/khoa-hoc', html)
        self.assertIn('zalo.me/0985188655', html)
        self.assertIn('cta-box', html)

    def test_bar_renders(self):
        from django.template.loader import render_to_string
        html = render_to_string('cta/bar.html', {})
        self.assertIn('cta-bar', html)
        self.assertIn('cothilaptrinh.vn/khoa-hoc', html)


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
