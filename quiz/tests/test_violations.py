import json

from django.test import TestCase
from django.urls import reverse

from quiz.models import Quiz, QuizAttempt, QuizViolation, ViolationType
from quiz.tests.util import create_question, create_quiz, create_user


class QuizViolationModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = create_user(username='vm_student')
        cls.q = create_question(title='vmq1')
        cls.quiz = create_quiz(code='vmquiz', questions=((cls.q, 1.0),))
        cls.attempt = QuizAttempt.start(cls.quiz, cls.student.profile)

    def test_integrity_monitoring_default_true(self):
        quiz = create_quiz(code='vmdefault')
        self.assertTrue(quiz.integrity_monitoring)

    def test_integrity_monitoring_can_be_disabled(self):
        quiz = create_quiz(code='vmdisabled', integrity_monitoring=False)
        self.assertFalse(quiz.integrity_monitoring)

    def test_violation_creation(self):
        from django.utils import timezone
        v = QuizViolation.objects.create(
            attempt=self.attempt,
            type=ViolationType.TAB_SWITCH,
            occurred_at=timezone.now(),
            extra_data={},
        )
        self.assertEqual(v.attempt, self.attempt)
        self.assertEqual(v.type, 'tab_switch')

    def test_violations_related_name(self):
        from django.utils import timezone
        QuizViolation.objects.create(
            attempt=self.attempt,
            type=ViolationType.DEVTOOLS,
            occurred_at=timezone.now(),
            extra_data={},
        )
        self.assertEqual(self.attempt.violations.count(), 1)

    def test_violation_ordering(self):
        from datetime import timedelta
        from django.utils import timezone
        now = timezone.now()
        QuizViolation.objects.create(
            attempt=self.attempt, type=ViolationType.TAB_SWITCH,
            occurred_at=now + timedelta(seconds=10), extra_data={})
        QuizViolation.objects.create(
            attempt=self.attempt, type=ViolationType.WINDOW_BLUR,
            occurred_at=now, extra_data={})
        types = list(self.attempt.violations.values_list('type', flat=True))
        self.assertEqual(types, ['window_blur', 'tab_switch'])


class QuizRecordViolationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = create_user(username='rv_student')
        cls.other = create_user(username='rv_other')
        cls.teacher = create_user(
            username='rv_teacher', user_permissions=('edit_own_quiz',))
        cls.q = create_question(title='rvq1')
        cls.quiz = create_quiz(code='rvquiz', questions=((cls.q, 1.0),))
        cls.quiz.authors.add(cls.teacher.profile)

    def setUp(self):
        self.attempt = QuizAttempt.start(self.quiz, self.student.profile)
        self.url = reverse('quiz_violation', kwargs={
            'quiz': 'rvquiz', 'attempt': self.attempt.id})

    def _post(self, data, user=None):
        self.client.force_login(user or self.student)
        return self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json',
        )

    def test_valid_violation_recorded(self):
        resp = self._post({'type': 'tab_switch',
                           'occurred_at': '2026-06-13T14:00:00Z'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content), {'recorded': True})
        self.assertEqual(self.attempt.violations.count(), 1)

    def test_invalid_type_returns_400(self):
        resp = self._post({'type': 'hacking',
                           'occurred_at': '2026-06-13T14:00:00Z'})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self.attempt.violations.count(), 0)

    def test_non_owner_gets_404(self):
        resp = self._post({'type': 'tab_switch',
                           'occurred_at': '2026-06-13T14:00:00Z'},
                          user=self.other)
        self.assertEqual(resp.status_code, 404)

    def test_submitted_attempt_silently_ignored(self):
        self.attempt.finalize()
        resp = self._post({'type': 'tab_switch',
                           'occurred_at': '2026-06-13T14:00:00Z'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content), {'recorded': True})
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.violations.count(), 0)

    def test_missing_body_returns_400(self):
        self.client.force_login(self.student)
        resp = self.client.post(self.url, data='not-json',
                                content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    def test_extra_data_stored(self):
        resp = self._post({'type': 'devtools',
                           'occurred_at': '2026-06-13T14:00:00Z',
                           'extra_data': {'window_delta': 200}})
        self.assertEqual(resp.status_code, 200)
        v = self.attempt.violations.first()
        self.assertEqual(v.extra_data, {'window_delta': 200})


class QuizViolationLogTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.utils import timezone
        cls.student = create_user(username='vl_student')
        cls.teacher = create_user(
            username='vl_teacher', user_permissions=('edit_own_quiz',))
        cls.other_teacher = create_user(
            username='vl_other', user_permissions=('edit_own_quiz',))
        cls.q = create_question(title='vlq1')
        cls.quiz = create_quiz(code='vlquiz', questions=((cls.q, 1.0),))
        cls.quiz.authors.add(cls.teacher.profile)
        cls.attempt = QuizAttempt.start(cls.quiz, cls.student.profile)
        cls.violation = QuizViolation.objects.create(
            attempt=cls.attempt,
            type=ViolationType.TAB_SWITCH,
            occurred_at=timezone.now(),
            extra_data={},
        )
        cls.log_url = reverse('quiz_violation_log', kwargs={
            'quiz': 'vlquiz', 'attempt': cls.attempt.id})

    def test_student_cannot_view_log(self):
        self.client.force_login(self.student)
        resp = self.client.get(self.log_url)
        self.assertEqual(resp.status_code, 404)

    def test_non_author_editor_cannot_view_log(self):
        self.client.force_login(self.other_teacher)
        resp = self.client.get(self.log_url)
        self.assertEqual(resp.status_code, 404)

    def test_author_can_view_log(self):
        self.client.force_login(self.teacher)
        resp = self.client.get(self.log_url)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data['attempt_id'], self.attempt.id)
        self.assertEqual(data['student'], 'vl_student')
        self.assertEqual(len(data['violations']), 1)
        self.assertEqual(data['violations'][0]['type'], 'tab_switch')
        self.assertEqual(data['violations'][0]['label'], 'Tab switch')
        self.assertIn('occurred_at', data['violations'][0])

    def test_empty_log_returns_empty_list(self):
        empty_attempt = QuizAttempt.start(self.quiz, self.student.profile)
        url = reverse('quiz_violation_log', kwargs={
            'quiz': 'vlquiz', 'attempt': empty_attempt.id})
        self.client.force_login(self.teacher)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data['violations'], [])
