from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0002_categories_and_preferences'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='category',
            field=models.CharField(
                blank=True,
                choices=[
                    ('learning_reminder', 'Daily learning reminder'), ('academy_update', 'Academy updates'),
                    ('new_course', 'New courses'), ('ai_tip', 'AI learning tips'), ('motivation', 'Motivation messages'),
                    ('job_opportunity', 'New job opportunities'), ('client_request', 'Client requests'),
                    ('portfolio_tip', 'Portfolio improvement tips'), ('ai_tool', 'AI creative tools'),
                    ('productivity', 'Daily productivity reminders'), ('hire_suggestion', 'Hire creative suggestions'),
                    ('recommended_creative', 'Recommended creatives'), ('platform_update', 'Platform updates'),
                    ('wallet_reminder', 'Wallet reminders'), ('promo', 'Promotional offers'),
                    ('message', 'Messages'), ('job', 'Jobs'), ('application', 'Applications'),
                    ('collaboration', 'Collaborations'), ('wallet', 'Wallet'), ('payment', 'Payments'),
                    ('vtu', 'VTU Orders'), ('ai_credit', 'AI Credits'), ('system', 'System Updates'),
                    ('broadcast', 'Announcements'), ('like', 'Likes on your work'),
                    ('comment', 'Comments on your work'), ('share', 'Shares of your work'),
                    ('follow', 'New followers'),
                ],
                max_length=32,
            ),
        ),
    ]
