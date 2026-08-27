from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academy', '0003_course_price_enrollmentpayment'),
    ]

    operations = [
        migrations.AddField(
            model_name='assignmentsubmission',
            name='passed',
            field=models.BooleanField(blank=True, null=True),
        ),
    ]
