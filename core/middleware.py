from django.utils.deprecation import MiddlewareMixin
from .models import Organization


class CurrentOrganizationMiddleware(MiddlewareMixin):
    """
    Временно: берем первую организацию в БД
    и кладем ее в request.organization.
    Потом заменим на выбор организации пользователем.
    """

    def process_request(self, request):
        # по умолчанию — нет организации
        request.organization = None

        # если пользователь не залогинен — выходим
        if not request.user.is_authenticated:
            return

        # пока просто берем первую организацию
        org = Organization.objects.first()
        request.organization = org
