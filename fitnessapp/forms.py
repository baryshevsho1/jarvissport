from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from .models import JarvisUser
from .models import Workout

class RegistrationForm(UserCreationForm):
    """
    Форма регистрации нового пользователя.
    Добавлены поля отчества, пола, даты рождения, веса и роста. 
    В clean_* методах проверяем уникальность логина и email.
    """
    middle_name = forms.CharField(
        required=False,
        label="Отчество"
    )

    GENDER_CHOICES = [
        ('male', 'Мужской'),
        ('female', 'Женский'),
    ]
    gender = forms.ChoiceField(
        choices=GENDER_CHOICES,
        label="Пол"
    )

    birth_date = forms.DateField(
        required=False,
        label="Дата рождения",
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    weight = forms.DecimalField(
        required=False,
        label="Вес (кг)",
        min_value=0,
        decimal_places=1
    )
    height = forms.DecimalField(
        required=False,
        label="Рост (см)",
        min_value=0,
        decimal_places=1
    )

    class Meta:
        model = JarvisUser
        fields = [
            'username',      # логин
            'password1',
            'password2',
            'first_name',
            'last_name',
            'middle_name',
            'gender',
            'birth_date',
            'weight',
            'height',
            'email'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        # Можно добавить кнопку, если её не реализовать в шаблоне:
        # self.helper.add_input(Submit('submit', 'Зарегистрироваться'))

    def clean_username(self):
        username = self.cleaned_data['username']
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError("Логин должен содержать только латинские буквы, цифры и подчёркивания!")
        if JarvisUser.objects.filter(username=username).exists():
            raise ValidationError("Пользователь с таким логином уже существует!")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if email and JarvisUser.objects.filter(email=email).exists():
            raise ValidationError("Пользователь с таким email уже зарегистрирован!")
        return email


class LoginForm(AuthenticationForm):
    """
    Форма аутентификации (логин).
    По умолчанию наследуемся от AuthenticationForm, настройка через crispy_forms.
    """
    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        # Опционально в шаблоне добавим кнопку:
        # self.helper.add_input(Submit('submit', 'Войти'))


class SettingsForm(forms.ModelForm):
    """
    Форма для редактирования данных профиля (Имя, Фамилия, Отчество, пол, дата рождения, вес, рост, email).
    """
    class Meta:
        model = JarvisUser
        fields = [
            'first_name', 'last_name', 'middle_name',
            'gender', 'birth_date', 'weight', 'height', 'email'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Сохранить'))
        

class WorkoutForm(forms.ModelForm):
    class Meta:
        model = Workout
        fields = ['date_time', 'workout_number', 'tracked_weight', 'comment', 'rating']  # Добавлено поле rating