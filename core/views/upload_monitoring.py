from collections import defaultdict
from datetime import datetime
from django.db.models.functions import Coalesce

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.contrib.auth import get_user_model


from core.models import (
    AuditStep,
    AuditSubStep,
    Client,
    ClientSubStepStatus,
    ProcedureFile,
)
from core.permissions import is_manager
from core.views._client_qs import get_user_clients_qs

TEAM_ROLE_FIELDS = (
    "manager",
    "qa_manager",
    "auditor",
    "auditor2",
    "auditor3",
    "assistant",
    "assistant2",
    "assistant3",
    "assistant4",
)


@login_required
def upload_monitoring(request, user_id=None):
    # --- доступ ---
    if not is_manager(request.user) and not request.user.is_superuser:
        return HttpResponseForbidden("Немає доступу.")

    # --- active_only: учитываем hidden+checkbox ---
    vals = request.GET.getlist("active_only")
    active_only = ("1" in vals) or (not vals)
    completed_filter = False if active_only else None

    # --- фильтры ---
    subject = (request.GET.get("subject") or "").strip()
    manager_id = (request.GET.get("manager") or "").strip()
    date_from = (request.GET.get("date_from") or "").strip()
    date_to = (request.GET.get("date_to") or "").strip()

    # --- base_qs для наполнения фильтров ---
    base_qs = get_user_clients_qs(
        user=request.user,
        organization=request.organization,
        completed=completed_filter,
    )

    subject_codes = (
        base_qs.values_list("engagement_subject", flat=True)
        .exclude(engagement_subject__isnull=True)
        .exclude(engagement_subject__exact="")
        .distinct()
        .order_by("engagement_subject")
    )

    subject_choices = [
        {
            "value": code,
            "label": Client(engagement_subject=code).get_engagement_subject_display(),
        }
        for code in subject_codes
    ]

    manager_ids = (
        base_qs.values_list("manager_id", flat=True)
        .exclude(manager_id__isnull=True)
        .distinct()
    )

    manager_users = (
        base_qs.filter(manager_id__in=manager_ids)
        .select_related("manager")
        .values(
            "manager_id",
            "manager__first_name",
            "manager__last_name",
            "manager__username",
        )
        .distinct()
        .order_by("manager__last_name", "manager__first_name")
    )

    manager_choices = [
        {
            "value": str(m["manager_id"]),
            "label": (
                f'{m["manager__first_name"]} {m["manager__last_name"]}'.strip()
                or m["manager__username"]
            ),
        }
        for m in manager_users
    ]

    # --- clients: базовый список + применяем фильтры ---
    clients = (
        get_user_clients_qs(
            user=request.user,
            organization=request.organization,
            completed=completed_filter,
        )
        .select_related(
            "manager",
            "qa_manager",
            "auditor",
            "auditor2",
            "auditor3",
            "assistant",
            "assistant2",
            "assistant3",
            "assistant4",
        )
        .order_by("is_completed", "name", "id")
    )
    # "Кінцевий строк" = contract_deadline если есть, иначе deadline
    clients = clients.annotate(end_date=Coalesce("contract_deadline", "deadline"))
        # --- фильтр по пользователю (персональный мониторинг) ---
       # --- фильтр по пользователю (персональный мониторинг) ---
    selected_user = None
    if user_id:
        User = get_user_model()
        selected_user = User.objects.filter(pk=user_id).first()

        user_filter = Q()
        for field in TEAM_ROLE_FIELDS:
            user_filter |= Q(**{f"{field}_id": user_id})
        clients = clients.filter(user_filter)



    # фильтр диапазона по конечной дате
    d1 = d2 = None

    if date_from:
        try:
            d1 = datetime.strptime(date_from, "%Y-%m-%d").date()
        except ValueError:
            d1 = None

    if date_to:
        try:
            d2 = datetime.strptime(date_to, "%Y-%m-%d").date()
        except ValueError:
            d2 = None

    if d1 and d2:
        # на случай если пользователь перепутал местами
        if d1 > d2:
            d1, d2 = d2, d1
        clients = clients.filter(end_date__range=(d1, d2))
    elif d1:
        clients = clients.filter(end_date__gte=d1)
    elif d2:
        clients = clients.filter(end_date__lte=d2)


    if subject:
        clients = clients.filter(engagement_subject=subject)

    if manager_id:
        clients = clients.filter(manager_id=manager_id)




    # --- шаги и подшаги ---
    steps = AuditStep.objects.filter(is_active=True).order_by("order")

    substeps = (
        AuditSubStep.objects.filter(step__in=steps, is_active=True)
        .select_related("step")
        .order_by("step__order", "order")
    )

    substeps_by_step = defaultdict(list)
    for s in substeps:
        substeps_by_step[s.step_id].append(s)

    substep_ids_str = [str(s.id) for s in substeps]
    substep_ids_int = [s.id for s in substeps]

    # --- статусы COMPLETED ---
    completed_statuses = (
        ClientSubStepStatus.objects.filter(
            client__in=clients,
            substep_id__in=substep_ids_int,
            status=ClientSubStepStatus.Status.COMPLETED,
        )
        .values("client_id", "substep_id")
    )

    completed_map = defaultdict(set)
    for st in completed_statuses:
        completed_map[st["client_id"]].add(st["substep_id"])

    # --- файлы (progress) ---
    files = (
        ProcedureFile.objects.filter(
            client__in=clients,
            procedure_code__in=substep_ids_str,
        )
        .values("client_id", "procedure_code")
        .distinct()
    )

    progress_map = defaultdict(set)
    for f in files:
        try:
            progress_map[f["client_id"]].add(int(f["procedure_code"]))
        except ValueError:
            continue

    # --- сбор строк таблицы ---
    rows = []
    for client in clients:
        team_users = []
        for field in TEAM_ROLE_FIELDS:
            u = getattr(client, field, None)
            if u and u not in team_users:
                team_users.append(u)

        substep_status_map = {}
        c_done = completed_map.get(client.id, set())
        c_prog = progress_map.get(client.id, set())

        for s in substeps:
            if s.id in c_done:
                substep_status_map[s.id] = "done"
            elif s.id in c_prog:
                substep_status_map[s.id] = "progress"
            else:
                substep_status_map[s.id] = "idle"

        rows.append(
            {
                "client": client,
                "client_name": client.name,
                "engagement_subject": (
                    client.get_engagement_subject_display()
                    if client.engagement_subject
                    else ""
                ),
                "contract_deadline": client.contract_deadline or client.deadline,
                "manager": client.manager,
                "team": {"count": len(team_users), "users": team_users},
                "substep_status_map": substep_status_map,
            }
        )

    context = {
        "active_only": active_only,
        "steps": steps,
        "substeps_by_step": dict(substeps_by_step),
        "rows": rows,
        "context_filters": {
            "subject": subject,
            "manager": manager_id,
            "date_from": date_from,
            "date_to": date_to,
        },
        "subject_choices": subject_choices,
        "manager_choices": manager_choices,
        "selected_user_id": user_id,
        "selected_user": selected_user,


    }

    return render(request, "core/upload_monitoring.html", context)
