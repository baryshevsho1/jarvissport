from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .forms import RegistrationForm, LoginForm, SettingsForm
from .models import JarvisUser, Workout, Exercise, ExerciseType
import json
from collections import defaultdict


def registration_view(request):
    """
    Страница регистрации нового пользователя.
    После успешной регистрации — переходим на login.
    """
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Дополнительная логика, если нужно
            user.save()
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'fitnessapp/registration.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('main')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user:
                login(request, user)
                return redirect('main')
    else:
        form = LoginForm(request)
    
    return render(request, 'fitnessapp/login.html', {'form': form})

def logout_view(request):
    """
    Выход. После логаута – на страницу логина.
    """
    logout(request)
    return redirect('login')

@login_required
def main_view(request):
    """
    Основная страница.
    В центре — кнопка "Создать тренировку".
    Ниже — блок из 5 последних тренировок (если они есть).
    """
    # Получаем последние 5 тренировок пользователя
    workouts_qs = Workout.objects.filter(user=request.user).order_by('-id')[:5]
    
    # Превращаем QuerySet в список, чтобы к каждому элементу
    # добавить дополнительные свойства hours, mins.
    workouts = []
    for w in workouts_qs:
        hours = w.duration // 60  # целое число часов
        mins = w.duration % 60    # остаток минут
        # Можно «прикрепить» эти значения к объекту:
        w.hours = hours
        w.mins = mins
        workouts.append(w)

    return render(request, 'fitnessapp/main.html', {'workouts': workouts})

@login_required
def show_all_workouts(request):
    """
    Страница, на которой отображаются все завершённые тренировки пользователя.
    Также обрабатывает удаление тренировок при получении POST-запроса.
    При отображении длительности (duration) вычисляются часы и минуты во views.py.
    """
    if request.method == 'POST':
        # Обработка удаления тренировки
        workout_id = request.POST.get('delete_workout_id')
        if workout_id:
            workout = get_object_or_404(Workout, id=workout_id, user=request.user)
            workout.delete()
            return redirect('show_all_workouts')

    # Получаем все тренировки, сортируем по убыванию id (самые свежие сверху)
    workouts_qs = Workout.objects.filter(user=request.user).order_by('-id')

    # Создаём список, в котором каждая тренировка будет иметь дополнительные поля hours/mins
    workouts = []
    for w in workouts_qs:
        # Допустим, w.duration хранит общее количество минут
        hours = w.duration // 60
        mins = w.duration % 60
        # «Прикрепляем» их к объекту w (присваиваем атрибуты)
        w.hours = hours
        w.mins = mins
        workouts.append(w)

    return render(request, 'fitnessapp/show_all_workouts.html', {'workouts': workouts})


@login_required
def workout_view(request):
    """
    Создание/управление тренировкой.
    По завершению — сброс таймера через очистку localStorage, 
    а в Python-коде заводим новую запись Workout, 
    позволяя weight=None, если пользователь не ввёл.
    """
    if request.method == 'POST':
        duration_str = request.POST.get('duration_minutes', '0')
        # Приводим к целому количеству минут (при желании можно хранить float-значение)
        duration_val = int(float(duration_str))

        w_str = request.POST.get('current_weight', '').strip()
        if w_str == '':
            current_weight = None  # если не ввели (пусто), храним None
        else:
            try:
                current_weight = float(w_str)
            except ValueError:
                current_weight = None

        existing_count = Workout.objects.filter(user=request.user).count()
        workout_number = existing_count + 1

        new_workout = Workout.objects.create(
            user=request.user,
            date=timezone.now(),
            duration=duration_val,
            weight=current_weight,
            workout_number=workout_number
        )

        # сохраняем упражнения
        ex_count = int(request.POST.get('exercise_count', 0))
        for i in range(1, ex_count + 1):
            et_id = request.POST.get(f'exercise_type_{i}', '')
            ex_w_str = request.POST.get(f'exercise_weight_{i}', '').strip()
            if ex_w_str == '':
                ex_weight = None
            else:
                try:
                    ex_weight = float(ex_w_str)
                except ValueError:
                    ex_weight = None

            if et_id:
                et_obj = ExerciseType.objects.get(id=et_id)
            else:
                et_obj = None

            Exercise.objects.create(
                workout=new_workout,
                exercise_type=et_obj,
                exercise_number=i,
                exercise_weight=ex_weight
            )

        # После сохранения — редирект на главную или main
        return redirect('main')

    # Если GET — отображаем
    last_workout = Workout.objects.filter(user=request.user).order_by('-id').first()
    last_weight = last_workout.weight if last_workout else None

    exercise_types = ExerciseType.objects.all()
    return render(request, 'fitnessapp/workout.html', {
        'exercise_types': exercise_types,
        'last_weight': last_weight
    })


