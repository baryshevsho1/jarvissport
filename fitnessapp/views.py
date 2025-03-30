from collections import defaultdict
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .forms import RegistrationForm, LoginForm, SettingsForm
from .models import JarvisUser, Workout, Exercise, ExerciseType
from .utils import calculate_category_percent  # НОВЫЙ импорт!
from django.core.paginator import Paginator
import json
from django.urls import reverse
from django.db.models import Min, Max, Avg, Count, F
from django.db.models.functions import ExtractWeek, ExtractYear, ExtractMonth

def registration_view(request):
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
    logout(request)
    return redirect('login')


@login_required
def main_view(request):
    """
    Главная страница: показывает тренировки с пагинацией.
    """
    all_workouts = Workout.objects.filter(user=request.user).order_by('-date_time')
    paginator = Paginator(all_workouts, 10)  # Показывать по 20 тренировок на странице
    page_number = request.GET.get('page')
    workouts_page = paginator.get_page(page_number)

    for w in workouts_page:
        exercises = w.exercises.select_related('exercise_type')
        w.category_stats = calculate_category_percent(exercises)

    # Проверяем, пришли ли параметры для модального окна
    new_wid = request.GET.get('new_wid')
    month_count = request.GET.get('month_count')

    return render(request, 'fitnessapp/main.html', {
        'workouts': workouts_page,
        'new_wid': new_wid,
        'month_count': month_count,
    })


@login_required
def workout_view(request):
    """
    Создание и сохранение новой тренировки.
    После отправки формы:
      1) Создаём Workout и Exercises (кардио/силовые).
      2) Обновляем вес пользователя (tracked_weight).
      3) Сохраняем комментарий.
      4) Подсчитываем, какая это тренировка в ТЕКУЩЕМ месяце (month_count).
      5) Редиректим на 'main' с GET-параметрами '?new_wid=...&month_count=...',
         чтобы там показать модальное окно с поздравлением и рейтингом.
    """
    if request.method == 'POST':
        # 1. Определяем порядковый номер для новой тренировки
        existing_count = Workout.objects.filter(user=request.user).count()
        workout_number = existing_count + 1

        # Создаём новую тренировку
        new_workout = Workout.objects.create(
            user=request.user,
            date_time=timezone.now(),
            workout_number=workout_number
        )

        # 2. Сохраняем вес пользователя
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

        # 3. Сохраняем комментарий
        comment = request.POST.get('comment', '').strip()
        if comment:
            new_workout.comment = comment
            new_workout.save()

        # 4. Сохранение упражнений (как кардио, так и силовых)
        ex_count = int(request.POST.get('exercise_count', 0))
        exercise_list = []
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

            if category == 'Кардио':
                dist_str = request.POST.get(f'exercise_distance_{i}', '').strip()
                hours_str = request.POST.get(f'exercise_hours_{i}', '0').strip()
                mins_str = request.POST.get(f'exercise_minutes_{i}', '0').strip()
                secs_str = request.POST.get(f'exercise_seconds_{i}', '0').strip()

                try:
                    distance_val = float(dist_str.replace(',', '.')) if dist_str else 0
                except ValueError:
                    distance_val = 0
                try:
                    h_val = int(hours_str)
                except ValueError:
                    h_val = 0
                try:
                    m_val = int(mins_str)
                except ValueError:
                    m_val = 0
                try:
                    s_val = int(secs_str)
                except ValueError:
                    s_val = 0
                total_seconds = h_val * 3600 + m_val * 60 + s_val

                exercise_list.append(
                    Exercise(
                        workout=new_workout,
                        exercise_type=exercise_type_obj,
                        exercise_number=i,
                        distance=distance_val,
                        duration=total_seconds
                    )
                )
            else:
                ex_sets_str = request.POST.get(f'exercise_sets_{i}', '0').strip()
                ex_reps_str = request.POST.get(f'exercise_reps_{i}', '0').strip()
                ex_weight_str = request.POST.get(f'exercise_weight_{i}', '').strip()

                try:
                    sets_val = int(ex_sets_str)
                except ValueError:
                    sets_val = 0
                try:
                    reps_val = int(ex_reps_str)
                except ValueError:
                    reps_val = 0
                try:
                    weight_val = float(ex_weight_str.replace(',', '.')) if ex_weight_str else None
                except ValueError:
                    weight_val = None

                exercise_list.append(
                    Exercise(
                        workout=new_workout,
                        exercise_type=exercise_type_obj,
                        exercise_number=i,
                        sets=sets_val,
                        reps=reps_val,
                        exercise_weight=weight_val
                    )
                )

        # bulk_create для оптимальной вставки
        Exercise.objects.bulk_create(exercise_list)

        # 5. Подсчитаем, которая это тренировка в текущем месяцe
        now = timezone.now()
        monthly_count = Workout.objects.filter(
            user=request.user,
            date_time__year=now.year,
            date_time__month=now.month
        ).count()

        # Формируем URL с GET-параметрами для показа модального окна
        redirect_url = reverse('finish_workout', kwargs={'workout_id': new_workout.id, 'month_count': monthly_count})

        return redirect('finish_workout', workout_id=new_workout.id, month_count=monthly_count)

    else:
        # Если GET-запрос — показываем форму добавления тренировки
        exercise_types = ExerciseType.objects.all().order_by('name')
        return render(request, 'fitnessapp/workout.html', {
            'exercise_types': exercise_types,
        })

