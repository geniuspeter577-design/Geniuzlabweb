import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('academy', '0002_enrollment_assignment_certificate_community'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.CreateModel(
            name='EnrollmentPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=150)),
                ('email', models.EmailField(max_length=254)),
                ('phone', models.CharField(max_length=30)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('reference', models.CharField(blank=True, max_length=100)),
                ('receipt', models.FileField(blank=True, null=True, upload_to='payment_receipts/%Y/%m/')),
                ('status', models.CharField(choices=[('pending', 'Pending review'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=10)),
                ('admin_note', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='enrollment_payments', to='academy.course')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_enrollment_payments', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='enrollment_payments', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
