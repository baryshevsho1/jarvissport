from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import JarvisUser, Workout, Exercise, ExerciseType


@admin.register(JarvisUser)
class JarvisUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {
            'fields': (
                'first_name', 'last_name', 'middle_name', 'gender',
                'age', 'weight', 'height', 'email', 'registration_date'
            )
        }),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'gender', 'age', 'weight', 'height', 'registration_date')
    search_fields = ('username', 'first_name', 'last_name', 'email')


@admin.register(Workout)
class WorkoutAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'date_time', 'workout_number', 'tracked_weight', 'rating') 
    ordering = ('-date_time',)


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'workout', 'exercise_type', 'exercise_number',
        'sets', 'reps', 'exercise_weight', 'distance', 'duration'
    )


@admin.register(ExerciseType)
class ExerciseTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category',)