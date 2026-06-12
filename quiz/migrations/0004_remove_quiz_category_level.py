from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('quiz', '0003_quizquestion_code'),
    ]

    operations = [
        migrations.RemoveField(model_name='quiz', name='category'),
        migrations.RemoveField(model_name='quiz', name='level'),
    ]
