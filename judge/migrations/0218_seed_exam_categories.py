from django.db import migrations

CATEGORIES = (
    ('HSG Tỉnh/TP', 'hsg-tinh-tp'),
    ('HSG Quốc Gia', 'hsg-quoc-gia'),
    ('Chọn đội tuyển quốc gia', 'chon-doi-tuyen-quoc-gia'),
    ('Olympic quốc tế', 'olympic-quoc-te'),
    ('Đề thi thử', 'de-thi-thu'),
    ('Đề vào 10 chuyên', 'de-vao-10-chuyen'),
    ('ICPC/OLP', 'icpc-olp'),
    ('Khác', 'khac'),
)


def seed_categories(apps, schema_editor):
    ExamCategory = apps.get_model('judge', 'ExamCategory')
    for order, (name, slug) in enumerate(CATEGORIES):
        ExamCategory.objects.get_or_create(slug=slug, defaults={'name': name, 'order': order})


def unseed_categories(apps, schema_editor):
    ExamCategory = apps.get_model('judge', 'ExamCategory')
    ExamCategory.objects.filter(slug__in=[slug for _, slug in CATEGORIES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('judge', '0217_library_models'),
    ]

    operations = [
        migrations.RunPython(seed_categories, unseed_categories),
    ]