@login_required
def edit_workout_view(request, workout_id):
    """
    Редактирование существующей тренировки.

    1) Если нажата кнопка удаления:
       - удаляем полностью текущую тренировку (Workout + связанные Exercise),
       - пересчитываем номера тренировок для оставшихся тренировок пользователя.
    
    2) Если идёт обычное сохранение (POST без удаления):
       - обновляем комментарий,
       - полностью пересоздаём список упражнений внутри этой тренировки.
    
    3) Если GET-запрос:
       - отображаем в шаблоне все данные тренировки (комментарий, упражнения),
         чтобы пользователь мог их отредактировать.
    """

    def reindex_workouts(user):
        """
        Переиндексировать поле workout_number у всех тренировок пользователя
        в порядке возрастания даты (date_time).
        Например, если были тренировки #1, #2, #3, и мы удаляем #2,
        оставшиеся становятся #1 и #2.
        """
        all_workouts = Workout.objects.filter(user=user).order_by('date_time')
        for i, w in enumerate(all_workouts, start=1):
            w.workout_number = i
            w.save()

    # Получаем тренировку или возвращаем 404 при отсутствии
    workout = get_object_or_404(Workout, id=workout_id, user=request.user)

    # ---------------------------------------------------------------------
    # 1) УДАЛЕНИЕ ТРЕНИРОВКИ
    # ---------------------------------------------------------------------
    if request.method == 'POST' and 'delete_workout' in request.POST:
        current_user = workout.user
        workout.delete()                 # Удаляем сам Workout (Exercises удаляются каскадно)
        reindex_workouts(current_user)   # Переиндексация оставшихся
        return redirect('main')

    # ---------------------------------------------------------------------
    # 2) СОХРАНЕНИЕ ОТРЕДАКТИРОВАННЫХ ДАННЫХ ТРЕНИРОВКИ
    # ---------------------------------------------------------------------
    if request.method == 'POST':
        # Сохраняем комментарий
        comment = request.POST.get('comment', '').strip()
        workout.comment = comment
        workout.save()

        # Удаляем все ранее сохранённые упражнения, чтобы пересоздать заново
        workout.exercises.all().delete()

        ex_count = int(request.POST.get('exercise_count', 0))
        new_exercise_list = []
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

            if category == 'Кардио':
                # Считываем данные кардио: дистанция, время
                dist_str = request.POST.get(f'exercise_distance_{i}', '').strip()
                hours_str = request.POST.get(f'exercise_hours_{i}', '0').strip()
                mins_str = request.POST.get(f'exercise_minutes_{i}', '0').strip()
                secs_str = request.POST.get(f'exercise_seconds_{i}', '0').strip()

                try:
                    distance_val = float(dist_str.replace(',', '.')) if dist_str else 0
                except ValueError:
                    distance_val = 0

                def safe_int(s):
                    try:
                        return int(s)
                    except ValueError:
                        return 0

                h_val = safe_int(hours_str)
                m_val = safe_int(mins_str)
                s_val = safe_int(secs_str)
                total_seconds = h_val * 3600 + m_val * 60 + s_val

                new_exercise_list.append(
                    Exercise(
                        workout=workout,
                        exercise_type=exercise_type_obj,
                        exercise_number=i,
                        distance=distance_val,
                        duration=total_seconds
                    )
                )
            else:
                # Считываем данные силового упражнения: подходы, повторения, вес
                ex_sets_str = request.POST.get(f'exercise_sets_{i}', '0').strip()
                ex_reps_str = request.POST.get(f'exercise_reps_{i}', '0').strip()
                ex_weight_str = request.POST.get(f'exercise_weight_{i}', '').strip()

                try:
                    sets_val = int(ex_sets_str)
                except ValueError:
                    sets_val = 0
                try:
                    reps_val = int(ex_reps_str)
                except ValueError:
                    reps_val = 0
                try:
                    weight_val = float(ex_weight_str.replace(',', '.')) if ex_weight_str else None
                except ValueError:
                    weight_val = None

                new_exercise_list.append(
                    Exercise(
                        workout=workout,
                        exercise_type=exercise_type_obj,
                        exercise_number=i,
                        sets=sets_val,
                        reps=reps_val,
                        exercise_weight=weight_val
                    )
                )

        # Сохраняем все созданные объекты Exercise
        Exercise.objects.bulk_create(new_exercise_list)
        return redirect('main')

    # ---------------------------------------------------------------------
    # 3) ПОДГОТОВКА ДАННЫХ ДЛЯ ФОРМЫ (GET-запрос)
    # ---------------------------------------------------------------------
    exercises_qs = workout.exercises.all().order_by('exercise_number')
    exercises_data = []
    for ex in exercises_qs:
        cat = ex.exercise_type.category if ex.exercise_type else ''
        durations = {'hours': 0, 'minutes': 0, 'seconds': 0}
        if ex.duration:
            total_sec = ex.duration
            durations['hours'] = total_sec // 3600
            durations['minutes'] = (total_sec % 3600) // 60
            durations['seconds'] = total_sec % 60

        exercises_data.append({
            'type_id': ex.exercise_type.id if ex.exercise_type else '',
            'type_name': ex.exercise_type.name if ex.exercise_type else '',
            'category': cat,
            'sets': ex.sets,
            'reps': ex.reps,
            'weight': str(ex.exercise_weight) if ex.exercise_weight is not None else '',
            'distance': str(ex.distance if ex.distance else ''),
            'hours': durations['hours'],
            'minutes': durations['minutes'],
            'seconds': durations['seconds'],
        })

    exercise_types = ExerciseType.objects.all().order_by('name')
    context = {
        'workout': workout,
        'exercises_data': exercises_data,
        'exercise_types': exercise_types,
    }
    return render(request, 'fitnessapp/edit_workout.html', context)

