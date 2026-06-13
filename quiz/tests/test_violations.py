from django.test import TestCase

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
