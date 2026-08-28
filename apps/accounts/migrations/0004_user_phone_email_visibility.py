from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_user_avatar_cover_customerprofile'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='phone_is_public',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='user',
            name='email_is_public',
            field=models.BooleanField(default=False),
        ),
    ]
