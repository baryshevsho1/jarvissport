from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import date

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
    birth_date = models.DateField(null=True, blank=True, verbose_name='Дата рождения')

    weight = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name='Вес пользователя'
    )
    height = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name='Рост (см)'
    )

    registration_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.username

    def get_age(self):
        """
        Вычисляет возраст на основе birth_date.
        """
        if self.birth_date:
            today = date.today()
            years = today.year - self.birth_date.year
            if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
                years -= 1
            return years
        return None


class ExerciseType(models.Model):
    """
    Типы упражнений (справочник).
    """
    name = models.CharField(max_length=200, unique=True, verbose_name="Название упражнения")
    category = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Категория'
    )

    def __str__(self):
        return self.name


class Workout(models.Model):
    """
    Модель одной тренировки и её основные поля.
    Теперь добавлены поля status и planned_for, чтобы различать
    завершённые тренировки и запланированные.
    """
    STATUS_CHOICES = (
        ('done', 'Завершена'),
        ('planned', 'Запланирована'),
    )

    user = models.ForeignKey(
        JarvisUser,
        on_delete=models.CASCADE,
        related_name='workouts',
        verbose_name='Пользователь'
    )

    # Для завершённой тренировки
    date_time = models.DateTimeField(
        default=timezone.now,
        verbose_name='Дата и время завершения'
    )

    # Номер тренировки (упрощённо)
    workout_number = models.PositiveIntegerField(
        default=1,
        verbose_name='Номер тренировки'
    )
    tracked_weight = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name='Вес пользователя на момент тренировки'
    )
    comment = models.TextField(
        null=True,
        blank=True,
        verbose_name='Комментарий'
    )
    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='Оценка',
        help_text='Оценка тренировки в диапазоне от 1 до 5'
    )

    # Новые поля (планирование)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='done',
        verbose_name='Статус тренировки'
    )
    planned_for = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата/время запланированной тренировки'
    )

    def __str__(self):
        return f"Workout #{self.workout_number} ({self.user.username}) [{self.status}]"


class Exercise(models.Model):
    """
    Упражнение внутри тренировки.
    Убрали поля sets/reps/exercise_weight — теперь они
    будут храниться в новой модели ExerciseApproach (дропсеты).
    У кардио сохраняются distance и duration.
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
    exercise_number = models.PositiveIntegerField(
        default=1,
        verbose_name='Порядковый номер упражнения'
    )

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


class ExerciseApproach(models.Model):
    """
    Дополнительная модель для хранения подходов (dropset) в одном Exercise.
    Хранит номер подхода, количество повторений и вес.
    """
    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        related_name='approaches',
        verbose_name='Упражнение'
    )
    order = models.PositiveIntegerField(
        default=1,
        verbose_name='Порядок подхода'
    )
    reps = models.PositiveIntegerField(
        default=0,
        verbose_name='Повторения'
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name='Вес (кг)'
    )

    def __str__(self):
        return f"Approach #{self.order} for exercise_id={self.exercise_id}"