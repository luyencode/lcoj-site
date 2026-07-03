from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('judge', '0217_set_testcase_visibility_default_out_contest'),
    ]

    operations = [
        migrations.AlterField(
            model_name='problem',
            name='testcase_visibility_mode',
            field=models.CharField(
                choices=[
                    ('O', 'Visible for authors'),
                    ('C', 'Visible if user is not in a contest'),
                    ('A', 'Always visible'),
                ],
                default='A',
                max_length=1,
                verbose_name='Testcase visibility',
            ),
        ),
        migrations.RunSQL(
            sql="UPDATE judge_problem SET testcase_visibility_mode = 'A'",
            reverse_sql="UPDATE judge_problem SET testcase_visibility_mode = 'C'",
        ),
    ]
