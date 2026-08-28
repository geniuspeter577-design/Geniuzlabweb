from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academy', '0007_course_cms_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='module',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft — hidden from students, admin review needed'),
                    ('published', 'Published — visible to enrolled students'),
                ],
                default='published',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='module',
            name='is_ai_generated',
            field=models.BooleanField(
                default=False,
                help_text='Set automatically by the AI course generator. Review the content, '
                          'edit anything that needs it, then set Status to Published.',
            ),
        ),
    ]
