from django.db import migrations, models


class Migration(migrations.Migration):
    """Adds an index on Notification.is_read. The notification bell/list
    filters unread notifications per-user on every authenticated page
    load; previously an unindexed column scan."""

    dependencies = [
        ('notifications', '0004_bible_verse_category'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='is_read',
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
