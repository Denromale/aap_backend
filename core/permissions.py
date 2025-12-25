from __future__ import annotations

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
    # суперюзер всегда может
    if getattr(user, "is_superuser", False):
        return True

    # менеджер-группа всегда может
    if is_manager(user):
        return True

    # любой участник команды может выполнять действия (генерация документов и т.д.)
    return user_in_client_team(user, client)

