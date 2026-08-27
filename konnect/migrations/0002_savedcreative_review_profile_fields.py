import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('konnect', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='creativeprofile',
            name='availability_note',
            field=models.CharField(blank=True, max_length=140, help_text="e.g. 'Booking from Aug 1' or 'Open to new clients'"),
        ),
        migrations.AddField(
            model_name='creativeprofile',
            name='profile_views',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name='SavedCreative',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('creative', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_by', to='konnect.creativeprofile')),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_creatives', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at'], 'unique_together': {('customer', 'creative')}},
        ),
        migrations.CreateModel(
            name='Review',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.PositiveSmallIntegerField(default=5)),
                ('comment', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('creative', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='konnect.creativeprofile')),
                ('reviewer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews_written', to=settings.AUTH_USER_MODEL)),
                ('service_request', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='review', to='konnect.servicerequest')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
