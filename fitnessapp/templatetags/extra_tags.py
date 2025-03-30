from django import template

register = template.Library()

@register.filter
def month_name(value):
    """
    Преобразует числовой месяц (1..12) в строку: "Январь", "Февраль" и т.д.
    Если число вне диапазона — вернёт как есть.
    """
    months = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    try:
        m = int(value)
        if 1 <= m <= 12:
            return months[m-1]
    except:
        pass
    return value

@register.filter
def get_duration(seconds):
    """
    seconds -> 'Hч Mм Sс' (пример)
    """
    if not seconds:
        return "0 сек"
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    parts = []
    if h > 0:
        parts.append(f"{h} ч")
    if m > 0:
        parts.append(f"{m} м")
    if s > 0:
        parts.append(f"{s} с")
    return " ".join(parts) if parts else "0 сек"