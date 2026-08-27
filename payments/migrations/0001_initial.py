import uuid
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
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reference', models.CharField(default=uuid.uuid4, max_length=64, unique=True)),
                ('provider', models.CharField(choices=[('paystack', 'Paystack'), ('flutterwave', 'Flutterwave'), ('monnify', 'Monnify'), ('wallet', 'Wallet Balance')], default='paystack', max_length=20)),
                ('purpose', models.CharField(choices=[('wallet_funding', 'Wallet Funding'), ('subscription', 'Subscription'), ('service', 'Creative Service'), ('job_deposit', 'Job Deposit'), ('other', 'Other')], default='other', max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('currency', models.CharField(default='NGN', max_length=8)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('success', 'Successful'), ('failed', 'Failed'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('description', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