@login_required
def show_all_workouts(request):
    """
    Отображаем все тренировки по месяцам, считаем MoM и процент категорий.
    """
    all_wk = Workout.objects.filter(user=request.user).order_by('-date_time')
    grouped = defaultdict(list)
    for w in all_wk:
        ym = (w.date_time.year, w.date_time.month)
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

    for i, ms in enumerate(month_stats):
        if i == len(month_stats) - 1:
            ms['mom_workouts'] = None
            ms['mom_exercises'] = None
        else:
            prev = month_stats[i + 1]
            prev_w = prev['count_workouts']
            prev_e = prev['count_exercises']
            curr_w = ms['count_workouts']
            curr_e = ms['count_exercises']

            ms['mom_workouts'] = ((curr_w - prev_w) / abs(prev_w) * 100) if prev_w else None
            ms['mom_exercises'] = ((curr_e - prev_e) / abs(prev_e) * 100) if prev_e else None

    # Процент категорий (по количеству упражнений) для каждой тренировки:
    for ms in month_stats:
        for w in ms['workouts']:
            exercises = w.exercises.select_related('exercise_type')
            w.category_stats = calculate_category_percent(exercises)

    return render(request, 'fitnessapp/show_all_workouts.html', {
        'month_stats': month_stats,
    })


