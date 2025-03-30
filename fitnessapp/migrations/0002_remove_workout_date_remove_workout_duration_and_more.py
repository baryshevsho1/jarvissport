# Generated by Django 5.1.7 on 2025-03-15 10:07

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fitnessapp', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='workout',
            name='date',
        ),
        migrations.RemoveField(
            model_name='workout',
            name='duration',
        ),
        migrations.RemoveField(
            model_name='workout',
            name='weight',
        ),
        migrations.AddField(
            model_name='exercise',
            name='reps',
            field=models.PositiveIntegerField(default=0, verbose_name='Повторения'),
        ),
        migrations.AddField(
            model_name='exercise',
            name='sets',
            field=models.PositiveIntegerField(default=0, verbose_name='Подходы'),
        ),
        migrations.AddField(
            model_name='workout',
            name='date_time',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Дата и время завершения'),
        ),
        migrations.AlterField(
            model_name='exercise',
            name='exercise_number',
            field=models.PositiveIntegerField(default=1, verbose_name='Порядковый номер упражнения'),
        ),
        migrations.AlterField(
            model_name='exercise',
            name='exercise_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='fitnessapp.exercisetype', verbose_name='Тип упражнения'),
        ),
        migrations.AlterField(
            model_name='exercise',
            name='exercise_weight',
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=5, null=True, verbose_name='Вес отягощения'),
        ),
        migrations.AlterField(
            model_name='exercise',
            name='workout',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exercises', to='fitnessapp.workout', verbose_name='Тренировка'),
        ),
        migrations.AlterField(
            model_name='exercisetype',
            name='name',
            field=models.CharField(max_length=200, unique=True, verbose_name='Название упражнения'),
        ),
        migrations.AlterField(
            model_name='jarvisuser',
            name='age',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Возраст'),
        ),
        migrations.AlterField(
            model_name='jarvisuser',
            name='height',
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=5, null=True, verbose_name='Рост (см)'),
        ),
        migrations.AlterField(
            model_name='jarvisuser',
            name='weight',
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=5, null=True, verbose_name='Вес пользователя'),
        ),
        migrations.AlterField(
            model_name='workout',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workouts', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь'),
        ),
        migrations.AlterField(
            model_name='workout',
            name='workout_number',
            field=models.PositiveIntegerField(default=1, verbose_name='Номер тренировки'),
        ),
    ]
