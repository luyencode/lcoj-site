from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from quiz.models import QuizAttempt
from quiz.tests.util import create_question, create_quiz, create_user


class QuizAttemptTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = create_user(username='attempt_student')
        cls.q_mc = create_question(title='mc1')
        cls.q_sa = create_question(
            title='sa1', qtype='SA', choices=[],
            correct_answers=[{'text': '42', 'case_sensitive': False,
                              'is_regex': False}])
        cls.quiz = create_quiz(
            code='attemptquiz', time_limit=10,
            questions=((cls.q_mc, 2.0), (cls.q_sa, 1.0)))

    def start(self):
        return QuizAttempt.start(self.quiz, self.student.profile)

    def test_start_freezes_question_order(self):
        attempt = self.start()
        self.assertEqual(attempt.question_order,
                         [self.q_mc.id, self.q_sa.id])
        self.assertFalse(attempt.is_submitted)

    def test_start_shuffles_when_enabled(self):
        self.quiz.shuffle_questions = True
        attempt = self.start()
        self.assertEqual(sorted(attempt.question_order),
                         sorted([self.q_mc.id, self.q_sa.id]))

    def test_choice_order_frozen_for_shuffled_questions(self):
        self.q_mc.shuffle_choices = True
        self.q_mc.save()
        attempt = self.start()
        frozen = attempt.choice_orders[str(self.q_mc.id)]
        self.assertEqual(sorted(frozen), [0, 1, 2, 3])

    def test_deadline_and_expiry(self):
        attempt = self.start()
        self.assertEqual(attempt.deadline,
                         attempt.started_at + timedelta(minutes=10))
        self.assertFalse(attempt.has_expired())
        just_past = attempt.deadline + timedelta(seconds=10)
        self.assertFalse(attempt.has_expired(now=just_past))
        self.assertTrue(attempt.has_expired(
            now=attempt.deadline + timedelta(seconds=31)))

    def test_no_time_limit_never_expires(self):
        quiz = create_quiz(code='untimed', questions=((self.q_mc, 1.0),))
        attempt = QuizAttempt.start(quiz, self.student.profile)
        self.assertIsNone(attempt.deadline)
        self.assertFalse(attempt.has_expired(
            now=timezone.now() + timedelta(days=365)))

    def test_save_answer_grades_immediately(self):
        attempt = self.start()
        answer = attempt.save_answer(self.q_mc, 0)
        self.assertEqual(answer.points, 2.0)
        self.assertTrue(answer.is_correct)
        answer = attempt.save_answer(self.q_mc, 1)
        self.assertEqual(answer.points, 0.0)
        self.assertEqual(attempt.answers.count(), 1)

    def test_finalize_scores_and_is_idempotent(self):
        attempt = self.start()
        attempt.save_answer(self.q_mc, 0)
        attempt.save_answer(self.q_sa, ' 42 ')
        attempt.finalize()
        self.assertTrue(attempt.is_submitted)
        self.assertEqual(attempt.score, 3.0)
        self.assertIsNotNone(attempt.submitted_at)
        first_submitted_at = attempt.submitted_at
        attempt.finalize()
        self.assertEqual(attempt.submitted_at, first_submitted_at)

    def test_finalize_after_expiry_clamps_submitted_at_to_deadline(self):
        attempt = self.start()
        attempt.save_answer(self.q_mc, 0)
        late = attempt.deadline + timedelta(minutes=5)
        attempt.finalize(now=late)
        self.assertEqual(attempt.submitted_at, attempt.deadline)
        self.assertEqual(attempt.duration, timedelta(minutes=10))

    def test_regrade_after_answer_key_change(self):
        attempt = self.start()
        attempt.save_answer(self.q_mc, 1)
        attempt.finalize()
        self.assertEqual(attempt.score, 0.0)
        self.q_mc.correct_answers = 1
        self.q_mc.save()
        self.quiz.regrade_attempts()
        attempt.refresh_from_db()
        self.assertEqual(attempt.score, 2.0)

    def test_ranking_best_attempt_per_user_with_duration_tiebreak(self):
        fast = create_user(username='rank_fast')
        slow = create_user(username='rank_slow')
        low = create_user(username='rank_low')
        now = timezone.now()
        for user, score, minutes in ((fast, 3.0, 3), (slow, 3.0, 7),
                                      (low, 1.0, 2)):
            attempt = QuizAttempt.start(self.quiz, user.profile)
            attempt.started_at = now
            attempt.score = score
            attempt.is_submitted = True
            attempt.submitted_at = now + timedelta(minutes=minutes)
            attempt.save()
        worse = QuizAttempt.start(self.quiz, fast.profile)
        worse.started_at = now
        worse.score = 0.5
        worse.is_submitted = True
        worse.submitted_at = now + timedelta(minutes=1)
        worse.save()
        ranking = self.quiz.get_ranking()
        self.assertEqual(
            [a.user_id for a in ranking],
            [fast.profile.id, slow.profile.id, low.profile.id])
        self.assertEqual(ranking[0].score, 3.0)


