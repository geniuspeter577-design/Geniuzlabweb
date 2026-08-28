import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('automation', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='automationsettings',
            name='bible_verse_enabled',
            field=models.BooleanField(
                default=True,
                help_text="Master switch for the daily Bible verse notification. Individual "
                "users can still opt out from their own notification preferences.",
            ),
        ),
        migrations.CreateModel(
            name='BibleVerse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reference', models.CharField(help_text="e.g. 'Philippians 4:13'", max_length=60)),
                ('text', models.TextField()),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'verbose_name': 'Bible Verse', 'ordering': ['reference']},
        ),
        migrations.CreateModel(
            name='BibleVerseLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bible_verse_logs', to=settings.AUTH_USER_MODEL)),
                ('verse', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs', to='automation.bibleverse')),
            ],
            options={'ordering': ['-sent_at'], 'unique_together': {('user', 'date')}},
        ),
    ]
