# Generated by Django 5.1.7 on 2025-04-04 23:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fitnessapp', '0011_jarvisuser_user_type_workout_is_trainer_created_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='jarvisuser',
            name='user_type',
        ),
        migrations.RemoveField(
            model_name='workout',
            name='is_trainer_created',
        ),
        migrations.RemoveField(
            model_name='workout',
            name='planned_date',
        ),
        migrations.RemoveField(
            model_name='workout',
            name='status',
        ),
        migrations.AlterField(
            model_name='exercise',
            name='reps',
            field=models.PositiveIntegerField(default=0, verbose_name='Повторения'),
        ),
        migrations.AlterField(
            model_name='exercise',
            name='sets',
            field=models.PositiveIntegerField(default=0, verbose_name='Подходы'),
        ),
        migrations.DeleteModel(
            name='Approach',
        ),
    ]
