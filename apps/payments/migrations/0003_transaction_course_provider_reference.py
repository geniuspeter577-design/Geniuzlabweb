from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("academy", "0010_alter_assignment_module_and_more"),
        ("payments", "0002_transaction_status_index"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="course",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="payment_transactions",
                to="academy.course",
            ),
        ),
        migrations.AddField(
            model_name="transaction",
            name="provider_reference",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name="transaction",
            name="purpose",
            field=models.CharField(
                choices=[
                    ("wallet_funding", "Wallet Funding"),
                    ("course_enrollment", "Course Enrollment"),
                    ("subscription", "Subscription"),
                    ("service", "Creative Service"),
                    ("job_deposit", "Job Deposit"),
                    ("other", "Other"),
                ],
                default="other",
                max_length=20,
            ),
        ),
    ]