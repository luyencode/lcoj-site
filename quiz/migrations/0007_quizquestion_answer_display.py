from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0006_choices_result_feedback'),
    ]

    operations = [
        migrations.AddField(
            model_name='quizquestion',
            name='answer_display',
            field=models.CharField(
                blank=True, max_length=500,
                verbose_name='answer display',
                help_text='SA only: human-readable answer shown to students on the '
                          'result page. Leave blank to show the raw patterns.',
            ),
        ),
    ]
