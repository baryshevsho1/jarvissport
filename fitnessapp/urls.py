from django.urls import path
from django.contrib.auth import views as auth_views
from fitnessapp.views import (
    registration_view,
    login_view,
    logout_view,
    main_view,
    workout_view,
    edit_workout_view,
    show_all_workouts,
    dashboard_view,
    users_view,
    settings_view,
    user_detail_view,
    finish_workout_view,
    plan_workout_view,
    finish_planned_view,
    calendar_full_view,
    calendar_data_view,
    workout_detail_view,
)

urlpatterns = [
    path('registration/', registration_view, name='registration'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),

    path('', main_view, name='main'),
    path('workout/', workout_view, name='workout'),
    path('plan_workout/', plan_workout_view, name='plan_workout'),
    path('edit_workout/<int:workout_id>/', edit_workout_view, name='edit_workout'),
    path('workout_detail/<int:workout_id>/', workout_detail_view, name='workout_detail'),  # <-- новая
    path('show_all_workouts/', show_all_workouts, name='show_all_workouts'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('users/', users_view, name='users'),
    path('settings/', settings_view, name='settings'),
    path('users/<str:username>/', user_detail_view, name='user_detail'),

    path('finish_workout/<int:workout_id>/<int:month_count>/', finish_workout_view, name='finish_workout'),
    path('finish_planned/<int:workout_id>/', finish_planned_view, name='finish_planned'),

    path('calendar/', calendar_full_view, name='calendar'),
    path('calendar/data/', calendar_data_view, name='calendar_data'),

    # Password reset (Django встроенные)
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='fitnessapp/password_reset.html'
         ),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='fitnessapp/password_reset_done.html'
         ),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='fitnessapp/password_reset_confirm.html'
         ),
         name='password_reset_confirm'),
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='fitnessapp/password_reset_complete.html'
         ),
         name='password_reset_complete'),
]