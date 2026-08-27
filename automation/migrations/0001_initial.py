import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

CATEGORY_CHOICES = [
    ("learning_reminder", "Daily learning reminder"),
    ("academy_update", "Academy updates"),
    ("new_course", "New courses"),
    ("ai_tip", "AI learning tips"),
    ("motivation", "Motivation messages"),
    ("job_opportunity", "New job opportunities"),
    ("client_request", "Client requests"),
    ("portfolio_tip", "Portfolio improvement tips"),
    ("ai_tool", "AI creative tools"),
    ("productivity", "Daily productivity reminders"),
    ("hire_suggestion", "Hire creative suggestions"),
    ("recommended_creative", "Recommended creatives"),
    ("platform_update", "Platform updates"),
    ("wallet_reminder", "Wallet reminders"),
    ("promo", "Promotional offers"),
    ("message", "Messages"),
    ("job", "Jobs"),
    ("application", "Applications"),
    ("collaboration", "Collaborations"),
    ("wallet", "Wallet"),
    ("payment", "Payments"),
    ("vtu", "VTU Orders"),
    ("ai_credit", "AI Credits"),
    ("system", "System Updates"),
    ("broadcast", "Announcements"),
]

TARGET_CHOICES = [
    ("all", "All Users"),
    ("customer", "Customer"),
    ("creative", "Creative"),
    ("student", "Student"),
    ("instructor", "Instructor"),
    ("admin", "Admin"),
]


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AutomationSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enabled', models.BooleanField(default=True, help_text='Master switch for the daily notification engine.')),
                ('send_hour', models.PositiveSmallIntegerField(default=7, help_text='0-23, server local time.')),
                ('send_minute', models.PositiveSmallIntegerField(default=0, help_text='0-59.')),
                ('assistant_enabled', models.BooleanField(default=True, help_text='Show the floating AI chat assistant site-wide.')),
                ('last_run_date', models.DateField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Automation Settings',
                'verbose_name_plural': 'Automation Settings',
            },
        ),
        migrations.CreateModel(
            name='DailyMessageTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('student', 'Student'), ('instructor', 'Instructor'), ('creative', 'Creative'), ('customer', 'Customer')], max_length=20)),
                ('category', models.CharField(choices=CATEGORY_CHOICES, max_length=32)),
                ('message', models.CharField(help_text='You can use {first_name} as a placeholder for personalization.', max_length=255)),
                ('link', models.CharField(blank=True, help_text='Optional relative URL, e.g. /academy/', max_length=255)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['role', 'category']},
        ),
        migrations.CreateModel(
            name='Broadcast',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField()),
                ('link', models.CharField(blank=True, max_length=255)),
                ('target_role', models.CharField(choices=TARGET_CHOICES, default='all', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('recipient_count', models.PositiveIntegerField(default=0)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='broadcasts', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='NotificationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('channel', models.CharField(choices=[('in_app', 'In-app'), ('email', 'Email'), ('both', 'In-app + Email'), ('none', 'Skipped')], default='in_app', max_length=10)),
                ('status', models.CharField(choices=[('sent', 'Sent'), ('failed', 'Failed')], default='sent', max_length=10)),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs', to='automation.dailymessagetemplate')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='automation_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-sent_at']},
        ),
        migrations.AlterUniqueTogether(
            name='notificationlog',
            unique_together={('template', 'user', 'date')},
        ),
    ]
