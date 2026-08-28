import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='GeneratedImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('prompt', models.CharField(max_length=1000)),
                ('provider', models.CharField(help_text="Which provider handled this request, e.g. 'openai'.", max_length=40)),
                ('model_name', models.CharField(blank=True, max_length=80)),
                ('image', models.ImageField(blank=True, null=True, upload_to='ai_hub/images/%Y/%m/')),
                ('image_url', models.URLField(blank=True, help_text='Used when the provider returns a hosted URL instead of raw image bytes.', max_length=1000)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('done', 'Done'), ('failed', 'Failed')], default='pending', max_length=10)),
                ('error_message', models.CharField(blank=True, max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ai_images', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='GeneratedVideo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('prompt', models.CharField(max_length=1000)),
                ('provider', models.CharField(help_text="Which provider handled this request, e.g. 'runway', 'luma'.", max_length=40)),
                ('external_job_id', models.CharField(blank=True, max_length=200)),
                ('video_url', models.URLField(blank=True, max_length=1000)),
                ('status', models.CharField(choices=[('not_configured', 'Provider not configured'), ('queued', 'Queued'), ('processing', 'Processing'), ('done', 'Done'), ('failed', 'Failed')], default='queued', max_length=20)),
                ('error_message', models.CharField(blank=True, max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ai_videos', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
