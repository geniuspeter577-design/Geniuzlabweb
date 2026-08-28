from django.db import migrations, models


class Migration(migrations.Migration):
    """Adds an index on VTUOrder.status. Order history/admin filters by
    status routinely; previously an unindexed column scan."""

    dependencies = [
        ('vtu', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vtuorder',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('successful', 'Successful'),
                    ('failed', 'Failed'),
                    ('reversed', 'Reversed (refunded to wallet)'),
                ],
                db_index=True,
                default='pending',
                max_length=12,
            ),
        ),
    ]
