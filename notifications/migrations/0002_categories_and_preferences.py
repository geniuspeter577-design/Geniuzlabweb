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


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='category',
            field=models.CharField(blank=True, choices=CATEGORY_CHOICES, max_length=32),
        ),
        migrations.CreateModel(
            name='NotificationPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('in_app_enabled', models.BooleanField(default=True)),
                ('email_enabled', models.BooleanField(default=True)),
                ('disabled_categories', models.JSONField(blank=True, default=list)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='notification_preference', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