@login_required
def dashboard_view(request):
    """
    Аналитика текущего пользователя за месяц + год:
      • count_workouts (кол-во тренировок в текущем месяце),
      • avg_duration, avg_exercises, avg_weight (средние показатели),
      • monthly_stats – данные для графика (кол-во тренировок + средний вес по месяцам),
      • avg_duration_hours и avg_duration_mins – разложение средней продолжительности на ч/мин.
    """
    user = request.user
    current_month = timezone.now().month
    current_year = timezone.now().year

    # Все тренировки за текущий месяц
    monthly_workouts = Workout.objects.filter(
        user=user, date__year=current_year, date__month=current_month
    )

    count_workouts = monthly_workouts.count()
    total_duration = sum(float(w.duration) for w in monthly_workouts)  # сумма минут
    total_exercises = sum(w.exercises.count() for w in monthly_workouts)
    total_weight = sum(float(w.weight or 0) for w in monthly_workouts)

    if count_workouts > 0:
        avg_duration = total_duration / count_workouts  # в минутах
        avg_exercises = total_exercises / count_workouts
        avg_weight = total_weight / count_workouts
    else:
        avg_duration = 0
        avg_exercises = 0
        avg_weight = 0

    # Переводим среднюю продолжительность из минут в ч/мин (для отображения)
    avg_duration_hours = int(avg_duration // 60)
    avg_duration_mins = int(avg_duration % 60)

     # 2) Делаем статистику помесячно (12 месяцев), 
    #    для первого нового графика (средний вес vs кол-во тренировок).
    #    Формат: [{'month_name': 'мар 25', 'count': 5, 'avg_weight': 84.3}, ...]
    monthly_stats = []
    MONTH_NAMES = [
        'янв', 'фев', 'мар', 'апр', 'май', 'июн',
        'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'
    ]
    # Допустим, current_year = 2025 (как в примере)
    for month in range(1, 13):
        w_qs = Workout.objects.filter(user=user, date__year=current_year, date__month=month)
        cnt = w_qs.count()
        sum_w = sum(float(x.weight or 0) for x in w_qs)
        if cnt > 0:
            avg_w = sum_w / cnt
        else:
            avg_w = 0
        # Подпись месяца в виде "мар 25"
        month_label = f"{MONTH_NAMES[month-1]} {str(current_year)[-2:]}"  
        # Округлим вес
        monthly_stats.append({
            'month_label': month_label,
            'count': cnt,
            'avg_weight': float(round(avg_w, 1)),
        })

    # 3) Статистика по упражнениям по дням (второй график):
    #    Нужно получить список уникальных упражнений, и для каждого –
    #    статистику вида [{'date': '2025-03-02', 'weight': 50.0}, ...],
    #    где weight — средний вес упражнения за день (если было несколько тренировок).
    # Для примера, сделаем выборку всех упражнений текущего пользователя за все время
    # (или за год — по своему усмотрению), сгруппируем по названию и дате.

    # exercise_stats = {
    #   "PushUps": [ {"date": "2025-03-02", "weight": 20.0}, ... ],
    #   "Squats": [ {"date": "2025-03-02", "weight": 45.0}, ... ],
    #   ...
    # }

    # Предположим, ExerciseType хранит название упражнения (name),
    # а Exercise хранит link -> workout, exercise_type, exercise_weight, 
    # а workout -> date, user
    # Пользователь может иметь много тренировок, много упражнений.

    exercise_stats_dict = defaultdict(lambda: defaultdict(list))
    # структура: { "PushUps": { "2025-03-01": [20, 25], "2025-03-02": [22] }, ... }

    all_exercises_qs = Exercise.objects.filter(workout__user=user)
    for ex in all_exercises_qs:
        if ex.exercise_type:
            ex_name = ex.exercise_type.name
        else:
            ex_name = "Без названия"

        date_str = ex.workout.date.strftime("%Y-%m-%d")  # группируем по дате, строкой
        # добавляем в словарь
        ex_weight = float(ex.exercise_weight) if ex.exercise_weight else 0
        exercise_stats_dict[ex_name][date_str].append(ex_weight)

    # Теперь конвертируем в желаемый формат:
    exercise_stats = {}
    for ex_name, date_map in exercise_stats_dict.items():
        # создаём список { date, weight }
        data_list = []
        # Сортируем даты по алфавиту (чтобы график шёл по возрастанию дат)
        for d in sorted(date_map.keys()):
            values = date_map[d]
            if len(values) > 0:
                avg_day = sum(values) / len(values)
            else:
                avg_day = 0
            data_list.append({
                'date': d,       # "2025-03-02"
                'weight': float(round(avg_day, 1)),
            })
        exercise_stats[ex_name] = data_list

    # 4) Сериализуем в JSON
    import json
    monthly_stats_json = json.dumps(monthly_stats)
    exercise_stats_json = json.dumps(exercise_stats)

    context = {
        # Существующие карточки
        'count_workouts': count_workouts,
        'avg_duration': avg_duration,
        'avg_duration_hours': avg_duration_hours,
        'avg_duration_mins': avg_duration_mins,
        'avg_exercises': avg_exercises,
        'avg_weight': avg_weight,

        'current_year': current_year,

        # Новые данные для графиков
        'monthly_stats_json': monthly_stats_json,  # [{month_label, count, avg_weight}, ...]
        'exercise_stats_json': exercise_stats_json, # { "PushUps": [{date, weight}, ...], ... }
    }
    return render(request, 'fitnessapp/dashboard.html', context)


@login_required
def users_view(request):
    """
    Страница "users":
      - Список всех пользователей со статистикой:
        -- Логин, Имя, Возраст
        -- Кол-во тренировок
        -- Средний вес пользователя
      - Сортировка по возрасту, по весу, по кол-ву тренировок (через GET-параметр sort)
    """
    users = JarvisUser.objects.all()
    data = []
    for u in users:
        workouts = u.workouts.all()
        total_workouts = workouts.count()
        if total_workouts > 0:
            average_weight = sum([w.weight or 0 for w in workouts]) / total_workouts
        else:
            average_weight = 0
        data.append({
            'user': u,
            'username': u.username,
            'first_name': u.first_name,
            'age': u.age,
            'total_workouts': total_workouts,
            'average_weight': round(float(average_weight), 1),
        })

    sort_param = request.GET.get('sort', None)
    if sort_param == 'age':
        data.sort(key=lambda x: x['age'] if x['age'] else 0)
    elif sort_param == 'weight':
        data.sort(key=lambda x: x['average_weight'], reverse=True)
    elif sort_param == 'workouts':
        data.sort(key=lambda x: x['total_workouts'], reverse=True)

    return render(request, 'fitnessapp/users.html', {'data': data})


@login_required
def settings_view(request):
    """
    Страница "settings" для изменения профиля пользователя:
      - Имя, Фамилия, Отчество, пол, возраст, вес, рост, email.
    """
    if request.method == 'POST':
        form = SettingsForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('main')
    else:
        form = SettingsForm(instance=request.user)
    return render(request, 'fitnessapp/settings.html', {'form': form})


@login_required
def user_detail_view(request, username):
    # Получить того пользователя, чьи данные хотим посмотреть
    target_user = get_object_or_404(JarvisUser, username=username)

    # Все тренировки target_user
    workouts_qs = Workout.objects.filter(user=target_user).order_by('-id')
    workouts = []
    for w in workouts_qs:
        hours = w.duration // 60
        mins = w.duration % 60
        w.hours = hours
        w.mins = mins
        workouts.append(w)

    # Аналитика (аналог dashboard, но только для чтения)
    from django.utils import timezone
    import json
    from collections import defaultdict

    current_month = timezone.now().month
    current_year = timezone.now().year

    monthly_workouts = Workout.objects.filter(
        user=target_user, date__year=current_year, date__month=current_month
    )
    count_workouts = monthly_workouts.count()
    total_duration = sum(float(w.duration) for w in monthly_workouts)
    total_exercises = sum(w.exercises.count() for w in monthly_workouts)
    total_weight = sum(float(w.weight or 0) for w in monthly_workouts)

    if count_workouts > 0:
        avg_duration = total_duration / count_workouts
        avg_exercises = total_exercises / count_workouts
        avg_weight = total_weight / count_workouts
    else:
        avg_duration = 0
        avg_exercises = 0
        avg_weight = 0

    avg_duration_hours = int(avg_duration // 60)
    avg_duration_mins = int(avg_duration % 60)

    # Статистика помесячно
    MONTH_NAMES = ['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек']
    monthly_stats = []
    for month in range(1, 13):
        w_qs = Workout.objects.filter(user=target_user, date__year=current_year, date__month=month)
        cnt = w_qs.count()
        sum_w = sum(float(x.weight or 0) for x in w_qs)
        avg_w = sum_w/cnt if cnt>0 else 0
        month_label = f"{MONTH_NAMES[month-1]} {str(current_year)[-2:]}"
        monthly_stats.append({
            'month_label': month_label,
            'count': cnt,
            'avg_weight': float(round(avg_w, 1)),
        })
    # Статистика упражнений
    exercise_stats_dict = defaultdict(lambda: defaultdict(list))
    all_exercises_qs = Exercise.objects.filter(workout__user=target_user)
    for ex in all_exercises_qs:
        ex_name = ex.exercise_type.name if ex.exercise_type else "Без названия"
        date_str = ex.workout.date.strftime("%Y-%m-%d")
        ex_weight = float(ex.exercise_weight) if ex.exercise_weight else 0
        exercise_stats_dict[ex_name][date_str].append(ex_weight)

    exercise_stats = {}
    for ex_name, date_map in exercise_stats_dict.items():
        data_list = []
        for d in sorted(date_map.keys()):
            vals = date_map[d]
            avg_day = sum(vals)/len(vals) if len(vals)>0 else 0
            data_list.append({
                'date': d,
                'weight': float(round(avg_day,1)),
            })
        exercise_stats[ex_name] = data_list

    monthly_stats_json = json.dumps(monthly_stats)
    exercise_stats_json = json.dumps(exercise_stats)

    context = {
        'target_user': target_user,
        'workouts': workouts,
        # Аналитика
        'count_workouts': count_workouts,
        'avg_duration': avg_duration,
        'avg_duration_hours': avg_duration_hours,
        'avg_duration_mins': avg_duration_mins,
        'avg_exercises': avg_exercises,
        'avg_weight': avg_weight,
        'current_year': current_year,
        'monthly_stats_json': monthly_stats_json,
        'exercise_stats_json': exercise_stats_json,
    }
    return render(request, 'fitnessapp/user_detail.html', context)