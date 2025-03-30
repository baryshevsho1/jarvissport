from collections import defaultdict

def calculate_category_percent(exercises):
    """
    Утилита для подсчёта процента упражнений по категориям.
    Возвращает список кортежей (category, percent).
    """
    cat_map = defaultdict(int)
    total_ex = 0
    for ex in exercises:
        if ex.exercise_type and ex.exercise_type.category:
            cat_map[ex.exercise_type.category] += 1
        else:
            cat_map['Прочее'] += 1
        total_ex += 1

    if total_ex == 0:
        return []

    result = []
    for cat, count in cat_map.items():
        prc = (count / total_ex) * 100
        result.append((cat, prc))
    return result