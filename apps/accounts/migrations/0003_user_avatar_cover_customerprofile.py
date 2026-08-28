import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import geniuzlab.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0002_user_last_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='avatar',
            field=models.ImageField(
                blank=True, null=True, upload_to='avatars/',
                validators=[geniuzlab.validators.validate_image_upload],
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='cover_photo',
            field=models.ImageField(
                blank=True, null=True, upload_to='covers/',
                validators=[geniuzlab.validators.validate_image_upload],
            ),
        ),
        migrations.CreateModel(
            name='CustomerProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('profile_type', models.CharField(
                    choices=[('personal', 'Personal'), ('business', 'Business')],
                    default='personal', max_length=10,
                )),
                ('company_name', models.CharField(blank=True, max_length=150)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='customer_profile', to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
    ]
