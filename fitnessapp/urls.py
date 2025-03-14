from django.urls import path
from .views import (
    registration_view, login_view, main_view, workout_view, dashboard_view, 
    users_view, settings_view, logout_view, show_all_workouts, user_detail_view 
)

urlpatterns = [
    # 1) registration
    path('registration/', registration_view, name='registration'),

    # 2) login
    path('login/', login_view, name='login'),
    # logout
    path('logout/', logout_view, name='logout'),

    # 3) main
    path('', main_view, name='main'),
    path('show_all_workouts/', show_all_workouts, name='show_all_workouts'),

    # 4) workout
    path('workout/', workout_view, name='workout'),

    # 5) dashboard
    path('dashboard/', dashboard_view, name='dashboard'),

    # 6) users
    path('users/', users_view, name='users'),

    # 7) settings
    path('settings/', settings_view, name='settings'),

    # Новый маршрут, принимающий username:
    path('users/<str:username>/', user_detail_view, name='user_detail'),
]