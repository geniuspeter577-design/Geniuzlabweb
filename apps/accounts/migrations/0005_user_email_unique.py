from django.db import migrations, models


class Migration(migrations.Migration):
    """Adds a DB-level unique constraint on User.email.

    IMPORTANT: run `python manage.py find_duplicate_emails` against your
    production database before applying this migration. If any accounts
    currently share an email address, this migration will fail (Postgres/
    MySQL) or silently produce an inconsistent index (SQLite) until those
    rows are resolved.
    """

    dependencies = [
        ('accounts', '0004_user_phone_email_visibility'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(blank=True, max_length=254, unique=True, verbose_name='email address'),
        ),
    ]
