from django.contrib.auth.decorators import user_passes_test
from .permissions import is_manager


def manager_required(view_func):
    """
    Декоратор для вьюх, доступных только менеджерам.
    """
    return user_passes_test(
        is_manager,
        login_url="login",
        redirect_field_name=None,
    )(view_func)
