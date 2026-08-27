import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import geniuzlab.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('konnect', '0003_creativeprofile_services_social_links'),
    ]

    operations = [
        migrations.AddField(
            model_name='portfolioitem',
            name='category',
            field=models.CharField(
                choices=[
                    ('logo', 'Logo'), ('branding', 'Branding'), ('flyer', 'Flyer'),
                    ('motion_graphics', 'Motion Graphics'), ('packaging', 'Packaging'),
                    ('ui_ux', 'UI/UX'), ('video_editing', 'Video Editing'),
                    ('web_development', 'Web Development'), ('social_media', 'Social Media'),
                    ('illustration', 'Illustration'), ('photography', 'Photography'), ('other', 'Other'),
                ],
                default='other', max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='portfolioitem',
            name='views_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='portfolioitem',
            name='is_reported_hidden',
            field=models.BooleanField(
                default=False,
                help_text='Hidden from feed/discover after moderation review.',
            ),
        ),
        migrations.AddField(
            model_name='portfolioitem',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.CreateModel(
            name='ProjectMedia',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(
                    upload_to='portfolio_media/%Y/%m/',
                    validators=[geniuzlab.validators.validate_project_media],
                )),
                ('media_type', models.CharField(choices=[('image', 'Image'), ('video', 'Video')], default='image', max_length=10)),
                ('order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='media', to='konnect.portfolioitem')),
            ],
            options={'ordering': ['order', 'created_at']},
        ),
        migrations.CreateModel(
            name='ProjectLike',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='likes', to='konnect.portfolioitem')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='project_likes', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at'], 'unique_together': {('project', 'user')}},
        ),
        migrations.CreateModel(
            name='ProjectComment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='konnect.portfolioitem')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='project_comments', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['created_at']},
        ),
        migrations.CreateModel(
            name='ProjectShare',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shares', to='konnect.portfolioitem')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='project_shares', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='SavedProject',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saves', to='konnect.portfolioitem')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_projects', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at'], 'unique_together': {('user', 'project')}},
        ),
        migrations.CreateModel(
            name='ProjectReport',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.CharField(choices=[
                    ('spam', 'Spam or misleading'), ('copyright', 'Copyright / stolen work'),
                    ('inappropriate', 'Inappropriate content'), ('other', 'Other'),
                ], default='other', max_length=20)),
                ('details', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='konnect.portfolioitem')),
                ('reporter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='project_reports', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='Follow',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('follower', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='following', to=settings.AUTH_USER_MODEL)),
                ('following', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='followers', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at'], 'unique_together': {('follower', 'following')}},
        ),
    ]
