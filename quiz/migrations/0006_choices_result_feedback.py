from django.db import migrations, models


def _merge_choices_data(choices, choice_explanations):
    """Pure helper — merge parallel lists into [{text, explanation}] objects."""
    choices = list(choices or [])
    expl = list(choice_explanations or [])
    expl = expl[:len(choices)]
    expl = expl + [''] * (len(choices) - len(expl))
    return [{'text': str(c), 'explanation': str(e)} for c, e in zip(choices, expl)]


def _result_feedback_from_bools(show_correctness, show_answers):
    """Pure helper — derive the new enum value from two old booleans."""
    if not show_correctness and not show_answers:
        return 'score_only'
    if show_correctness and not show_answers:
        return 'correctness'
    return 'full'


def _do_merge_choices(apps, schema_editor):
    QuizQuestion = apps.get_model('quiz', 'QuizQuestion')
    for q in QuizQuestion.objects.all():
        q.choices = _merge_choices_data(q.choices, q.choice_explanations)
        q.save(update_fields=['choices'])


def _do_set_result_feedback(apps, schema_editor):
    Quiz = apps.get_model('quiz', 'Quiz')
    for quiz in Quiz.objects.all():
        quiz.result_feedback = _result_feedback_from_bools(
            quiz.show_correctness, quiz.show_answers)
        quiz.save(update_fields=['result_feedback'])


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0005_question_type_default_mc'),
    ]

    operations = [
        # 1. Add result_feedback (default full so all existing rows are valid)
        migrations.AddField(
            model_name='quiz',
            name='result_feedback',
            field=models.CharField(
                choices=[('score_only', 'Score only'),
                         ('correctness', 'Show correctness (no answer key)'),
                         ('full', 'Show correct answers and explanations')],
                default='full',
                max_length=11,
                verbose_name='result feedback',
                help_text=(
                    'Controls what students see on the result page after submitting.'
                ),
            ),
        ),
        # 2. Populate result_feedback from old booleans
        migrations.RunPython(_do_set_result_feedback,
                             migrations.RunPython.noop),
        # 3. Remove old boolean fields
        migrations.RemoveField(model_name='quiz', name='show_correctness'),
        migrations.RemoveField(model_name='quiz', name='show_answers'),
        # 4. Merge choices + choice_explanations into choices
        migrations.RunPython(_do_merge_choices,
                             migrations.RunPython.noop),
        # 5. Remove choice_explanations
        migrations.RemoveField(
            model_name='quizquestion', name='choice_explanations'),
    ]
