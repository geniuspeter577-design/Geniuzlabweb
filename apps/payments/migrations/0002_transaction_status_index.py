from django.db import migrations, models


class Migration(migrations.Migration):
    """Adds an index on Transaction.status. Views/admin filter and count
    transactions by status regularly (pending/success/failed); this was
    previously an unindexed column scan."""

    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='status',
            field=models.CharField(
                choices=[('pending', 'Pending'), ('success', 'Successful'), ('failed', 'Failed'), ('cancelled', 'Cancelled')],
                db_index=True,
                default='pending',
                max_length=20,
            ),
        ),
    ]
