from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from judge.models import ExamCategory, ExamStatement
from judge.models.tests.util import create_contest


class ExamCategoryTest(TestCase):
    def test_ordering(self):
        cat_b = ExamCategory.objects.create(name='OLP', slug='olp', order=1)
        cat_a = ExamCategory.objects.create(name='HSG', slug='hsg', order=0)
        self.assertEqual(list(ExamCategory.objects.filter(slug__in=['olp', 'hsg'])), [cat_a, cat_b])


class ExamStatementModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = ExamCategory.objects.create(name='HSG Tỉnh', slug='hsg-tinh', order=0)

    def create_exam(self, **kwargs):
        defaults = {
            'title': 'Đề thi HSG Hà Nội',
            'slug': 'de-thi-hsg-ha-noi',
            'category': self.category,
            'pdf_url': '/pdf/abc.pdf',
            'publish_on': timezone.now(),
        }
        defaults.update(kwargs)
        return ExamStatement.objects.create(**defaults)

    @override_settings(SITE_FULL_URL='http://example.com')
    def test_absolute_pdf_url(self):
        exam = self.create_exam()
        self.assertEqual(exam.absolute_pdf_url, 'http://example.com/pdf/abc.pdf')

    def test_absolute_pdf_url_none_when_blank(self):
        exam = self.create_exam(pdf_url='')
        self.assertIsNone(exam.absolute_pdf_url)

    def test_year_validator(self):
        self.create_exam(year=timezone.now().year).full_clean()

        with self.assertRaises(ValidationError):
            self.create_exam(year=1800).full_clean()

        with self.assertRaises(ValidationError):
            self.create_exam(year=timezone.now().year + 5).full_clean()

    def test_blank_province_and_year_allowed(self):
        exam = self.create_exam(province='', year=None)
        exam.full_clean()
        self.assertEqual(exam.get_province_display(), '')

    def test_contest_delete_sets_null(self):
        contest = create_contest(key='libcontest', name='Lib Contest',
                                 start_time=timezone.now() - timezone.timedelta(days=1),
                                 end_time=timezone.now() + timezone.timedelta(days=1))
        exam = self.create_exam(contest=contest)
        contest.delete()
        exam.refresh_from_db()
        self.assertIsNone(exam.contest)

    def test_category_delete_protected(self):
        cat = ExamCategory.objects.create(name='Keep', slug='keep')
        self.create_exam(category=cat)
        from django.db.models.deletion import ProtectedError
        with self.assertRaises(ProtectedError):
            cat.delete()
