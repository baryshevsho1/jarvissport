from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import JarvisUser, Workout, Exercise, ExerciseType, ExerciseApproach

@admin.register(JarvisUser)
class JarvisUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {
            'fields': (
                'first_name', 'last_name', 'middle_name', 'gender',
                'birth_date', 'weight', 'height', 'email', 'registration_date'
            )
        }),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'gender', 'birth_date', 'weight', 'height', 'registration_date'
    )
    search_fields = ('username', 'first_name', 'last_name', 'email')

@admin.register(Workout)
class WorkoutAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'date_time', 'workout_number',
        'tracked_weight', 'rating', 'status', 'planned_for'
    )
    ordering = ('-date_time',)

@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    """
    Убираем sets, reps, exercise_weight (которые 
    теперь хранятся в ExerciseApproach). Вместо них 
    можно добавить метод для подсчёта подходов.
    """
    list_display = (
        'id',
        'workout',
        'exercise_type',
        'exercise_number',
        'approaches_count',   # наш новый метод
        'distance',
        'duration'
    )

    def approaches_count(self, obj):
        return obj.approaches.count()
    approaches_count.short_description = 'Подходов'

@admin.register(ExerciseApproach)
class ExerciseApproachAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'exercise', 'order', 'reps', 'weight'
    )

@admin.register(ExerciseType)
class ExerciseTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category',)