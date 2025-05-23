"""
Django settings for jarvissport project.

Generated by 'django-admin startproject' using Django 5.1.7.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""


import os
from pathlib import Path
from decouple import config

DEBUG = config('DJANGO_DEBUG', default=False, cast=bool)

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('DJANGO_SECRET_KEY')
DEBUG = True

ALLOWED_HOSTS = ["*"]

# Приложения Django
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Сторонние пакеты
    'crispy_forms',
    'crispy_bootstrap5',

    # Наше приложение
    'fitnessapp',
]

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'jarvissport.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Можно использовать папку templates в корне проекта,
        # а также шаблоны внутри каждого приложения (app_dir=True).
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'jarvissport.wsgi.application'


# База данных (пример для sqlite3, поменяйте при необходимости)
DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'jarvissport',
           'USER': 'andrey',
           'PASSWORD': 'Plumbum2089883',
           'HOST': 'localhost',
           'PORT': '5432',
       }
   }


# Используем кастомную модель пользователя
AUTH_USER_MODEL = 'fitnessapp.JarvisUser'

# Пароли (минимальный пример, дополняйте при необходимости)
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Язык и часовой пояс
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Статические файлы
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# crispy-forms: выбираем bootstrap5
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Настройки перенаправлений при входе-выходе
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'main'
LOGOUT_REDIRECT_URL = 'login'

# Уникальный идентификатор для новых моделей
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'main'
LOGOUT_REDIRECT_URL = 'login'

AUTH_USER_MODEL = 'fitnessapp.JarvisUser'

# Дополнительно,
# если у вас есть кастомный фильтр month_name в extra_tags.py:
# Обычно достаточно, что 'fitnessapp' прописано в INSTALLED_APPS,
# и в самом fitnessapp/templatetags/__init__.py есть, а в extra_tags.py — ваш фильтр.
# Django автоматически найдёт теги в папке templatetags при рендере.
#
# Если хотите, можете явно указать:
# INSTALLED_APPS += ['fitnessapp.templatetags'] <-- обычно не требуется, если файлы
# в "fitnessapp/templatetags" корректно настроены (с __init__.py).

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'mail.jarvissport.ru'  # Сервер исходящей почты
EMAIL_PORT = 587  # Порт для TLS
EMAIL_USE_TLS = True  # Используем шифрование TLS
EMAIL_HOST_USER = 'support@jarvissport.ru'  # Ваш email-адрес
EMAIL_HOST_PASSWORD = 'CK38c7Zzj8o6khQx'  # Пароль от почты
DEFAULT_FROM_EMAIL = 'JarvisSport <support@jarvissport.ru>'  # Отправитель