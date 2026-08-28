import django.db.models.deletion
from django.db import migrations, models

import geniuzlab.validators


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='text',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='message',
            name='attachment',
            field=models.FileField(
                blank=True, null=True, upload_to='chat_attachments/%Y/%m/',
                validators=[geniuzlab.validators.validate_chat_attachment],
            ),
        ),
        migrations.AddField(
            model_name='message',
            name='reply_to',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='replies', to='chat.message',
            ),
        ),
    ]
