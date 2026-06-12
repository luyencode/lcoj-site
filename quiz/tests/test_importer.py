import io

from django.test import TestCase

from quiz.importers import xlsx_fmt
from quiz.importers.base import ParsedQuestion
from quiz.tests.util import create_question, create_user


def _make_xlsx(rows):
    """Build a minimal XLSX file with the current HEADERS and given data rows."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(list(xlsx_fmt.HEADER_LABELS))
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _row(code='mycode1', qtype='Multiple Choice', title='Q title',
         content='Q body', correct='1', points=1,
         category='', level='Easy', explanation='',
         shuffle='', ma_strategy=''):
    """Build a full XLSX row with 23 values matching HEADERS after code is added."""
    choices = ['Choice A', '', 'Choice B', '', None, '', None, '', None, '', None, '']
    return [code, qtype, title, content] + choices + [
        correct, points, category, level, explanation, shuffle, ma_strategy]


class XlsxParseCodeTest(TestCase):
    def test_parse_sets_code_from_column(self):
        buf = _make_xlsx([_row(code='pyq001')])
        questions = xlsx_fmt.parse(buf)
        self.assertEqual(len(questions), 1)
        self.assertFalse(questions[0].errors, questions[0].errors)
        self.assertEqual(questions[0].code, 'pyq001')

    def test_invalid_code_format_adds_error(self):
        buf = _make_xlsx([_row(code='has_underscore')])
        questions = xlsx_fmt.parse(buf)
        self.assertTrue(any('code' in e.lower() for e in questions[0].errors))

    def test_missing_code_adds_error(self):
        buf = _make_xlsx([_row(code='')])
        questions = xlsx_fmt.parse(buf)
        self.assertTrue(any('code' in e.lower() for e in questions[0].errors))


class XlsxImportDuplicateCodeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.editor = create_user(
            username='imp_editor', user_permissions=('edit_own_quiz',))
        cls.existing = create_question(
            title='existing', code='existing1',
            authors=(cls.editor.profile,))

    def test_duplicate_code_in_batch_blocked(self):
        from django.urls import reverse
        buf = _make_xlsx([
            _row(code='samecode', title='Q1'),
            _row(code='samecode', title='Q2'),
        ])
        self.client.force_login(self.editor)
        resp = self.client.post(reverse('quiz_import'), {'file': buf})
        self.assertEqual(resp.status_code, 200)
        # Check for duplicate error in the rendered response
        self.assertContains(resp, 'samecode')
        self.assertContains(resp, 'uplicate')

    def test_code_already_in_db_blocked(self):
        from django.urls import reverse
        buf = _make_xlsx([_row(code='existing1', title='Conflict')])
        self.client.force_login(self.editor)
        resp = self.client.post(reverse('quiz_import'), {'file': buf})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'existing1')
