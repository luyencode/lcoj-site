from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='quizquestion',
            name='choice_explanations',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Optional explanation per choice, shown to students after submitting.',
                verbose_name='choice explanations',
            ),
        ),
    ]
