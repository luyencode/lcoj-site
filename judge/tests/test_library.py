from unittest.mock import patch

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from judge.admin.library import ExamStatementAdmin, ExamStatementAdminForm
from judge.models import ExamCategory, ExamStatement


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

    @patch('judge.admin.library.pdf_statement_uploader', return_value='/pdf/stored.pdf')
    def test_save_model_uploads_pdf(self, uploader):
        admin = ExamStatementAdmin(ExamStatement, None)
        form = self.make_form(SimpleUploadedFile('ok.pdf', b'%PDF-1.4 fake'))
        self.assertTrue(form.is_valid(), form.errors)
        obj = form.save(commit=False)
        admin.save_model(None, obj, form, change=False)
        self.assertEqual(obj.pdf_url, '/pdf/stored.pdf')
        uploader.assert_called_once()
