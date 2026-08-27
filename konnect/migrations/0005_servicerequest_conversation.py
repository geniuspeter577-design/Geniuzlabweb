import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0002_message_attachment_reply'),
        ('konnect', '0004_social_layer'),
    ]

    operations = [
        migrations.AddField(
            model_name='servicerequest',
            name='conversation',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='service_requests', to='chat.conversation',
            ),
        ),
    ]