@login_required
def dashboard_view(request):
    """
    Страница аналитики:
      1) «Тренировки vs Средний вес» (месяц, неделя, год).
      2) «Вес упражнения по датам» (days, months, years).
      3) «Разбивка по категориям» (месяц, неделя, год).
      Плюс карточки count_workouts, avg_exercises, user_avg_weight.
    """
    user = request.user

    # --- БЛОК 1. Карточки: кол-во тренировок, cреднее кол-во упражнений, средний вес ---
    now = timezone.now()
    current_year = now.year
    current_month = now.month

    monthly_workouts = Workout.objects.filter(
        user=user,
        date_time__year=current_year,
        date_time__month=current_month
    )
    count_workouts = monthly_workouts.count()
    total_ex_count = sum(w.exercises.count() for w in monthly_workouts)
    avg_exercises = total_ex_count / count_workouts if count_workouts else 0

    # Средний вес пользователя за все время
    all_user_workouts = Workout.objects.filter(user=user).order_by('date_time')
    all_weights = [w.tracked_weight for w in all_user_workouts if w.tracked_weight is not None]
    user_avg_weight = sum(all_weights) / len(all_weights) if all_weights else 0

    # --- БЛОК 2. Подготовка данных для «Тренировки vs Средний вес» ---
    qs_workouts = Workout.objects.filter(user=user)
    min_date = qs_workouts.aggregate(Min('date_time'))['date_time__min']
    max_date = qs_workouts.aggregate(Max('date_time'))['date_time__max']

    # Если вообще нет тренировок, передаём пустые результаты и выходим
    if not min_date or not max_date:
        return render(request, 'fitnessapp/dashboard.html', {
            'count_workouts': 0,
            'avg_exercises': 0,
            'user_avg_weight': 0,
            'stats_all_json': json.dumps({"month":[],"week":[],"year":[]}),
            'exercise_stats_json': json.dumps({}),
            'stats_categories_json': json.dumps({"month":[],"week":[],"year":[]}),
        })

    # ------------------------
    # 2a) Группировка по Месяцам
    # ------------------------
    MONTH_NAMES = ["янв","фев","мар","апр","май","июн",
                   "июл","авг","сен","окт","ноя","дек"]

    workouts_by_month = (
        qs_workouts
        .annotate(y=ExtractYear('date_time'), m=ExtractMonth('date_time'))
        .values('y','m')
        .annotate(
            count=Count('id'),
            avg_weight=Avg('tracked_weight')
        )
        .order_by('y','m')
    )

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

    # ------------------------
    # 2b) Группировка по Неделям
    # ------------------------
    workouts_by_week = (
        qs_workouts
        .annotate(y=ExtractYear('date_time'), w=ExtractWeek('date_time'))
        .values('y','w')
        .annotate(
            count=Count('id'),
            avg_weight=Avg('tracked_weight')
        )
        .order_by('y','w')
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

    # ------------------------
    # 2c) Группировка по Годам
    # ------------------------
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

    # --- БЛОК 3. Формирование exercise_stats для «Вес упражнения по датам» (days, months, years) ---
    all_ex = Exercise.objects.filter(workout__user=user).select_related('workout','exercise_type')
    
    # Собираем названия упражнений
    ex_names = set(
        all_ex.filter(exercise_type__isnull=False)
        .values_list('exercise_type__name', flat=True)
    )

    exercise_stats = defaultdict(lambda: {"days":[],"months":[],"years":[]})

    # 3a) days: последние 6 записей на уровне каждого упражнения
    for ex_name in ex_names:
        qs_ex = all_ex.filter(exercise_type__name=ex_name).order_by('-workout__date_time')
        last_6 = qs_ex[:6]
        day_entries = []
        for obj in reversed(last_6):
            date_str = obj.workout.date_time.strftime("%Y-%m-%d")
            val = obj.exercise_weight if obj.exercise_weight is not None else 0
            day_entries.append({
                "date": date_str,
                "weight": float(val)
            })
        exercise_stats[ex_name]["days"] = day_entries

    # 3b) months: (считаем средний вес упражнения за (yyyymm))
    ex_by_month = (
        all_ex
        .annotate(yy=ExtractYear('workout__date_time'),
                  mm=ExtractMonth('workout__date_time'))
        .values('exercise_type__name','yy','mm')
        .annotate(avg_w=Avg('exercise_weight'))
        .order_by('exercise_type__name','yy','mm')
    )
    for row in ex_by_month:
        ename = row['exercise_type__name']
        avgw = row['avg_w'] if row['avg_w'] else 0
        period_str = f"{row['yy']}-{row['mm']:02d}"
        exercise_stats[ename]["months"].append({
            "period": period_str,
            "weight": float(avgw)
        })

    # 3c) years: (считаем средний вес за год)
    ex_by_year = (
        all_ex
        .annotate(yy=ExtractYear('workout__date_time'))
        .values('exercise_type__name','yy')
        .annotate(avg_w=Avg('exercise_weight'))
        .order_by('exercise_type__name','yy')
    )
    for row in ex_by_year:
        ename = row['exercise_type__name']
        avgw = row['avg_w'] if row['avg_w'] else 0
        exercise_stats[ename]["years"].append({
            "period": str(row['yy']),
            "weight": float(avgw)
        })

    exercise_stats =dict(exercise_stats)  # Превращаем defaultdict в обычный dict

    # --- БЛОК 4. Формируем stats_categories для «Разбивка по категориям» (месяц, неделя, год) ---
    # Анализируем объект Exercise: будем считать, сколько упражнений каждой категории
    # пришлось на каждый период (month/week/year).

    stats_categories = {"month": [], "week": [], "year": []}

    # 4a) Месяц
    ex_by_month_cat = (
        all_ex
        .annotate(y=ExtractYear('workout__date_time'),
                  m=ExtractMonth('workout__date_time'))
        .values('y','m','exercise_type__category')
        .annotate(cnt=Count('id'))
        .order_by('y','m','exercise_type__category')
    )
    month_map = defaultdict(lambda: defaultdict(int))
    for row in ex_by_month_cat:
        y, m = row['y'], row['m']
        cat = row['exercise_type__category'] or "Прочее"
        month_map[(y,m)][cat] += row['cnt']

    stats_month_cat = []
    for (yy, mm), cat_dict in sorted(month_map.items()):
        lbl = f"{MONTH_NAMES[mm-1]} {str(yy)[-2:]}"
        stats_month_cat.append({
            "period_label": lbl,
            "year": yy,
            "month": mm,
            "categories": dict(cat_dict)
        })
    stats_categories["month"] = stats_month_cat

    # 4b) Неделя
    ex_by_week_cat = (
        all_ex
        .annotate(y=ExtractYear('workout__date_time'),
                  w=ExtractWeek('workout__date_time'))
        .values('y','w','exercise_type__category')
        .annotate(cnt=Count('id'))
        .order_by('y','w','exercise_type__category')
    )
    week_map = defaultdict(lambda: defaultdict(int))
    for row in ex_by_week_cat:
        y, w = row['y'], row['w']
        cat = row['exercise_type__category'] or "Прочее"
        week_map[(y,w)][cat] += row['cnt']

    stats_week_cat = []
    for (yy, ww), cat_dict in sorted(week_map.items()):
        lbl = f"{yy}-W{ww}"
        stats_week_cat.append({
            "period_label": lbl,
            "year": yy,
            "week": ww,
            "categories": dict(cat_dict)
        })
    stats_categories["week"] = stats_week_cat

    # 4c) Год
    ex_by_year_cat = (
        all_ex
        .annotate(y=ExtractYear('workout__date_time'))
        .values('y','exercise_type__category')
        .annotate(cnt=Count('id'))
        .order_by('y','exercise_type__category')
    )
    year_map = defaultdict(lambda: defaultdict(int))
    for row in ex_by_year_cat:
        y = row['y']
        cat = row['exercise_type__category'] or "Прочее"
        year_map[y][cat] += row['cnt']

    stats_year_cat = []
    for yy, cat_dict in sorted(year_map.items()):
        lbl = str(yy)
        stats_year_cat.append({
            "period_label": lbl,
            "year": yy,
            "categories": dict(cat_dict)
        })
    stats_categories["year"] = stats_year_cat

    # Преобразование в обычный JSON-словарь
    stats_categories_json = json.dumps(stats_categories, ensure_ascii=False)

    # --- Итог: передаём всё в шаблон dashboard.html ---
    return render(request, 'fitnessapp/dashboard.html', {
        # Карточки
        'count_workouts': count_workouts,
        'avg_exercises': avg_exercises,
        'user_avg_weight': round(user_avg_weight, 1),

        # График «Тренировки vs Средний вес»
        'stats_all_json': json.dumps(stats_all, ensure_ascii=False),

        # График «Вес упражнения по датам»
        'exercise_stats_json': json.dumps(exercise_stats, ensure_ascii=False),

        # График «Разбивка по категориям»
        'stats_categories_json': stats_categories_json,
    })



@login_required
def users_view(request):
    """
    Список пользователей и их статистика.
    """
    users = JarvisUser.objects.all()
    data = []
    for u in users:
        w_qs = u.workouts.all()
        total_w = w_qs.count()
        w_weights = [w.tracked_weight for w in w_qs if w.tracked_weight is not None]
        if w_weights:
            average_weight = round(sum(w_weights) / len(w_weights), 1)
        else:
            average_weight = 0

        data.append({
            'user': u,
            'username': u.username,
            'first_name': u.first_name,
            'age': u.age,
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


@login_required
def settings_view(request):
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
    """
    Страница тренировок другого пользователя:  
     1) Показать 3 карточки аналитики (текущий месяц).  
     2) График по месяцам (как на dashboard).  
     3) Список тренировок в стиле main, с пагинацией по 20.  
    """
    target_user = get_object_or_404(JarvisUser, username=username)

    # --- 1) Метрики за текущий месяц ---
    now = timezone.now()
    current_year = now.year
    current_month = now.month

    monthly_qs = Workout.objects.filter(
        user=target_user, 
        date_time__year=current_year,
        date_time__month=current_month
    )
    monthly_count_workouts = monthly_qs.count()
    monthly_ex_count = sum(w.exercises.count() for w in monthly_qs)
    if monthly_count_workouts > 0:
        monthly_avg_ex = monthly_ex_count / monthly_count_workouts
    else:
        monthly_avg_ex = 0

    # Средний вес за всё время
    w_weights = Workout.objects.filter(
        user=target_user, 
        tracked_weight__isnull=False
    )
    if w_weights.exists():
        sum_w = sum(float(x.tracked_weight) for x in w_weights)
        avg_weight = round(sum_w / w_weights.count(), 1)
    else:
        avg_weight = None

    # --- 2) Для графика по месяцам (как dashboard) ---
    MONTH_NAMES = ['янв', 'фев', 'мар', 'апр', 'май', 'июн',
                   'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']
    monthly_data = []
    for m in range(1, 13):
        w_qs = Workout.objects.filter(
            user=target_user, 
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

    # --- 3) Список всех тренировок пользователя с пагинацией (20 на страницу) ---
    all_workouts = Workout.objects.filter(user=target_user).order_by('-date_time')
    paginator = Paginator(all_workouts, 20)
    page_number = request.GET.get('page')
    workouts_page = paginator.get_page(page_number)

    # Для каждой тренировки посчитаем category_stats (как в main)
    for w in workouts_page:
        exercises = w.exercises.select_related('exercise_type')
        w.category_stats = calculate_category_percent(exercises)

    return render(request, 'fitnessapp/user_detail.html', {
        'target_user': target_user,

        # 1) Карточки аналитики
        'monthly_count_workouts': monthly_count_workouts,
        'monthly_avg_ex': monthly_avg_ex,
        'avg_weight': avg_weight,

        # 2) Данные для графика
        'current_year': current_year,
        'monthly_stats_json': monthly_stats_json,

        # 3) Список с пагинацией
        'workouts_page': workouts_page,
    })



@login_required
def finish_workout_view(request, workout_id, month_count):
    """
    Показывает страницу «Поздравляем!» с формой для выставления оценки.
    По POST сохраняет rating и перенаправляет на главную страницу.
    """
    workout = get_object_or_404(Workout, id=workout_id, user=request.user)
    
    if request.method == 'POST':
        rating_str = request.POST.get('rating')
        try:
            rating_val = int(rating_str)
        except (TypeError, ValueError):
            return HttpResponseBadRequest("Некорректное значение оценки.")

        if rating_val < 1 or rating_val > 5:
            return HttpResponseBadRequest("Оценка должна быть в диапазоне 1..5.")

        # Сохраняем оценку
        workout.rating = rating_val
        workout.save()

        # По условию кнопка «Закрыть» ведёт на главную, 
        # а при сохранении оценки тоже уходим на главную.
        return redirect('main')

    # Если GET-запрос — показать поздравление и форму.
    return render(request, 'fitnessapp/workout_congrats.html', {
        'workout': workout,
        'month_count': month_count,
    })




