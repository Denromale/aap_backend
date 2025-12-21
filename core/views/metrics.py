from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from core.permissions import is_manager
from core.models import Client
from django.utils import timezone
from decimal import Decimal
from decimal import Decimal, ROUND_HALF_UP


@login_required
def metrics_view(request):
    # доступ только менеджерам
    if not is_manager(request.user):
        return render(
            request,
            "core/access_denied.html",
            {
                "message": "У вас немає прав для перегляду цієї сторінки."
            },
            status=403,
        )

    org = request.organization

    # --- чтение диапазона дат из GET ---
    date_from_raw = (request.GET.get("date_from") or "").strip()
    date_to_raw = (request.GET.get("date_to") or "").strip()
    date_from = parse_date(date_from_raw) if date_from_raw else None
    date_to = parse_date(date_to_raw) if date_to_raw else None

    # --- базовый queryset по організації ---
    clients_qs = Client.objects.filter(organization=org).select_related(
        "manager",
        "auditor",
        "auditor2",
        "auditor3",
        "assistant",
        "assistant2",
        "assistant3",
        "assistant4",
        "qa_manager",
    )

    # --- фільтр по діапазону дат (contract_deadline) ---
    if date_from:
        clients_qs = clients_qs.filter(contract_deadline__gte=date_from)
    if date_to:
        clients_qs = clients_qs.filter(contract_deadline__lte=date_to)

    # карточки вверху (уже по відфільтрованих проєктах)
    total_clients = clients_qs.count()
    active_projects = clients_qs.filter(status="active").count()
    overdue_projects = clients_qs.filter(
        contract_deadline__lt=timezone.now().date()
    ).count()

    # ---- АГРЕГАЦІЯ ПО КОМАНДІ ----

    def quant(x: Decimal) -> Decimal:
        return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    stats: dict[int, dict] = {}

    def get_stat(user):
        if user.id not in stats:
            stats[user.id] = {
                "user": user,
                "projects": set(),
                "poi_projects": set(),
                "contract_sum": Decimal("0"),
                "hours_sum": Decimal("0"),
                "budget_share_sum": Decimal("0"),
            }
        return stats[user.id]

    for client in clients_qs:
        total_hours = client.planned_hours or Decimal("0")
        total_budget = client.requisites_amount or Decimal("0")
        is_poi = bool(client.poi)

        def add_role(user, coeff: Decimal):
            if not user or coeff == 0:
                return

            st = get_stat(user)

            # разовый учёт проєкту для користувача
            if client.id not in st["projects"]:
                st["projects"].add(client.id)
                st["contract_sum"] += total_budget
            if is_poi:
                st["poi_projects"].add(client.id)

            # вклад по годинам і бюджету
            st["hours_sum"] += total_hours * coeff
            st["budget_share_sum"] += total_budget * coeff

        manager_coeff = Decimal("0.10")
        auditor_total_coeff = Decimal("0.47")
        assistant_total_coeff = Decimal("0.40")
        qa_coeff = Decimal("0.03")

        add_role(client.manager, manager_coeff)

        auditors = [client.auditor, client.auditor2, client.auditor3]
        auditors_used = [u for u in auditors if u is not None]
        per_auditor_coeff = (
            auditor_total_coeff / len(auditors_used) if auditors_used else Decimal("0")
        )
        for u in auditors_used:
            add_role(u, per_auditor_coeff)

        assistants = [
            client.assistant,
            client.assistant2,
            client.assistant3,
            client.assistant4,
        ]
        assistants_used = [u for u in assistants if u is not None]
        per_assistant_coeff = (
            assistant_total_coeff / len(assistants_used) if assistants_used else Decimal("0")
        )
        for u in assistants_used:
            add_role(u, per_assistant_coeff)

        add_role(client.qa_manager, qa_coeff)

    # ---- ПІДГОТОВКА ДАНИХ ДЛЯ ТАБЛИЦІ ----

    team_stats = []
    for st in stats.values():
        projects_count = len(st["projects"])
        poi_count = len(st["poi_projects"])

        team_stats.append({
            "user": st["user"],
            "projects_count": projects_count,
            "poi_count": poi_count,
            "contract_sum": quant(st["contract_sum"]),
            "hours_sum": quant(st["hours_sum"]),
            "budget_share_sum": quant(st["budget_share_sum"]),
        })

    # ---- СОРТУВАННЯ ----

    sort_param = request.GET.get("sort", "projects")
    field_map = {
        "projects": "projects_count",
        "poi": "poi_count",
        "contract": "contract_sum",
        "hours": "hours_sum",
        "budget": "budget_share_sum",
    }
    sort_field = field_map.get(sort_param, "projects_count")

    team_stats.sort(key=lambda item: item[sort_field], reverse=True)

    context = {
        "total_clients": total_clients,
        "active_projects": active_projects,
        "overdue_projects": overdue_projects,
        "team_stats": team_stats,
        "current_sort": sort_param,
        "date_from": date_from_raw,
        "date_to": date_to_raw,
        "is_manager": True,
    }
    return render(request, "core/metrics.html", context)

