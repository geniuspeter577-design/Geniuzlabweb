import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Adds QuizAnswer: the per-question choice a student picked on a
    QuizAttempt. Purely additive — no existing field, table, or data is
    touched. QuizAttempt.score_percent/passed remain the source of truth
    for grading; this just records the underlying answers behind that
    score, which previously weren't persisted anywhere."""

    dependencies = [
        ('academy', '0008_module_status_ai_generated'),
    ]

    operations = [
        migrations.CreateModel(
            name='QuizAnswer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attempt', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='answers', to='academy.quizattempt',
                )),
                ('question', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='answers', to='academy.quizquestion',
                )),
                ('choice', models.ForeignKey(
                    blank=True, null=True,
                    help_text='Null if the student submitted the quiz without answering this question.',
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+', to='academy.quizchoice',
                )),
            ],
            options={
                'unique_together': {('attempt', 'question')},
            },
        ),
    ]
