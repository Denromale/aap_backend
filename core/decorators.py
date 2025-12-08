from django.contrib.auth.decorators import user_passes_test


def is_manager(user):
    """
    Менеджер = аутентифицированный пользователь из группы 'manager'.
    """
    return (
        getattr(user, "is_authenticated", False)
        and user.groups.filter(name="manager").exists()
    )


def manager_required(view_func):
    """
    Декоратор для вьюх, доступных только менеджерам.
    """
    decorated_view_func = user_passes_test(
        is_manager,
        login_url="login",        # имя url логина
        redirect_field_name=None,
    )(view_func)
    return decorated_view_func
