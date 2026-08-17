from unittest.mock import patch

from django.conf import settings
from django.contrib.admin.widgets import AdminSplitDateTime
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from judge.admin.library import ExamStatementAdmin, ExamStatementAdminForm
from judge.models import ExamCategory, ExamStatement
from judge.models.tests.util import CommonDataMixin, create_contest
from judge.widgets import AdminHeavySelect2Widget


class ExamStatementAdminFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = ExamCategory.objects.create(name='HSG', slug='hsg')

    def make_form(self, file=None):
        files = {'pdf_file': file} if file is not None else {}
        data = {'title': 'T', 'slug': 't', 'category': self.category.id}
        return ExamStatementAdminForm(data=data, files=files)

    def test_rejects_non_pdf_extension(self):
        form = self.make_form(SimpleUploadedFile('bad.exe', b'MZ'))
        self.assertFalse(form.is_valid())
        self.assertIn('pdf_file', form.errors)

    def test_rejects_oversized_file(self):
        class BigFile:
            name = 'big.pdf'
            size = settings.PDF_STATEMENT_MAX_FILE_SIZE + 1
            content_type = 'application/pdf'

        form = self.make_form(BigFile())
        self.assertFalse(form.is_valid())
        self.assertIn('pdf_file', form.errors)

    def test_empty_publish_on_cleans_to_now(self):
        form = self.make_form()
        self.assertTrue(form.is_valid(), form.errors)
        publish_on = form.cleaned_data['publish_on']
        self.assertIsNotNone(publish_on)
        self.assertLessEqual(publish_on, timezone.now())
        self.assertGreaterEqual(publish_on, timezone.now() - timezone.timedelta(seconds=5))

    def test_publish_on_uses_admin_datetime_picker(self):
        form = self.make_form()
        self.assertIsInstance(form.fields['publish_on'].widget, AdminSplitDateTime)

    def test_contest_uses_searchable_select2(self):
        form = self.make_form()
        self.assertIsInstance(form.fields['contest'].widget, AdminHeavySelect2Widget)

    @patch('judge.admin.library.pdf_statement_uploader', return_value='/pdf/stored.pdf')
    def test_save_model_uploads_pdf(self, uploader):
        admin = ExamStatementAdmin(ExamStatement, None)
        form = self.make_form(SimpleUploadedFile('ok.pdf', b'%PDF-1.4 fake'))
        self.assertTrue(form.is_valid(), form.errors)
        obj = form.save(commit=False)
        admin.save_model(None, obj, form, change=False)
        self.assertEqual(obj.pdf_url, '/pdf/stored.pdf')
        uploader.assert_called_once()


class ExamStatementModelTest(TestCase):
    def test_model_get_absolute_url(self):
        from judge.models import ExamStatement
        exam = ExamStatement.objects.create(
            title='Đề URL', slug='de-url',
            category=ExamCategory.objects.create(name='URL cat', slug='url-cat'))
        self.assertEqual(exam.get_absolute_url(),
                         reverse('library_detail', args=(exam.slug,)))


class LibraryViewTestCase(CommonDataMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.cat_hsg = ExamCategory.objects.create(name='HSG', slug='hsg', order=0)
        cls.cat_olp = ExamCategory.objects.create(name='OLP', slug='olp', order=1)
        cls.contest = create_contest(key='libcontest', name='Lib Contest',
                                     start_time=timezone.now() - timezone.timedelta(days=1),
                                     end_time=timezone.now() + timezone.timedelta(days=1))

        def exam(title, slug, **kwargs):
            defaults = {'title': title, 'slug': slug, 'category': cls.cat_hsg,
                        'publish_on': timezone.now() - timezone.timedelta(days=1)}
            defaults.update(kwargs)
            return ExamStatement.objects.create(**defaults)

        cls.exam_visible = exam('Đề HSG Hà Nội', 'hsg-hn', province='ha_noi', year=2024,
                                description='Đề marathon vòng chung kết')
        cls.exam_invisible = exam('Đề ẩn', 'hidden', is_visible=False)
        cls.exam_future = exam('Đề tương lai', 'future',
                               publish_on=timezone.now() + timezone.timedelta(days=1))
        cls.exam_olp = exam('Đề ICPC 2025', 'icpc-2025', category=cls.cat_olp,
                            province='tp_ho_chi_minh', year=2025)
        cls.exam_with_contest = exam('Đề thi có contest', 'contest-linked', contest=cls.contest,
                                     pdf_url='/pdf/contest.pdf')

    def test_list_shows_only_visible_published(self):
        response = self.client.get(reverse('library_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Đề HSG Hà Nội')
        self.assertNotContains(response, 'Đề ẩn')
        self.assertNotContains(response, 'Đề tương lai')

    def test_filter_by_category(self):
        response = self.client.get(reverse('library_list'), {'category': 'olp'})
        self.assertContains(response, 'Đề ICPC 2025')
        self.assertNotContains(response, 'Đề HSG Hà Nội')

    def test_filter_by_province(self):
        response = self.client.get(reverse('library_list'), {'province': 'tp_ho_chi_minh'})
        self.assertContains(response, 'Đề ICPC 2025')
        self.assertNotContains(response, 'Đề HSG Hà Nội')

    def test_filter_by_year(self):
        response = self.client.get(reverse('library_list'), {'year': '2024'})
        self.assertContains(response, 'Đề HSG Hà Nội')
        self.assertNotContains(response, 'Đề ICPC 2025')

    def test_invalid_year_filter_does_not_crash(self):
        response = self.client.get(reverse('library_list'), {'year': 'abc'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Đề HSG Hà Nội')
        self.assertContains(response, 'Đề ICPC 2025')

    def test_search_matches_title_and_description(self):
        response = self.client.get(reverse('library_list'), {'q': 'ICPC'})
        self.assertContains(response, 'Đề ICPC 2025')
        self.assertNotContains(response, 'Đề HSG Hà Nội')

        # A term that appears only in a description (not in any title).
        response = self.client.get(reverse('library_list'), {'q': 'marathon'})
        self.assertContains(response, 'Đề HSG Hà Nội')
        self.assertNotContains(response, 'Đề ICPC 2025')

    def test_detail_renders_flipbook_and_contest_link(self):
        exam = self.exam_with_contest
        response = self.client.get(reverse('library_detail', args=(exam.slug,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'flipbook-container')
        self.assertContains(response, 'library-flipbook-%d' % exam.id)
        self.assertContains(response, 'library-action-link')
        self.assertContains(response, 'Xem kỳ thi')

    def test_detail_hidden_is_404(self):
        exam = self.exam_invisible
        response = self.client.get(reverse('library_detail', args=(exam.slug,)))
        self.assertEqual(response.status_code, 404)

    def test_pagination_preserves_filters(self):
        for i in range(13):
            ExamStatement.objects.create(
                title='Đề phụ %d' % i, slug='phu-%d' % i, category=self.cat_hsg, year=2024,
                publish_on=timezone.now() - timezone.timedelta(days=1))
        response = self.client.get(reverse('library_list'), {'category': 'hsg'})
        self.assertContains(response, 'library/2?category=hsg')