class TestQuizResultFeedbackModes(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.student = create_user(username='rfstudent')
        cls.q = create_question(
            title='rf_q', code='rfq1', qtype='MC',
            choices=[
                {'text': 'Option A', 'explanation': 'Why A'},
                {'text': 'Option B', 'explanation': ''},
                {'text': 'Option C', 'explanation': 'Why C'},
                {'text': 'Option D', 'explanation': ''},
            ],
            correct_answers=0,
            explanation='This is the question explanation.',
        )

    def _make_attempt(self, feedback):
        quiz = create_quiz(
            code='rfquiz_' + feedback,
            questions=[(self.q, 1.0)],
            result_feedback=feedback,
        )
        attempt = quiz.attempts.create(
            user=self.student.profile,
            question_order=[self.q.id],
            is_submitted=True,
            score=0.0,
        )
        attempt.answers.create(
            question=self.q, answer=1, points=0.0, is_correct=False)
        return quiz, attempt

    def test_score_only_hides_correctness_and_answers(self):
        """score_only: no per-question points, no choice list, no explanation."""
        quiz, attempt = self._make_attempt('score_only')
        self.client.force_login(self.student)
        resp = self.client.get(f'/quizzes/{quiz.code}/attempt/{attempt.id}/result')
        self.assertEqual(resp.status_code, 200)
        # Student's answer text (Option B, index 1) is shown
        self.assertContains(resp, 'Option B')
        # Per-question points breakdown should NOT appear (only in correctness/full)
        # Pattern: "/ N.N)" appears only in correctness/full h4
        self.assertNotContains(resp, '/ 1.0)')
        # Full choice list (<ul class="quiz-choices-result">) should NOT appear
        self.assertNotContains(resp, '<ul class="quiz-choices-result">')
        # Explanation should NOT appear
        self.assertNotContains(resp, 'This is the question explanation.')

    def test_correctness_shows_points_not_answers(self):
        """correctness: per-question points shown, but no choice list or explanation."""
        quiz, attempt = self._make_attempt('correctness')
        self.client.force_login(self.student)
        resp = self.client.get(f'/quizzes/{quiz.code}/attempt/{attempt.id}/result')
        self.assertEqual(resp.status_code, 200)
        # Per-question points should appear in the h4 (points are floats)
        self.assertContains(resp, '/ 1.0)')
        # Full choice list should NOT appear
        self.assertNotContains(resp, '<ul class="quiz-choices-result">')
        # Explanation should NOT appear
        self.assertNotContains(resp, 'This is the question explanation.')

    def test_full_shows_choices_and_explanation(self):
        """full: correct choices highlighted, Why? toggle, explanation shown."""
        quiz, attempt = self._make_attempt('full')
        self.client.force_login(self.student)
        resp = self.client.get(f'/quizzes/{quiz.code}/attempt/{attempt.id}/result')
        self.assertEqual(resp.status_code, 200)
        # Full choice list rendered as <ul>
        self.assertContains(resp, '<ul class="quiz-choices-result">')
        # All choices including Option A (correct) and Option B (selected)
        self.assertContains(resp, 'Option A')
        # Explanation shown
        self.assertContains(resp, 'This is the question explanation.')
        # Why? toggle for Option A's choice-level explanation
        self.assertContains(resp, 'Why A')

    def test_editor_always_gets_full(self):
        """Editor always sees full feedback even when quiz is score_only."""
        editor = create_user(username='rfeditor',
                             user_permissions=('edit_own_quiz',))
        quiz, attempt = self._make_attempt('score_only')
        quiz.authors.add(editor.profile)
        self.client.force_login(editor)
        resp = self.client.get(f'/quizzes/{quiz.code}/attempt/{attempt.id}/result')
        self.assertEqual(resp.status_code, 200)
        # Editor sees full mode: choice list and explanation present
        self.assertContains(resp, '<ul class="quiz-choices-result">')
        self.assertContains(resp, 'This is the question explanation.')
