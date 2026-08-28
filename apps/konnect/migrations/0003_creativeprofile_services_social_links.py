from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('konnect', '0002_savedcreative_review_profile_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='creativeprofile',
            name='services_offered',
            field=models.CharField(
                blank=True, max_length=255,
                help_text='e.g. Logo Design, Brand Guidelines, Social Media Kits',
            ),
        ),
        migrations.AddField(
            model_name='creativeprofile',
            name='website_url',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='creativeprofile',
            name='instagram_url',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='creativeprofile',
            name='twitter_url',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='creativeprofile',
            name='linkedin_url',
            field=models.URLField(blank=True),
        ),
    ]
