from django.test import SimpleTestCase

from quiz import grading


class GradeSingleChoiceTestCase(SimpleTestCase):
    CHOICES = ['a', 'b', 'c', 'd']

    def grade(self, answer, correct=1, qtype=grading.MC):
        return grading.grade(qtype, self.CHOICES, correct, None, answer)

    def test_correct_choice(self):
        self.assertEqual(self.grade(1), (1.0, True))

    def test_wrong_choice(self):
        self.assertEqual(self.grade(0), (0.0, False))

    def test_empty_answer(self):
        self.assertEqual(self.grade(None), (0.0, False))

    def test_no_answer_key(self):
        self.assertEqual(self.grade(1, correct=None), (0.0, False))

    def test_true_false(self):
        self.assertEqual(self.grade(0, correct=0, qtype=grading.TF), (1.0, True))
        self.assertEqual(self.grade(1, correct=0, qtype=grading.TF), (0.0, False))

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            grading.grade('ES', [], 0, None, 0)


class GradeMultipleAnswerTestCase(SimpleTestCase):
    CHOICES = ['a', 'b', 'c', 'd', 'e']
    CORRECT = [0, 2]

    def grade(self, selected, strategy):
        return grading.grade(grading.MA, self.CHOICES, self.CORRECT, strategy, selected)

    def test_exact_match_full_credit_all_strategies(self):
        for strategy in grading.MA_STRATEGIES:
            self.assertEqual(self.grade([0, 2], strategy), (1.0, True), strategy)

    def test_empty_answer_zero_all_strategies(self):
        for strategy in grading.MA_STRATEGIES:
            for answer in (None, []):
                self.assertEqual(self.grade(answer, strategy), (0.0, False), strategy)

    def test_all_or_nothing_partial_selection(self):
        self.assertEqual(self.grade([0, 1], grading.MA_ALL_OR_NOTHING), (0.0, False))

    def test_partial_credit(self):
        ratio, ok = self.grade([0, 1], grading.MA_PARTIAL_CREDIT)
        self.assertAlmostEqual(ratio, 1 / 2 - 1 / 3)
        self.assertFalse(ok)

    def test_right_minus_wrong_floors_at_zero(self):
        self.assertEqual(self.grade([0, 1], grading.MA_RIGHT_MINUS_WRONG), (0.0, False))
        self.assertEqual(self.grade([1, 3, 4], grading.MA_RIGHT_MINUS_WRONG), (0.0, False))

    def test_correct_only_no_penalty(self):
        self.assertEqual(self.grade([0, 1], grading.MA_CORRECT_ONLY), (0.5, False))
        self.assertEqual(self.grade([0, 1, 2, 3, 4], grading.MA_CORRECT_ONLY), (1.0, True))

    def test_partial_credit_no_wrong_choices_no_penalty_term(self):
        ratio, ok = grading.grade(
            grading.MA, ['a', 'b'], [0, 1], grading.MA_PARTIAL_CREDIT, [0])
        self.assertEqual((ratio, ok), (0.5, False))

    def test_empty_answer_key_zero(self):
        self.assertEqual(
            grading.grade(grading.MA, self.CHOICES, [], grading.MA_ALL_OR_NOTHING, [0]),
            (0.0, False))

    def test_unknown_strategy_defaults_to_all_or_nothing(self):
        self.assertEqual(self.grade([0, 2], None), (1.0, True))
        self.assertEqual(self.grade([0], None), (0.0, False))


class GradeShortAnswerTestCase(SimpleTestCase):
    def grade(self, answer, accepted):
        return grading.grade(grading.SA, [], accepted, None, answer)

    @staticmethod
    def acc(text, case_sensitive=False, is_regex=False):
        return {'text': text, 'case_sensitive': case_sensitive, 'is_regex': is_regex}

    def test_case_insensitive_default(self):
        self.assertEqual(self.grade('Hanoi', [self.acc('hanoi')]), (1.0, True))

    def test_case_sensitive(self):
        accepted = [self.acc('Hanoi', case_sensitive=True)]
        self.assertEqual(self.grade('hanoi', accepted), (0.0, False))
        self.assertEqual(self.grade('Hanoi', accepted), (1.0, True))

    def test_whitespace_stripped(self):
        self.assertEqual(self.grade('  42 ', [self.acc('42')]), (1.0, True))

    def test_first_match_wins_across_multiple_accepted(self):
        accepted = [self.acc('42'), self.acc('forty two')]
        self.assertEqual(self.grade('forty TWO', accepted), (1.0, True))

    def test_regex_fullmatch(self):
        accepted = [self.acc(r'4[0-9]', is_regex=True)]
        self.assertEqual(self.grade('42', accepted), (1.0, True))
        self.assertEqual(self.grade('142', accepted), (0.0, False))

    def test_regex_case_sensitivity(self):
        self.assertEqual(self.grade('ABC', [self.acc('abc', is_regex=True)]), (1.0, True))
        self.assertEqual(
            self.grade('ABC', [self.acc('abc', case_sensitive=True, is_regex=True)]),
            (0.0, False))

    def test_invalid_stored_regex_is_no_match_not_crash(self):
        self.assertEqual(self.grade('x', [self.acc('(', is_regex=True)]), (0.0, False))

    def test_empty_answer(self):
        self.assertEqual(self.grade('', [self.acc('42')]), (0.0, False))
        self.assertEqual(self.grade(None, [self.acc('42')]), (0.0, False))

    def test_no_match_is_zero(self):
        self.assertEqual(self.grade('43', [self.acc('42')]), (0.0, False))
