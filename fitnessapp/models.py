from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class JarvisUser(AbstractUser):
    # Поля AbstractUser уже имеют username, password, email и др.
    # Добавим нужные дополнительные поля
    first_name = models.CharField(max_length=150, blank=True, verbose_name='Имя')
    last_name = models.CharField(max_length=150, blank=True, verbose_name='Фамилия')
    middle_name = models.CharField(max_length=150, blank=True, verbose_name='Отчество')
    
    GENDER_CHOICES = (
        ('male', 'Мужской'),
        ('female', 'Женский'),
    )
    gender = models.CharField(max_length=6, choices=GENDER_CHOICES, default='male', verbose_name='Пол')
    age = models.PositiveIntegerField(null=True, blank=True, verbose_name='Возраст')
    weight = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='Вес')
    height = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='Рост')
    
    registration_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.username

class ExerciseType(models.Model):
    """
    Справочник упражнений (редактируемый в админке).
    """
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name

class Workout(models.Model):
    """
    Тренировка, связанна с пользователем, содержит дату, продолжительность, вес пользователя на момент тренировки и т.д.
    """
    user = models.ForeignKey(JarvisUser, on_delete=models.CASCADE, related_name='workouts')
    date = models.DateField(default=timezone.now)
    duration = models.PositiveIntegerField(default=0, help_text='Время в минутах')  # храним общее кол-во минут
    weight = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    
    # Поле "номер тренировки" можно хранить автоматически
    # либо вычислять динамически по количеству завершённых тренировок
    # Однако для наглядности создадим отдельное поле:
    workout_number = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"Workout #{self.workout_number} ({self.user.username})"

class Exercise(models.Model):
    """
    Упражнение внутри тренировки.
    """
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE, related_name='exercises')
    exercise_type = models.ForeignKey(ExerciseType, on_delete=models.SET_NULL, null=True, blank=True)
    exercise_number = models.PositiveIntegerField(default=1)
    # Вес (оборудования/отягощения) для конкретного упражнения
    exercise_weight = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)

    def __str__(self):
        return f"Exercise #{self.exercise_number} in workout #{self.workout.workout_number}"