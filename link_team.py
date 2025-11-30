# link_team.py
from django.db import transaction
from django.contrib.auth.models import User
from core.models import Client


def norm(u: str) -> str:
    """Нормализуем username: убираем пробелы по краям."""
    if not u:
        return ""
    return str(u).strip()


def run():
    # 1. Собираем все username из *_username полей
    username_fields = [
        "manager_username",
        "auditor_username",
        "auditor2_username",
        "auditor3_username",
        "assistant_username",
        "assistant2_username",
        "assistant3_username",
        "assistant4_username",
        "qa_manager_username",
    ]

    usernames = set()

    for client in Client.objects.all():
        for field in username_fields:
            raw = getattr(client, field, "")
            u = norm(raw)
            if u:
                usernames.add(u)

    print(f"Найдено уникальных username в CSV: {len(usernames)}")

    # 2. Создаём пользователей, если их нет
    for u in sorted(usernames):
        user, created = User.objects.get_or_create(
            username=u,
            defaults={
                "first_name": u,
            },
        )
        if created:
            print(f"Создан новый User: {u}")
        else:
            print(f"User уже был: {u}")

    # 3. Привязываем User к полям manager/auditor/assistant/qa_manager
    with transaction.atomic():
        updated = 0

        for client in Client.objects.all():

            def link(field_username: str, field_fk: str):
                raw = getattr(client, field_username, "")
                u = norm(raw)
                if not u:
                    return
                try:
                    user = User.objects.get(username=u)
                except User.DoesNotExist:
                    # если пользователя нет, просто пропускаем
                    return
                # не трогаем, если уже кто-то стоит
                if getattr(client, field_fk) is None:
                    setattr(client, field_fk, user)

            link("manager_username", "manager")
            link("auditor_username", "auditor")
            link("auditor2_username", "auditor2")
            link("auditor3_username", "auditor3")
            link("assistant_username", "assistant")
            link("assistant2_username", "assistant2")
            link("assistant3_username", "assistant3")
            link("assistant4_username", "assistant4")
            link("qa_manager_username", "qa_manager")

            client.save()
            updated += 1

    print(f"Обновлено клиентов (пройдены циклом): {updated}")
    print("Привязка команды завершена.")
