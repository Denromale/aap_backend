from __future__ import annotations

from django.contrib.auth.models import Group


MANAGER_GROUP = "manager"


def is_manager(user) -> bool:
    """
    Менеджер = аутентифицированный пользователь из группы 'manager'.
    (1-в-1 как в decorators.py)
    """
    return (
        getattr(user, "is_authenticated", False)
        and user.groups.filter(name=MANAGER_GROUP).exists()
    )


def user_in_client_team(user, client) -> bool:
    """
    Проверка участия пользователя в команде клиента.
    Основано на полях Client: manager, qa_manager, auditor(1..3), assistant(1..4).
    """
    if not getattr(user, "is_authenticated", False):
        return False
    if not client:
        return False

    members = [
        getattr(client, "manager", None),
        getattr(client, "qa_manager", None),
        getattr(client, "auditor", None),
        getattr(client, "auditor2", None),
        getattr(client, "auditor3", None),
        getattr(client, "assistant", None),
        getattr(client, "assistant2", None),
        getattr(client, "assistant3", None),
        getattr(client, "assistant4", None),
    ]
    return user in [m for m in members if m is not None]


def can_manage_step15(user, client) -> bool:
    """
    Кто может менять команду на Step 1.5.
    По текущей логике проекта: superuser или менеджер.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return is_manager(user)


def action_allowed_for_user(action, user, client) -> bool:
    """
    Единая проверка для StepAction:
    - если у action указаны allowed_groups → пользователь должен быть в одной из групп
    - иначе: fallback на участие в команде или менеджера/супера
    """
    if not getattr(user, "is_authenticated", False):
        return False

    if getattr(user, "is_superuser", False):
        return True

    # 1) если ограничено группами — проверяем группы
    allowed_groups = getattr(action, "allowed_groups", None)
    if allowed_groups is not None:
        # ManyToMany manager
        if allowed_groups.exists():
            user_group_names = set(user.groups.values_list("name", flat=True))
            action_group_names = set(allowed_groups.values_list("name", flat=True))
            return bool(user_group_names & action_group_names)

    # 2) иначе — допуск по команде или менеджеру
    return is_manager(user) or user_in_client_team(user, client)
