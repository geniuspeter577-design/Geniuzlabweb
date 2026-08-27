from django.db import migrations, models


class Migration(migrations.Migration):
    """Adds indexes on the three status fields the marketplace/hire flows
    filter by most (open jobs list, pending service requests, pending
    collaboration requests) — previously unindexed column scans."""

    dependencies = [
        ('konnect', '0005_servicerequest_conversation'),
    ]

    operations = [
        migrations.AlterField(
            model_name='servicerequest',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('accepted', 'Accepted'),
                    ('declined', 'Declined'),
                    ('completed', 'Completed'),
                ],
                db_index=True,
                default='pending',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='job',
            name='status',
            field=models.CharField(
                choices=[('open', 'Open'), ('closed', 'Closed')],
                db_index=True,
                default='open',
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name='collaborationrequest',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('accepted', 'Accepted'),
                    ('declined', 'Declined'),
                ],
                db_index=True,
                default='pending',
                max_length=20,
            ),
        ),
    ]
