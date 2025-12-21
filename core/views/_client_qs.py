from __future__ import annotations

from django.db.models import Q

from core.models import Client

TEAM_ROLE_FIELDS = [
    "manager",
    "qa_manager",
    "auditor",
    "auditor2",
    "auditor3",
    "assistant",
    "assistant2",
    "assistant3",
    "assistant4",
]


def build_team_q(user) -> Q:
    q = Q()
    for f in TEAM_ROLE_FIELDS:
        q |= Q(**{f: user})
    return q


def get_user_clients_qs(user, organization=None, completed: bool | None = None):
    """
    Возвращает queryset клиентов, доступных пользователю.
    Логика как раньше: суперюзер видит всё, иначе только клиентов где он в команде.
    Если передан organization — фильтруем по organization.
    Если completed задан — фильтруем по is_completed.
    """
    qs = Client.objects.all()

    if organization is not None:
        qs = qs.filter(organization=organization)

    if not user.is_superuser:
        qs = qs.filter(build_team_q(user))

    if completed is not None:
        qs = qs.filter(is_completed=completed)

    return qs
