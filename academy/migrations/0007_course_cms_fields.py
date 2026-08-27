from django.db import migrations, models

import geniuzlab.validators


class Migration(migrations.Migration):

    dependencies = [
        ('academy', '0006_enrollmentpayment_receipt_validators'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='summary',
            field=models.CharField(
                max_length=255, help_text='Short description shown on the course card.',
            ),
        ),
        migrations.AlterField(
            model_name='course',
            name='url_name',
            field=models.CharField(
                blank=True, max_length=60,
                help_text='Legacy field from the old hardcoded course pages. No longer used '
                           'for routing — every course now renders through the single dynamic '
                           'course detail page (by slug). Safe to leave blank on new courses.',
            ),
        ),
        migrations.AddField(
            model_name='course',
            name='image',
            field=models.ImageField(
                blank=True, null=True, upload_to='course_images/%Y/%m/',
                validators=[geniuzlab.validators.validate_image_upload],
                help_text='Used as both the homepage thumbnail and the course detail cover image.',
            ),
        ),
        migrations.AddField(
            model_name='course',
            name='description',
            field=models.TextField(
                blank=True, help_text='Full description shown on the course detail page.',
            ),
        ),
        migrations.AddField(
            model_name='course',
            name='duration',
            field=models.CharField(blank=True, max_length=60, help_text="e.g. '6 weeks', '3 months'."),
        ),
        migrations.AddField(
            model_name='course',
            name='level',
            field=models.CharField(
                choices=[
                    ('beginner', 'Beginner'),
                    ('intermediate', 'Intermediate'),
                    ('advanced', 'Advanced'),
                ],
                default='beginner', max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='course',
            name='requirements',
            field=models.TextField(
                blank=True, help_text="One requirement per line, e.g. 'A laptop'.",
            ),
        ),
        migrations.AddField(
            model_name='course',
            name='outcomes',
            field=models.TextField(
                blank=True,
                help_text="One learning outcome per line, e.g. 'Build a portfolio website'.",
            ),
        ),
        migrations.AddField(
            model_name='course',
            name='instructor_name',
            field=models.CharField(blank=True, default='GeniuzLab Instructor Team', max_length=120),
        ),
        migrations.AddField(
            model_name='course',
            name='instructor_bio',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='course',
            name='meta_description',
            field=models.CharField(
                blank=True, max_length=255,
                help_text='SEO meta description. Falls back to the short description if left blank.',
            ),
        ),
        migrations.AddField(
            model_name='course',
            name='is_published',
            field=models.BooleanField(
                default=True,
                help_text='Unpublished courses are hidden from the academy homepage and detail pages.',
            ),
        ),
    ]
