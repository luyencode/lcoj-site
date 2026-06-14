from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from quiz.models import QuizAttempt
from quiz.tests.util import create_question, create_quiz, create_user


class QuizSchedulingModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.q = create_question(title='sched_mc')
        cls.student = create_user(username='sched_student')

    # ── can_start ──────────────────────────────────────────────

    def test_can_start_no_schedule(self):
        quiz = create_quiz(code='nowindow', questions=((self.q, 1.0),))
        self.assertTrue(quiz.can_start)

    def test_can_start_future_start_time(self):
        future = timezone.now() + timedelta(hours=2)
        quiz = create_quiz(code='upcoming', questions=((self.q, 1.0),),
                           start_time=future)
        self.assertFalse(quiz.can_start)

    def test_can_start_past_start_time(self):
        past = timezone.now() - timedelta(hours=1)
        quiz = create_quiz(code='alreadyopen', questions=((self.q, 1.0),),
                           start_time=past)
        self.assertTrue(quiz.can_start)

    # ── ended ──────────────────────────────────────────────────

    def test_ended_no_end_time(self):
        quiz = create_quiz(code='noend', questions=((self.q, 1.0),))
        self.assertFalse(quiz.ended)

    def test_ended_future_end_time(self):
        future = timezone.now() + timedelta(hours=1)
        quiz = create_quiz(code='notended', questions=((self.q, 1.0),),
                           end_time=future)
        self.assertFalse(quiz.ended)

    def test_ended_past_end_time(self):
        past = timezone.now() - timedelta(minutes=5)
        quiz = create_quiz(code='closed', questions=((self.q, 1.0),),
                           end_time=past)
        self.assertTrue(quiz.ended)

    # ── has_expired with end_time (no time_limit) ──────────────

    def test_has_expired_end_time_no_personal_limit(self):
        """Attempt with no time_limit expires when quiz end_time passes."""
        past_end = timezone.now() - timedelta(minutes=1)
        quiz = create_quiz(code='endedquiz', questions=((self.q, 1.0),),
                           end_time=past_end)
        attempt = QuizAttempt.start(quiz, self.student.profile)
        self.assertTrue(attempt.has_expired())

    def test_has_expired_personal_timer_wins_over_end_time(self):
        """When time_limit is set and still running, end_time passing doesn't expire attempt."""
        past_end = timezone.now() - timedelta(minutes=1)
        # time_limit=60min means personal deadline is ~60min from now — still running
        quiz = create_quiz(code='timedendedquiz', questions=((self.q, 1.0),),
                           time_limit=60, end_time=past_end)
        attempt = QuizAttempt.start(quiz, self.student.profile)
        self.assertFalse(attempt.has_expired())


class QuizSchedulingViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.q = create_question(title='view_sched_mc')
        cls.student = create_user(username='view_sched_student')

    def test_quiz_start_blocked_when_upcoming(self):
        future = timezone.now() + timedelta(hours=1)
        quiz = create_quiz(code='upcomingview', questions=((self.q, 1.0),),
                           start_time=future)
        self.client.force_login(self.student)
        response = self.client.post(f'/quizzes/{quiz.code}/start')
        self.assertRedirects(response, f'/quizzes/{quiz.code}/')

    def test_quiz_start_blocked_when_ended(self):
        past = timezone.now() - timedelta(hours=1)
        quiz = create_quiz(code='endedview', questions=((self.q, 1.0),),
                           end_time=past)
        self.client.force_login(self.student)
        response = self.client.post(f'/quizzes/{quiz.code}/start')
        self.assertRedirects(response, f'/quizzes/{quiz.code}/')
