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
            name='Skill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=60, unique=True)),
            ],
            options={'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='CreativeProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('headline', models.CharField(blank=True, max_length=120)),
                ('category', models.CharField(choices=[('graphic_design', 'Graphic Design'), ('video_editing', 'Video Editing / Motion'), ('web_development', 'Web Development'), ('ai_productivity', 'AI & Productivity'), ('other', 'Other')], default='other', max_length=30)),
                ('bio', models.TextField(blank=True)),
                ('experience_years', models.PositiveIntegerField(default=0)),
                ('hourly_rate', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('location', models.CharField(blank=True, max_length=100)),
                ('avatar', models.ImageField(blank=True, null=True, upload_to='creative_avatars/')),
                ('is_available', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('skills', models.ManyToManyField(blank=True, related_name='creatives', to='konnect.skill')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='creative_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='PortfolioItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=120)),
                ('description', models.TextField(blank=True)),
                ('image', models.ImageField(blank=True, null=True, upload_to='portfolio/')),
                ('link', models.URLField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('creative', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='portfolio_items', to='konnect.creativeprofile')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='ServiceRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField()),
                ('budget', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('declined', 'Declined'), ('completed', 'Completed')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='service_requests_sent', to=settings.AUTH_USER_MODEL)),
                ('creative', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='service_requests', to='konnect.creativeprofile')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=150)),
                ('description', models.TextField()),
                ('category', models.CharField(choices=[('graphic_design', 'Graphic Design'), ('video_editing', 'Video Editing / Motion'), ('web_development', 'Web Development'), ('ai_productivity', 'AI & Productivity'), ('other', 'Other')], default='other', max_length=30)),
                ('budget', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('deadline', models.DateField(blank=True, null=True)),
                ('status', models.CharField(choices=[('open', 'Open'), ('closed', 'Closed')], default='open', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('poster', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='posted_jobs', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='JobApplication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cover_letter', models.TextField()),
                ('status', models.CharField(choices=[('submitted', 'Submitted'), ('shortlisted', 'Shortlisted'), ('rejected', 'Rejected'), ('hired', 'Hired')], default='submitted', max_length=20)),
                ('applied_at', models.DateTimeField(auto_now_add=True)),
                ('applicant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='job_applications', to=settings.AUTH_USER_MODEL)),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='applications', to='konnect.job')),
            ],
            options={'ordering': ['-applied_at'], 'unique_together': {('job', 'applicant')}},
        ),
        migrations.CreateModel(
            name='CollaborationRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('declined', 'Declined')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('from_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='collab_requests_sent', to=settings.AUTH_USER_MODEL)),
                ('to_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='collab_requests_received', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at'], 'unique_together': {('from_user', 'to_user')}},
        ),
    ]
