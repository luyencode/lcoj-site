from django.core.validators import RegexValidator
from django.db import migrations, models


def set_question_codes(apps, schema_editor):
    QuizQuestion = apps.get_model('quiz', 'QuizQuestion')
    for q in QuizQuestion.objects.order_by('id'):
        q.code = f'q{q.id}'
        q.save(update_fields=['code'])


class Migration(migrations.Migration):
    dependencies = [
        ('quiz', '0002_quizquestion_choice_explanations'),
    ]

    operations = [
        # Step A: add column with a temporary default so existing rows aren't NULL
        migrations.AddField(
            model_name='quizquestion',
            name='code',
            field=models.CharField(
                default='',
                max_length=32,
                validators=[RegexValidator(
                    '^[a-z0-9]+$', 'Question code must be ^[a-z0-9]+$')],
                verbose_name='question code',
            ),
            preserve_default=False,
        ),
        # Step B: populate deterministic codes for all existing rows
        migrations.RunPython(set_question_codes, migrations.RunPython.noop),
        # Step C: add unique constraint and drop default
        migrations.AlterField(
            model_name='quizquestion',
            name='code',
            field=models.CharField(
                max_length=32,
                unique=True,
                validators=[RegexValidator(
                    '^[a-z0-9]+$', 'Question code must be ^[a-z0-9]+$')],
                verbose_name='question code',
            ),
        ),
        # Update Quiz.code validator (DB-level no-op; updates migration state)
        migrations.AlterField(
            model_name='quiz',
            name='code',
            field=models.CharField(
                max_length=32,
                unique=True,
                validators=[RegexValidator(
                    '^[a-z0-9]+$', 'Quiz code must be ^[a-z0-9]+$')],
                verbose_name='quiz code',
            ),
        ),
    ]
