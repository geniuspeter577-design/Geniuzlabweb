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
            name='VTUOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_type', models.CharField(choices=[('airtime', 'Airtime'), ('data', 'Data'), ('cable', 'Cable TV'), ('electricity', 'Electricity'), ('education', 'Education (WAEC/JAMB)')], max_length=20)),
                ('service_id', models.CharField(help_text="VTpass serviceID, e.g. 'mtn', 'mtn-data', 'dstv', 'ikeja-electric', 'waec-registration'.", max_length=50)),
                ('variation_code', models.CharField(blank=True, max_length=50)),
                ('recipient', models.CharField(help_text='Phone number, smartcard/IUC number, or meter number depending on service.', max_length=50)),
                ('recipient_name', models.CharField(blank=True, help_text='Verified customer name (cable/electricity).', max_length=150)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('request_id', models.CharField(max_length=64, unique=True)),
                ('provider_transaction_id', models.CharField(blank=True, max_length=100)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('successful', 'Successful'), ('failed', 'Failed'), ('reversed', 'Reversed (refunded to wallet)')], default='pending', max_length=12)),
                ('response_message', models.CharField(blank=True, max_length=255)),
                ('raw_response', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vtu_orders', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
