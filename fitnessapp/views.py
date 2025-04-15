from collections import defaultdict as ddict
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.urls import reverse
from django.http import HttpResponseBadRequest
from django.core.paginator import Paginator
from django.db.models import Min, Max, Avg, Count
from django.db.models.functions import ExtractWeek, ExtractYear, ExtractMonth
from django.db import models 
from .utils import calculate_category_percent
from .forms import RegistrationForm, LoginForm, SettingsForm, WorkoutForm
from .models import (
    JarvisUser,
    Workout,
    Exercise,
    ExerciseType,
    ExerciseApproach
)
from .utils import calculate_category_percent

#--------------------------------------------------------------------------
# РЕГИСТРАЦИЯ, ВХОД, ВЫХОД
#--------------------------------------------------------------------------
def registration_view(request):
    """
    Обрабатывает регистрацию нового пользователя.
    """
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'fitnessapp/registration.html', {'form': form})

def login_view(request):
    """
    Обрабатывает вход пользователя в систему.
    """
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
    Обрабатывает выход пользователя из системы.
    """
    logout(request)
    return redirect('login')

#--------------------------------------------------------------------------
# ГЛАВНАЯ (MAIN)
#--------------------------------------------------------------------------
@login_required
def main_view(request):
    """
    Главная страница: показывает список тренировок текущего пользователя.
    Сначала выводим «будущие плановые» (planned_for > текущее время), 
    затем все остальные (завершённые и плановые с прошедшей датой).
    Результат пагинируем по 10 записей на страницу.
    """

    now = timezone.now()

    # Шаг 1. Находим плановые тренировки, которые ещё не наступили, 
    #        и сортируем их по возрастанию planned_for.
    # 1) Все плановые (в том числе, если planned_for в прошлом)
    planned = Workout.objects.filter(
        user=request.user,
        status='planned'
    ).order_by('planned_for')

    # 2) Завершённые
    done = Workout.objects.filter(
        user=request.user,
        status='done'
    ).order_by('-date_time')

    # 3) Объединяем
    all_workouts = list(planned) + list(done)

    # 4) Пагинация
    paginator = Paginator(all_workouts, 10)
    page_number = request.GET.get('page')
    workouts_page = paginator.get_page(page_number)

    # 5) Для статистики категорий
    for w in workouts_page:
        exercises = w.exercises.select_related('exercise_type')
        w.category_stats = calculate_category_percent(exercises)
    
    return render(request, 'fitnessapp/main.html', {
        'workouts': workouts_page,
    })

#--------------------------------------------------------------------------
# СОЗДАНИЕ ТРЕНИРОВКИ (DONE)
#--------------------------------------------------------------------------
@login_required
def workout_view(request):
    """
    Создаёт завершённую тренировку (done).
    Добавлено поле "tracked_weight" для обновления веса пользователя
    (и сохранения веса в самой тренировке).
    """
    if request.method == 'POST':
        # Подсчитываем, сколько тренировок уже есть у пользователя,
        # чтобы назначить следующий номер (workout_number).
        existing_count = Workout.objects.filter(user=request.user).count()
        workout_number = existing_count + 1

        new_workout = Workout.objects.create(
            user=request.user,
            status='done',
            date_time=timezone.now(),
            workout_number=workout_number
        )

        # Получаем введённый вес и обновляем модель пользователя и тренировки
        new_weight_str = request.POST.get('tracked_weight', '').strip()
        if new_weight_str:
            try:
                user_weight = float(new_weight_str.replace(',', '.'))
                request.user.weight = user_weight
                request.user.save()
                new_workout.tracked_weight = user_weight
                new_workout.save()
            except ValueError:
                pass

        # Сохраняем комментарий (если есть)
        comment = request.POST.get('comment', '').strip()
        if comment:
            new_workout.comment = comment
            new_workout.save()

        # Обрабатываем упражнения
        ex_count = int(request.POST.get('exercise_count', 0))
        for i in range(1, ex_count + 1):
            et_id = request.POST.get(f'exercise_type_{i}', '')
            exercise_type_obj = None
            category = None
            if et_id:
                try:
                    exercise_type_obj = ExerciseType.objects.get(id=et_id)
                    category = exercise_type_obj.category
                except ExerciseType.DoesNotExist:
                    pass

            exercise_obj = Exercise.objects.create(
                workout=new_workout,
                exercise_type=exercise_type_obj,
                exercise_number=i
            )

            # Если «Кардио»
            if category == 'Кардио':
                dist_str = request.POST.get(f'exercise_distance_{i}', '').strip()
                hours_str = request.POST.get(f'exercise_hours_{i}', '0').strip()
                mins_str = request.POST.get(f'exercise_minutes_{i}', '0').strip()
                secs_str = request.POST.get(f'exercise_seconds_{i}', '0').strip()

                def safe_int(s):
                    try:
                        return int(s)
                    except ValueError:
                        return 0

                def safe_float(s):
                    try:
                        return float(s.replace(',', '.'))
                    except ValueError:
                        return 0.0

                distance_val = safe_float(dist_str)
                h_val = safe_int(hours_str)
                m_val = safe_int(mins_str)
                s_val = safe_int(secs_str)
                total_seconds = h_val * 3600 + m_val * 60 + s_val

                exercise_obj.distance = distance_val
                exercise_obj.duration = total_seconds
                exercise_obj.save()
            else:
                # Силовое упражнение
                approach_count = int(request.POST.get(f'approach_count_{i}', 0))
                approach_list = []
                for ap in range(1, approach_count + 1):
                    reps_str = request.POST.get(f'approach_{i}_{ap}_reps', '0')
                    weight_str = request.POST.get(f'approach_{i}_{ap}_weight', '0')
                    try:
                        reps_val = int(reps_str)
                    except ValueError:
                        reps_val = 0
                    try:
                        weight_val = float(weight_str.replace(',', '.'))
                    except ValueError:
                        weight_val = 0

                    approach_list.append(
                        ExerciseApproach(
                            exercise=exercise_obj,
                            order=ap,
                            reps=reps_val,
                            weight=weight_val
                        )
                    )
                ExerciseApproach.objects.bulk_create(approach_list)

        # После сохранения создаём редирект на finish_workout
        now = timezone.now()
        monthly_count = Workout.objects.filter(
            user=request.user,
            status='done',
            date_time__year=now.year,
            date_time__month=now.month
        ).count()

        return redirect('finish_workout', workout_id=new_workout.id, month_count=monthly_count)

    else:
        # GET-запрос: показываем форму создания завершённой тренировки
        exercise_types = ExerciseType.objects.all().order_by('name')
        return render(request, 'fitnessapp/workout.html', {
            'exercise_types': exercise_types,
        })

#--------------------------------------------------------------------------
# ПЛАНИРОВАНИЕ ТРЕНИРОВКИ (PLANNED)
#--------------------------------------------------------------------------
@login_required
def plan_workout_view(request):
    """
    Создаёт (или редактирует) запланированную тренировку.
    """
    if request.method == 'POST':
        existing_count = Workout.objects.filter(user=request.user).count()
        workout_number = existing_count + 1

        planned_str = request.POST.get('planned_date_time', '').strip()
        try:
            from django.utils.dateparse import parse_datetime
            planned_dt = parse_datetime(planned_str)
        except:
            planned_dt = None

        # Создаём новую тренировку со статусом "planned"
        new_workout = Workout.objects.create(
            user=request.user,
            status='planned',
            planned_for=planned_dt,
            workout_number=workout_number
        )

        # Сохраняем комментарий (если есть)
        comment = request.POST.get('comment', '').strip()
        new_workout.comment = comment
        new_workout.save()

        # Сохраняем упражнения
        ex_count = int(request.POST.get('exercise_count', 0))
        for i in range(1, ex_count + 1):
            et_id = request.POST.get(f'exercise_type_{i}', '')
            exercise_type_obj = None
            category = None
            if et_id:
                try:
                    exercise_type_obj = ExerciseType.objects.get(id=et_id)
                    category = exercise_type_obj.category
                except ExerciseType.DoesNotExist:
                    pass

            # Создаём Exercise
            exercise_obj = Exercise.objects.create(
                workout=new_workout,
                exercise_type=exercise_type_obj,
                exercise_number=i
            )

            # Если "Кардио" — сохраняем distance/duration
            if category == 'Кардио':
                dist_str = request.POST.get(f'exercise_distance_{i}', '').strip()
                hours_str = request.POST.get(f'exercise_hours_{i}', '0').strip()
                mins_str = request.POST.get(f'exercise_minutes_{i}', '0').strip()
                secs_str = request.POST.get(f'exercise_seconds_{i}', '0').strip()

                def safe_float(s):
                    try:
                        return float(s.replace(',', '.') or 0)
                    except ValueError:
                        return 0.0

                def safe_int(s):
                    try:
                        return int(s or 0)
                    except ValueError:
                        return 0

                distance_val = safe_float(dist_str)
                h_val = safe_int(hours_str)
                m_val = safe_int(mins_str)
                s_val = safe_int(secs_str)
                total_seconds = h_val * 3600 + m_val * 60 + s_val

                exercise_obj.distance = distance_val
                exercise_obj.duration = total_seconds
                exercise_obj.save()
            else:
                # Если силовое, добавим подходы (дропсеты)
                approach_count = int(request.POST.get(f'approach_count_{i}', 0))
                approach_list = []
                for ap in range(1, approach_count + 1):
                    reps_str = request.POST.get(f'approach_{i}_{ap}_reps', '0')
                    weight_str = request.POST.get(f'approach_{i}_{ap}_weight', '0')
                    try:
                        reps_val = int(reps_str)
                    except ValueError:
                        reps_val = 0
                    try:
                        weight_val = float(weight_str.replace(',', '.'))
                    except ValueError:
                        weight_val = 0
                    approach_list.append(
                        ExerciseApproach(
                            exercise=exercise_obj,
                            order=ap,
                            reps=reps_val,
                            weight=weight_val
                        )
                    )
                ExerciseApproach.objects.bulk_create(approach_list)

        return redirect('main')

    else:
        exercise_types = ExerciseType.objects.all().order_by('name')
        return render(request, 'fitnessapp/plan_workout.html', {
            'exercise_types': exercise_types,
        })

#--------------------------------------------------------------------------
# РЕДАКТИРОВАНИЕ ТРЕНИРОВКИ
#--------------------------------------------------------------------------

@login_required
def edit_workout_view(request, workout_id):
    """
    Редактирование существующей тренировки (planned или done).
    Реализована логика:
      - Возможность изменить дату/время (если плановая).
      - Возможность обновить текущий вес (tracked_weight).
      - Удалить тренировку.
      - Завершить плановую (finish_planned).
      - Перейти на страницу finish_workout (оценка).
    """
    workout = get_object_or_404(Workout, id=workout_id, user=request.user)

    def reindex_workouts(user):
        """
        Переиндексация workout_number, если нужно
        сохранить сквозную нумерацию по дате/времени.
        """
        done_w = Workout.objects.filter(user=user, status='done').order_by('date_time')
        planned_w = Workout.objects.filter(user=user, status='planned').order_by('planned_for')
        combined = list(done_w) + list(planned_w)
        for i, w in enumerate(combined, start=1):
            w.workout_number = i
            w.save()

    if request.method == 'POST':
        # Если нажали "Удалить"
        if 'delete_workout' in request.POST:
            user = workout.user
            workout.delete()
            reindex_workouts(user)
            return redirect('main')

        # Если тренировка плановая, даём возможность изменить planned_for
        if workout.status == 'planned':
            planned_str = request.POST.get('planned_date_time', '').strip()
            if planned_str:
                from django.utils.dateparse import parse_datetime
                planned_dt = parse_datetime(planned_str)
                if planned_dt:
                    workout.planned_for = planned_dt

        # Обновляем комментарий
        comment = request.POST.get('comment', '').strip()
        workout.comment = comment

        # Сохраняем (и в user, и в Workout) новый вес
        new_weight_str = request.POST.get('tracked_weight', '').strip()
        if new_weight_str:
            try:
                user_weight = float(new_weight_str.replace(',', '.'))
                request.user.weight = user_weight
                request.user.save()
                workout.tracked_weight = user_weight
            except ValueError:
                pass

        workout.save()

        # Обновляем упражнения
        existing_exercises = {ex.id: ex for ex in workout.exercises.all()}
        ex_count = int(request.POST.get('exercise_count', 0))
        new_exercises = []

        for i in range(1, ex_count + 1):
            exercise_id_str = request.POST.get(f'exercise_id_{i}', '')
            try:
                exercise_id = int(exercise_id_str)
            except (TypeError, ValueError):
                exercise_id = None

            et_id = request.POST.get(f'exercise_type_{i}', '')
            exercise_type_obj = None
            category = None
            if et_id:
                try:
                    exercise_type_obj = ExerciseType.objects.get(id=et_id)
                    category = exercise_type_obj.category
                except ExerciseType.DoesNotExist:
                    pass

            if exercise_id and exercise_id in existing_exercises:
                ex_obj = existing_exercises[exercise_id]
                del existing_exercises[exercise_id]
            else:
                ex_obj = Exercise(workout=workout)

            ex_obj.exercise_type = exercise_type_obj
            ex_obj.exercise_number = i

            if category == 'Кардио':
                dist_str = request.POST.get(f'exercise_distance_{i}', '').strip()
                hours_str = request.POST.get(f'exercise_hours_{i}', '0').strip()
                mins_str = request.POST.get(f'exercise_minutes_{i}', '0').strip()
                secs_str = request.POST.get(f'exercise_seconds_{i}', '0').strip()

                def sfloat(s):
                    try:
                        return float(s.replace(',', '.'))
                    except:
                        return 0.0

                def sint(s):
                    try:
                        return int(s)
                    except:
                        return 0

                ex_obj.distance = sfloat(dist_str)
                total_sec = sint(hours_str)*3600 + sint(mins_str)*60 + sint(secs_str)
                ex_obj.duration = total_sec
            else:
                ex_obj.distance = None
                ex_obj.duration = None

            ex_obj.save()
            new_exercises.append(ex_obj)

        # Удаляем удалённые упражнения
        for leftover_ex in existing_exercises.values():
            leftover_ex.delete()

        # Вновь создаём подходы
        for i in range(1, ex_count + 1):
            ex_obj = new_exercises[i - 1]
            if ex_obj.exercise_type and ex_obj.exercise_type.category == 'Кардио':
                continue  # У кардио нет подходов

            # Удаляем предыдущие подходы
            ex_obj.approaches.all().delete()

            approach_count = int(request.POST.get(f'approach_count_{i}', 0))
            approach_list = []
            for ap_idx in range(1, approach_count + 1):
                reps_str = request.POST.get(f'approach_{i}_{ap_idx}_reps', '0')
                weight_str = request.POST.get(f'approach_{i}_{ap_idx}_weight', '0')
                try:
                    reps_val = int(reps_str)
                except:
                    reps_val = 0
                try:
                    weight_val = float(weight_str.replace(',', '.'))
                except:
                    weight_val = 0
                approach_list.append(ExerciseApproach(
                    exercise=ex_obj,
                    order=ap_idx,
                    reps=reps_val,
                    weight=weight_val
                ))
            ExerciseApproach.objects.bulk_create(approach_list)

        # Если нажали "Завершить плановую тренировку"
        if 'finish_planned' in request.POST:
            if workout.status == 'planned':
                workout.status = 'done'
                workout.date_time = timezone.now()
                workout.planned_for = None
                workout.save()

            reindex_workouts(request.user)
            now = timezone.now()
            monthly_count = Workout.objects.filter(
                user=request.user, status='done',
                date_time__year=now.year,
                date_time__month=now.month
            ).count()

            return redirect('finish_workout', workout_id=workout.id, month_count=monthly_count)

        # Если не плановая/не завершали — сохраняем и редиректим на главную
        return redirect('main')

    else:
        # GET-запрос: формируем JSON для подгрузки динамических полей
        exercises_qs = workout.exercises.all().order_by('exercise_number')
        exercises_data = []
        for ex in exercises_qs:
            cat = ex.exercise_type.category if ex.exercise_type else ''
            h, m, s = 0, 0, 0
            if ex.duration:
                h = ex.duration // 3600
                m = (ex.duration % 3600) // 60
                s = ex.duration % 60

            approaches_qs = ex.approaches.order_by('order')
            approaches_list = []
            for ap in approaches_qs:
                approaches_list.append({
                    'order': ap.order,
                    'reps': ap.reps,
                    'weight': str(ap.weight) if ap.weight is not None else '0'
                })

            exercises_data.append({
                'exercise_id': ex.id,
                'type_id': ex.exercise_type.id if ex.exercise_type else '',
                'type_name': ex.exercise_type.name if ex.exercise_type else '',
                'category': cat,
                'distance': str(ex.distance if ex.distance else ''),
                'hours': h,
                'minutes': m,
                'seconds': s,
                'approaches': approaches_list
            })

        exercise_types = ExerciseType.objects.all().order_by('name')
        context = {
            'workout': workout,
            'exercises_data': json.dumps(exercises_data),
            'exercise_types': exercise_types,
        }
        return render(request, 'fitnessapp/edit_workout.html', context)
#--------------------------------------------------------------------------
# ПОКАЗАТЬ ВСЕ ТРЕНИРОВКИ (ПО МЕСЯЦАМ)
#--------------------------------------------------------------------------
@login_required
def show_all_workouts(request):
    """
    Отображает все тренировки по месяцам.
    """
    all_wk = Workout.objects.filter(user=request.user).order_by('-date_time', '-planned_for')
    grouped = ddict(list)
    for w in all_wk:
        dt = w.date_time if w.status == 'done' else (w.planned_for or w.date_time)
        ym = (dt.year, dt.month)
        grouped[ym].append(w)

    grouped_list = []
    for (y, m), w_list in grouped.items():
        grouped_list.append((y, m, w_list))
    grouped_list.sort(key=lambda x: (x[0], x[1]), reverse=True)

    month_stats = []
    for (y, m, w_list) in grouped_list:
        total_workouts = len(w_list)
        total_exercises = sum(w.exercises.count() for w in w_list)
        month_stats.append({
            'year': y,
            'month': m,
            'workouts': w_list,
            'count_workouts': total_workouts,
            'count_exercises': total_exercises
        })

    for ms in month_stats:
        for w in ms['workouts']:
            exercises = w.exercises.select_related('exercise_type')
            w.category_stats = calculate_category_percent(exercises)

    for i, ms in enumerate(month_stats):
            curr_w = ms['count_workouts']
            curr_e = ms['count_exercises']
            ms['mom_workouts'] = curr_w
            ms['mom_exercises'] = curr_e


    return render(request, 'fitnessapp/show_all_workouts.html', {
        'month_stats': month_stats,
    })

#--------------------------------------------------------------------------
# АНАЛИТИКА (DASHBOARD)
#--------------------------------------------------------------------------
@login_required
def dashboard_view(request):
    """
    Страница аналитики: строим графики по тренировкам, весу пользователя,
    а также разбивку по категориям упражнений (кардио/силовые).
    Содержит логику:
      - Подсчёт кол-ва тренировок в текущем месяце (count_workouts)
      - Среднего кол-ва упражнений за месяц (avg_exercises)
      - Общего среднего веса пользователя (user_avg_weight)
      - Сбор подробной статистики для построения графиков: 
        1) Кол-во тренировок и средний вес — помесячно, понедельно, по годам.
        2) Упражнения (силовые/кардио) — вес или дистанция (days, months, years).
        3) Разбивка по категориям упражнений.
    """

    user = request.user
    now = timezone.now()
    current_year = now.year
    current_month = now.month

    # ------------------ 1) Статистика за ТЕКУЩИЙ месяц ------------------
    monthly_workouts = Workout.objects.filter(
        user=user,
        status='done',
        date_time__year=current_year,
        date_time__month=current_month
    )

    count_workouts = monthly_workouts.count()
    total_ex_count = sum(w.exercises.count() for w in monthly_workouts)
    avg_exercises = total_ex_count / count_workouts if count_workouts else 0

    # ------------------ 2) Общая статистика по всем тренировкам history ------------------
    all_user_workouts = Workout.objects.filter(user=user, status='done').order_by('date_time')
    total_workouts_all_time = all_user_workouts.count()
    total_ex_count_all_time = sum(w.exercises.count() for w in all_user_workouts)

    # Собираем данные по весу за все законченные тренировки
    all_weights = [w.tracked_weight for w in all_user_workouts if w.tracked_weight is not None]
    user_avg_weight = sum(all_weights) / len(all_weights) if all_weights else 0

    # Средний вес в текущем месяце
    monthly_weights = [w.tracked_weight for w in monthly_workouts if w.tracked_weight is not None]
    monthly_avg_weight = sum(monthly_weights)/len(monthly_weights) if monthly_weights else 0

    # ------------------ Минимальная и максимальная дата тренировок (для доп.логики) ------------------
    qs_workouts = Workout.objects.filter(user=user, status='done')
    min_date = qs_workouts.aggregate(Min('date_time'))['date_time__min']
    max_date = qs_workouts.aggregate(Max('date_time'))['date_time__max']

    # Если у пользователя нет завершённых тренировок, выведем шаблон с нулевыми данными
    if not min_date or not max_date:
        return render(request, 'fitnessapp/dashboard.html', {
            'count_workouts': count_workouts,
            'avg_exercises': avg_exercises,
            'monthly_avg_weight': monthly_avg_weight,
            'total_workouts_all_time': total_workouts_all_time,
            'total_ex_count_all_time': total_ex_count_all_time,
            'user_avg_weight': round(user_avg_weight, 1),
            # Пустые словари/списки для графиков:
            'stats_all_json': json.dumps({}),
            'exercise_stats_json': json.dumps({}),
            'stats_categories_json': json.dumps({}),
        })

    # ------------------ 3) Группировка тренировок (помесячно, понедельно, по годам) ------------------
    # Для графика "Тренировки vs. Средний вес"
    workouts_by_month = (
        qs_workouts
        .annotate(y=ExtractYear('date_time'), m=ExtractMonth('date_time'))
        .values('y', 'm')
        .annotate(
            count=Count('id'),
            avg_weight=Avg('tracked_weight')
        )
        .order_by('y', 'm')
    )
    MONTH_NAMES = ["янв", "фев", "мар", "апр", "май", "июн",
                   "июл", "авг", "сен", "окт", "ноя", "дек"]

    stats_month = []
    for row in workouts_by_month:
        y, m = row['y'], row['m']
        cnt = row['count'] or 0
        avgw = row['avg_weight'] if row['avg_weight'] is not None else 0
        period_label = f"{MONTH_NAMES[m-1]} {str(y)[-2:]}"
        stats_month.append({
            "month_label": period_label,
            "year": y,
            "month": m,
            "count": cnt,
            "avg_weight": float(avgw),
        })

    workouts_by_week = (
        qs_workouts
        .annotate(y=ExtractYear('date_time'), w=ExtractWeek('date_time'))
        .values('y', 'w')
        .annotate(
            count=Count('id'),
            avg_weight=Avg('tracked_weight')
        )
        .order_by('y', 'w')
    )
    stats_week = []
    for row in workouts_by_week:
        y, w = row['y'], row['w']
        cnt = row['count'] or 0
        avgw = row['avg_weight'] if row['avg_weight'] is not None else 0
        period_label = f"{y}-W{w}"
        stats_week.append({
            "period_label": period_label,
            "year": y,
            "week": w,
            "count": cnt,
            "avg_weight": float(avgw),
        })

    workouts_by_year = (
        qs_workouts
        .annotate(y=ExtractYear('date_time'))
        .values('y')
        .annotate(
            count=Count('id'),
            avg_weight=Avg('tracked_weight')
        )
        .order_by('y')
    )
    stats_year = []
    for row in workouts_by_year:
        y = row['y']
        cnt = row['count'] or 0
        avgw = row['avg_weight'] if row['avg_weight'] is not None else 0
        stats_year.append({
            "period_label": str(y),
            "year": y,
            "count": cnt,
            "avg_weight": float(avgw),
        })

    stats_all = {
        "month": stats_month,
        "week": stats_week,
        "year": stats_year
    }
     # ------------------ 4) Статистика упражнений (силовые/кардио) ------------------

    all_ex = Exercise.objects.filter(
        workout__user=user,
        workout__status='done'
    ).select_related('workout', 'exercise_type')

    # Собираем: ex_name => category (например, "Кардио" или "")
    ex_name_category = {}
    for ex in all_ex:
        if ex.exercise_type:
            ex_name_category[ex.exercise_type.name] = ex.exercise_type.category or ''

    # Подготовим структуру для хранения результатов
    # "days" - несколько последних дней, "months", "years" + какой-нибудь "category"
    exercise_stats = ddict(lambda: {
        "days": [],
        "months": [],
        "years": [],
        "category": ""
    })

    # Заполним category для каждого названия упражнения
    for ex_name, cat in ex_name_category.items():
        exercise_stats[ex_name]["category"] = cat

    # 4A) Для каждого упражнения — история за последние 6 "дней"/тренировок
    ex_names = set(
        all_ex.filter(exercise_type__isnull=False)
              .values_list('exercise_type__name', flat=True)
    )

    for ex_name in ex_names:
        cat = ex_name_category.get(ex_name, '')
        # Берём последние 6 тренировок
        qs_ex = all_ex.filter(exercise_type__name=ex_name).order_by('-workout__date_time')
        last_6 = qs_ex[:6]
        day_entries = []

        for obj in reversed(last_6):
            date_str = obj.workout.date_time.strftime("%Y-%m-%d")
            if cat == 'Кардио':
                # Для кардио — distance
                distance_val = float(obj.distance or 0)
                day_entries.append({
                    "date": date_str,
                    "distance": distance_val
                })
            else:
                # Для силовых — вес берём из подходов (максимальный или можно средний)
                approaches = obj.approaches.all()
                if approaches.exists():
                    wval = max(a.weight for a in approaches if a.weight is not None)
                else:
                    wval = 0
                day_entries.append({
                    "date": date_str,
                    "weight": float(wval)
                })

        exercise_stats[ex_name]["days"] = day_entries

    # 4B) Группировка "помесячно"
    ex_by_month = (
        all_ex
        .annotate(yy=ExtractYear('workout__date_time'),
                  mm=ExtractMonth('workout__date_time'))
        .values('exercise_type__name', 'yy', 'mm')
        .order_by('exercise_type__name', 'yy', 'mm')
    )
    aggregator_month = ddict(list)

    for row in ex_by_month:
        ename = row['exercise_type__name']
        y, m = row['yy'], row['mm']
        cat = ex_name_category.get(ename, '')
        sub_qs = all_ex.filter(
            exercise_type__name=ename,
            workout__date_time__year=y,
            workout__date_time__month=m
        )
        if sub_qs.exists():
            if cat == 'Кардио':
                # Считаем среднюю дистанцию
                dists = [float(x.distance or 0) for x in sub_qs]
                avg_dist = sum(dists)/len(dists) if dists else 0
                aggregator_month[(ename, y, m)].append(avg_dist)
            else:
                # Силовые — считаем средний (или max) вес из подходов
                w_list = []
                for eobj in sub_qs:
                    for ap in eobj.approaches.all():
                        if ap.weight is not None:
                            w_list.append(float(ap.weight))
                avg_w = sum(w_list)/len(w_list) if w_list else 0
                aggregator_month[(ename, y, m)].append(avg_w)

    for (ename, y, m), arr in aggregator_month.items():
        val = sum(arr)/len(arr)
        period_str = f"{y}-{m:02d}"
        exercise_stats[ename]["months"].append({
            "period": period_str,
            "distance" if ex_name_category.get(ename, '') == 'Кардио' else "weight": float(val)
        })

    # 4C) Группировка "по годам"
    ex_by_year = (
        all_ex
        .annotate(yy=ExtractYear('workout__date_time'))
        .values('exercise_type__name', 'yy')
        .order_by('exercise_type__name', 'yy')
    )
    aggregator_year = ddict(list)

    for row in ex_by_year:
        ename = row['exercise_type__name']
        yy = row['yy']
        cat = ex_name_category.get(ename, '')
        sub_qs = all_ex.filter(
            exercise_type__name=ename,
            workout__date_time__year=yy
        )
        if sub_qs.exists():
            if cat == 'Кардио':
                dists = [float(x.distance or 0) for x in sub_qs]
                avg_dist = sum(dists)/len(dists) if dists else 0
                aggregator_year[(ename, yy)].append(avg_dist)
            else:
                w_list = []
                for eobj in sub_qs:
                    for ap in eobj.approaches.all():
                        if ap.weight is not None:
                            w_list.append(float(ap.weight))
                avg_w = sum(w_list)/len(w_list) if w_list else 0
                aggregator_year[(ename, yy)].append(avg_w)

    for (ename, yy), arr in aggregator_year.items():
        val = sum(arr)/len(arr)
        exercise_stats[ename]["years"].append({
            "period": str(yy),
            "distance" if ex_name_category.get(ename, '') == 'Кардио' else "weight": float(val)
        })

    exercise_stats = dict(exercise_stats)

    # ------------------ 5) Разбивка по категориям (для донат-графиков и т.п.) ------------------
    stats_categories = {"month": [], "week": [], "year": []}

    ex_by_month_cat = (
        all_ex
        .annotate(y=ExtractYear('workout__date_time'),
                  m=ExtractMonth('workout__date_time'))
        .values('y', 'm', 'exercise_type__category')
        .annotate(cnt=Count('id'))
        .order_by('y', 'm', 'exercise_type__category')
    )
    month_map = ddict(lambda: ddict(int))
    for row in ex_by_month_cat:
        y, m = row['y'], row['m']
        cat = row['exercise_type__category'] or "Прочее"
        month_map[(y, m)][cat] += row['cnt']

    month_list = []
    for (yy, mm), cat_dict in sorted(month_map.items()):
        lbl = f"{MONTH_NAMES[mm-1]} {str(yy)[-2:]}"
        month_list.append({
            "period_label": lbl,
            "year": yy,
            "month": mm,
            "categories": dict(cat_dict)
        })
    stats_categories["month"] = month_list

    ex_by_week_cat = (
        all_ex
        .annotate(y=ExtractYear('workout__date_time'),
                  w=ExtractWeek('workout__date_time'))
        .values('y', 'w', 'exercise_type__category')
        .annotate(cnt=Count('id'))
        .order_by('y', 'w', 'exercise_type__category')
    )
    week_map = ddict(lambda: ddict(int))
    for row in ex_by_week_cat:
        y, w = row['y'], row['w']
        cat = row['exercise_type__category'] or "Прочее"
        week_map[(y, w)][cat] += row['cnt']

    week_list = []
    for (yy, ww), cat_dict in sorted(week_map.items()):
        lbl = f"{yy}-W{ww}"
        week_list.append({
            "period_label": lbl,
            "year": yy,
            "week": ww,
            "categories": dict(cat_dict)
        })
    stats_categories["week"] = week_list

    ex_by_year_cat = (
        all_ex
        .annotate(y=ExtractYear('workout__date_time'))
        .values('y', 'exercise_type__category')
        .annotate(cnt=Count('id'))
        .order_by('y', 'exercise_type__category')
    )
    year_map = ddict(lambda: ddict(int))
    for row in ex_by_year_cat:
        y = row['y']
        cat = row['exercise_type__category'] or "Прочее"
        year_map[y][cat] += row['cnt']

    year_list = []
    for yy, cat_dict in sorted(year_map.items()):
        lbl = str(yy)
        year_list.append({
            "period_label": lbl,
            "year": yy,
            "categories": dict(cat_dict)
        })
    stats_categories["year"] = year_list

    stats_categories_json = json.dumps(stats_categories, ensure_ascii=False)

    # ------------------ 6) Рендерим шаблон с графиками ------------------
    return render(request, 'fitnessapp/dashboard.html', {
        'count_workouts': count_workouts,
        'avg_exercises': avg_exercises,
        'user_avg_weight': round(user_avg_weight, 1),
        'stats_all_json': json.dumps(stats_all, ensure_ascii=False),
        'exercise_stats_json': json.dumps(exercise_stats, ensure_ascii=False),
        'stats_categories_json': stats_categories_json,
    })

#--------------------------------------------------------------------------
# СПИСОК ПОЛЬЗОВАТЕЛЕЙ
#--------------------------------------------------------------------------
@login_required
def users_view(request):
    """
    Отображает список пользователей.
    """
    users = JarvisUser.objects.all()
    data = []
    for u in users:
        w_qs = u.workouts.filter(status='done')
        total_w = w_qs.count()
        w_weights = [w.tracked_weight for w in w_qs if w.tracked_weight is not None]
        if w_weights:
            average_weight = round(sum(w_weights) / len(w_weights), 1)
        else:
            average_weight = u.weight if u.weight else 0
        age_val = u.get_age() or 0
        data.append({
            'user': u,
            'username': u.username,
            'first_name': u.first_name,
            'age': age_val,
            'weight': u.weight,
            'total_workouts': total_w,
            'average_weight': average_weight,
        })

    sort_param = request.GET.get('sort')
    if sort_param == 'age':
        data.sort(key=lambda x: x['age'] if x['age'] else 0)
    elif sort_param == 'weight':
        data.sort(key=lambda x: x['weight'] if x['weight'] else 0, reverse=True)
    elif sort_param == 'workouts':
        data.sort(key=lambda x: x['total_workouts'], reverse=True)

    return render(request, 'fitnessapp/users.html', {'data': data})

#--------------------------------------------------------------------------
# НАСТРОЙКИ
#--------------------------------------------------------------------------
@login_required
def settings_view(request):
    """
    Обрабатывает настройки пользователя.
    """
    if request.method == 'POST':
        form = SettingsForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('main')
    else:
        form = SettingsForm(instance=request.user)
    return render(request, 'fitnessapp/settings.html', {'form': form})

#--------------------------------------------------------------------------
# ДЕТАЛИ ПОЛЬЗОВАТЕЛЯ
#--------------------------------------------------------------------------
@login_required
def user_detail_view(request, username):
    """
    Отображает детали пользователя.
    """
    target_user = get_object_or_404(JarvisUser, username=username)
    now = timezone.now()
    current_year = now.year
    current_month = now.month

    monthly_qs = Workout.objects.filter(
        user=target_user, 
        status='done',
        date_time__year=current_year,
        date_time__month=current_month
    )
    monthly_count_workouts = monthly_qs.count()
    monthly_ex_count = sum(w.exercises.count() for w in monthly_qs)
    if monthly_count_workouts > 0:
        monthly_avg_ex = monthly_ex_count / monthly_count_workouts
    else:
        monthly_avg_ex = 0

    w_weights = Workout.objects.filter(
        user=target_user,
        status='done',
        tracked_weight__isnull=False
    )
    if w_weights.exists():
        sum_w = sum(float(x.tracked_weight) for x in w_weights)
        avg_weight = round(sum_w / w_weights.count(), 1)
    else:
        avg_weight = None

    MONTH_NAMES = ['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек']
    monthly_data = []
    for m in range(1, 13):
        w_qs = Workout.objects.filter(
            user=target_user,
            status='done',
            date_time__year=current_year,
            date_time__month=m
        )
        cnt_w = w_qs.count()
        label = f"{MONTH_NAMES[m - 1]} {str(current_year)[-2:]}"
        weight_values = [w.tracked_weight for w in w_qs if w.tracked_weight is not None]
        if weight_values:
            avg_weight_for_month = sum(weight_values) / len(weight_values)
        else:
            avg_weight_for_month = 0
        monthly_data.append({
            'month_label': label,
            'count': cnt_w,
            'avg_weight': float(avg_weight_for_month),
        })
    monthly_stats_json = json.dumps(monthly_data)

    all_workouts = Workout.objects.filter(user=target_user).order_by('-date_time', '-planned_for')
    paginator = Paginator(all_workouts, 20)
    page_number = request.GET.get('page')
    workouts_page = paginator.get_page(page_number)

    for w in workouts_page:
        exercises = w.exercises.select_related('exercise_type')
        w.category_stats = calculate_category_percent(exercises)

    return render(request, 'fitnessapp/user_detail.html', {
        'target_user': target_user,
        'monthly_count_workouts': monthly_count_workouts,
        'monthly_avg_ex': monthly_avg_ex,
        'avg_weight': avg_weight,
        'current_year': current_year,
        'monthly_stats_json': monthly_stats_json,
        'workouts_page': workouts_page,
    })

#--------------------------------------------------------------------------
# ФИНИШ ТРЕНИРОВКИ (выставление оценки)
#--------------------------------------------------------------------------
@login_required
def finish_workout_view(request, workout_id, month_count):
    """
    Показывает страницу «Поздравляем!» с формой для выставления оценки.
    Добавили логику определения: была ли тренировка уже "done" до этого?
    """
    workout = get_object_or_404(Workout, id=workout_id, user=request.user)

    # НОВОЕ: проверяем, была ли тренировка изначально завершенной и имела ли рейтинг
    was_already_done = (workout.status == 'done')

    if request.method == 'POST':
        rating_str = request.POST.get('rating')
        try:
            rating_val = int(rating_str)
        except (TypeError, ValueError):
            return HttpResponseBadRequest("Некорректное значение оценки.")

        if rating_val < 1 or rating_val > 5:
            return HttpResponseBadRequest("Оценка должна быть в диапазоне 1..5.")

        workout.rating = rating_val
        # Если вдруг тренировка была ещё planned, то переведём в done
        if workout.status == 'planned':
            workout.status = 'done'
            workout.date_time = timezone.now()
            workout.planned_for = None

        workout.save()
        return redirect('main')

    # month_count, возможно, формируется где-то выше. Если вызываем повторно — иногда 0. 
    # Можем проверить, если тренировка уже была done, то всё равно month_count = фактическое число.
    # Но если мы хотим динамически пересчитать месяц:
    if was_already_done:
        # Пересчитаем номер для сообщений
        now = timezone.now()
        month_count = Workout.objects.filter(
            user=request.user,
            status='done',
            date_time__year=now.year,
            date_time__month=now.month
        ).count()

    context = {
        'workout': workout,
        'month_count': month_count,
        'was_already_done': was_already_done,  # ← передадим шаблону
    }
    return render(request, 'fitnessapp/workout_congrats.html', context)


@login_required
def finish_planned_view(request, workout_id):
    """
    Завершает запланированную тренировку, меняя её статус на 'done'.
    """
    workout = get_object_or_404(Workout, pk=workout_id, user=request.user)
    if workout.status == 'planned':
        workout.status = 'done'
        workout.date_time = timezone.now()
        workout.planned_for = None  # Обнуляем дату запланированной тренировки
        workout.save()
    return redirect('main')  # Перенаправляем на главную страницу


@login_required
def calendar_full_view(request):
    return render(request, 'fitnessapp/calendar_full.html')


@login_required
def calendar_data_view(request):
    """
    Возвращает JSON-список тренировок в формате, где в title
    #номер (комментарий); добавляем "url": чтобы при клике
    открывалась страница workout_detail.
    """
    user = request.user
    workouts = Workout.objects.filter(user=user)

    events = []
    for w in workouts:
        comment = (w.comment or '').strip()
        if len(comment) > 20:
            comment = comment[:20] + '...'

        title_str = f"№{w.workout_number}"
        if comment:
            title_str += f" ({comment})"

        if w.status == 'planned' and w.planned_for:
            start_date = w.planned_for.date().isoformat()
        else:
            start_date = w.date_time.date().isoformat()

        # Важно: добавляем поле "url":
        events.append({
            "title": title_str,
            "start": start_date,
            "status": w.status,
            "url": reverse('workout_detail', args=[w.id])  # при клике переходим
        })

    from django.http import JsonResponse
    return JsonResponse(events, safe=False)


@login_required
def workout_detail_view(request, workout_id):
    workout = get_object_or_404(Workout, pk=workout_id, user=request.user)
    exercises = workout.exercises.select_related('exercise_type')
    
    # Вычисляем процентное распределение категорий
    category_stats = calculate_category_percent(exercises)
    
    # И либо присваиваем workout.category_stats,
    # либо передаём в контекст отдельной переменной:
    workout.category_stats = category_stats
    
    return render(request, 'fitnessapp/workout_detail.html', {
        'workout': workout,
    })