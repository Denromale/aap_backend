from django import template

register = template.Library()

@register.filter
def get_item(value, key):
    """
    Безопасно возвращает value[key] / value.get(key).
    Если value не dict/не mapping — вернёт None (и шаблон не упадёт).
    """
    if value is None:
        return None

    # 1) dict-like (has .get)
    if hasattr(value, "get"):
        # пробуем как есть
        out = value.get(key, None)
        if out is not None:
            return out

        # часто ключи в dict хранятся как строки
        try:
            return value.get(str(key), None)
        except Exception:
            return None

    # 2) indexable (list/tuple/QuerySet etc.)
    try:
        return value[key]
    except Exception:
        # если key int, а value string — тоже сюда попадём и вернём None
        return None
