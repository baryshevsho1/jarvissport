from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class JarvisUser(AbstractUser):
    """
    Кастомная модель пользователя.
    """
    first_name = models.CharField(max_length=150, blank=True, verbose_name='Имя')
    last_name = models.CharField(max_length=150, blank=True, verbose_name='Фамилия')
    middle_name = models.CharField(max_length=150, blank=True, verbose_name='Отчество')

    GENDER_CHOICES = (
        ('male', 'Мужской'),
        ('female', 'Женский'),
    )
    gender = models.CharField(max_length=6, choices=GENDER_CHOICES, default='male')
    age = models.PositiveIntegerField(null=True, blank=True, verbose_name='Возраст')
    weight = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True,
        verbose_name='Вес пользователя'
    )
    height = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True,
        verbose_name='Рост (см)'
    )

    registration_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.username


class ExerciseType(models.Model):
    """
    Типы упражнений (справочник).
    """
    name = models.CharField(max_length=200, unique=True, verbose_name="Название упражнения")
    # Новое поле для категории:
    category = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Категория'
    )
    # Например: Грудь, Спина, Плечи, Руки (бицепс, трицепс), Пресс, Ноги, Кардио, Комплексные упражнения

    def __str__(self):
        return self.name


class Workout(models.Model):
    user = models.ForeignKey(
        JarvisUser,
        on_delete=models.CASCADE,
        related_name='workouts',
        verbose_name='Пользователь'
    )
    date_time = models.DateTimeField(default=timezone.now, verbose_name='Дата и время завершения')
    workout_number = models.PositiveIntegerField(default=1, verbose_name='Номер тренировки')
    tracked_weight = models.DecimalField(
        max_digits=5, decimal_places=1,
        null=True, blank=True,
        verbose_name='Вес пользователя на момент тренировки'
    )

    # Добавляем поле для комментария:
    comment = models.TextField(null=True, blank=True, verbose_name='Комментарий')

# Новое поле для оценки тренировки
    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='Оценка',
        help_text='Оценка тренировки в диапазоне от 1 до 5'
    )

    def __str__(self):
        return f"Workout #{self.workout_number} ({self.user.username})"


class Exercise(models.Model):
    """
    Упражнение внутри тренировки.
    """
    workout = models.ForeignKey(
        Workout,
        on_delete=models.CASCADE,
        related_name='exercises',
        verbose_name='Тренировка'
    )
    exercise_type = models.ForeignKey(
        ExerciseType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Тип упражнения'
    )
    exercise_number = models.PositiveIntegerField(default=1, verbose_name='Порядковый номер упражнения')
    sets = models.PositiveIntegerField(default=0, verbose_name='Подходы')
    reps = models.PositiveIntegerField(default=0, verbose_name='Повторения')
    exercise_weight = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name='Вес отягощения'
    )

    # Новые поля:
    distance = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Дистанция (км)'
    )
    duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Длительность (сек)'
    )

    def __str__(self):
        return f"Exercise #{self.exercise_number} in workout #{self.workout.workout_number}"

