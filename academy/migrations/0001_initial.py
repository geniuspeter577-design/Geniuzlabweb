from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=120)),
                ('slug', models.SlugField(unique=True)),
                ('icon', models.CharField(default='🎓', max_length=10)),
                ('summary', models.CharField(max_length=255)),
                ('url_name', models.CharField(help_text='Django url name for the detail page', max_length=60)),
            ],
            options={'ordering': ['title']},
        ),
    ]
