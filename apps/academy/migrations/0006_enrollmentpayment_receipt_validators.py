from django.db import migrations, models

import geniuzlab.validators


class Migration(migrations.Migration):

    dependencies = [
        ('academy', '0005_module_lesson_quiz_lms'),
    ]

    operations = [
        migrations.AlterField(
            model_name='enrollmentpayment',
            name='receipt',
            field=models.FileField(
                blank=True, null=True, upload_to='payment_receipts/%Y/%m/',
                validators=[geniuzlab.validators.validate_receipt_upload],
            ),
        ),
    ]
