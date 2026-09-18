import importlib

from django.test import SimpleTestCase

_mig = importlib.import_module(
    'quiz.migrations.0006_choices_result_feedback')


class TestMergeChoicesData(SimpleTestCase):

    def test_equal_length(self):
        result = _mig._merge_choices_data(['A', 'B'], ['Correct', 'Wrong'])
        self.assertEqual(result, [
            {'text': 'A', 'explanation': 'Correct'},
            {'text': 'B', 'explanation': 'Wrong'},
        ])

    def test_short_explanations_padded(self):
        result = _mig._merge_choices_data(['A', 'B', 'C'], ['x'])
        self.assertEqual(result, [
            {'text': 'A', 'explanation': 'x'},
            {'text': 'B', 'explanation': ''},
            {'text': 'C', 'explanation': ''},
        ])

    def test_long_explanations_truncated(self):
        result = _mig._merge_choices_data(['A'], ['x', 'y', 'z'])
        self.assertEqual(result, [{'text': 'A', 'explanation': 'x'}])

    def test_empty(self):
        self.assertEqual(_mig._merge_choices_data([], []), [])

    def test_none_inputs(self):
        self.assertEqual(_mig._merge_choices_data(None, None), [])


class TestResultFeedbackFromBools(SimpleTestCase):

    def test_both_true_gives_full(self):
        self.assertEqual(
            _mig._result_feedback_from_bools(True, True), 'full')

    def test_correctness_only(self):
        self.assertEqual(
            _mig._result_feedback_from_bools(True, False), 'correctness')

    def test_both_false_gives_score_only(self):
        self.assertEqual(
            _mig._result_feedback_from_bools(False, False), 'score_only')

    def test_answers_only_maps_to_full(self):
        self.assertEqual(
            _mig._result_feedback_from_bools(False, True), 'full')
