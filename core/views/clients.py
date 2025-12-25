from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from core.models import News  # если уже импортировано — не дублируй
from core.views._client_qs import get_user_clients_qs
from decimal import Decimal, ROUND_HALF_UP
from django.http import HttpResponseForbidden
from core.models import ClientDocument


from core.models import Client
from core.forms import ClientForm
from core.utils import require_active_client
from core.permissions import is_manager

@login_required
def dashboard(request):
    """
    Призначені проєкти:
    - Суперадмін і користувач у групі manager бачать усіх клієнтів своєї організації
    - Звичайний користувач – тільки там, де він у ролі
    + Фільтри по назві, періоду, предмету завдання та статусу
    """
    user = request.user
    base_qs = get_user_clients_qs(user, request.organization, completed=False)


    # ---------- фильтры из GET ----------
    q = (request.GET.get("q") or "").strip()
    reporting_period = (request.GET.get("reporting_period") or "").strip()
    status = (request.GET.get("status") or "").strip()
    subject = (request.GET.get("subject") or "").strip()

    clients = base_qs
    clients = clients.filter(is_completed=False)

    if q:
        clients = clients.filter(name__icontains=q)

    if reporting_period:
        clients = clients.filter(reporting_period=reporting_period)

    if status:
        clients = clients.filter(status=status)

    if subject:
        clients = clients.filter(engagement_subject=subject)

    clients = clients.order_by("-created_at")

    # ---------- значения для селектов ----------
    reporting_period_choices = (
        base_qs.values_list("reporting_period", flat=True)
        .distinct()
        .order_by("reporting_period")
    )

    status_choices = (
        base_qs.values_list("status", flat=True)
        .exclude(status__isnull=True)
        .exclude(status__exact="")
        .distinct()
        .order_by("status")
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

    # ---------- активный проект из сессии ----------
    active_client_id = request.session.get("active_client_id")
    active_client_id_str = str(active_client_id) if active_client_id is not None else ""

    context = {
        "clients": clients,
        "reporting_period_choices": reporting_period_choices,
        "status_choices": status_choices,
        "subject_choices": subject_choices,
        "active_client_id": active_client_id_str,
        "is_manager": is_manager(user),
    }

    return render(request, "core/dashboard.html", context)

def news_detail(request, pk):
    news_item = get_object_or_404(News, pk=pk, is_published=True)
    return render(request, "core/news_detail.html", {"news_item": news_item})

@login_required
def client_create(request):
    # клиентов создаёт только админ
    if not request.user.is_superuser:
        return redirect("dashboard")

    if request.method == "POST":
        form = ClientForm(request.POST, request.FILES)
        if form.is_valid():
            client = form.save(commit=False)
            client.organization = request.organization

            # SERVER IGNORE (CREATE):
            # На этапе "Додати клієнта" разрешаем только manager + qa_manager.
            # Всё остальное (аудиторы/ассистенты) обнуляем даже если пришло в POST.
            for fname in (
                "auditor", "auditor2", "auditor3",
                "assistant", "assistant2", "assistant3", "assistant4",
            ):
                if hasattr(client, fname):
                    setattr(client, fname, None)

            client.save()  # логика синхронизации команды (если есть) сработает уже на чистых полях

            # --- ищем "соседние" проекты с тем же договором ---
            siblings = Client.objects.filter(
                organization=request.organization,
                name=client.name,
                requisites_number=client.requisites_number,
                requisites_date=client.requisites_date,
            ).exclude(pk=client.pk)

            # --- пробуем взять файл из формы ---
            file = request.FILES.get("contract_scan")

            if file:
                # 1) есть новый файл → создаём документ для текущего клиента
                base_doc = ClientDocument.objects.create(
                    organization=request.organization,
                    client=client,
                    file=file,
                    doc_type="agreement",
                    original_name=file.name,
                    custom_label="Скан-копія договору",
                    uploaded_by=request.user,
                )

                # 2) размножаем этот договор на все проекты с тем же договором
                for other in siblings:
                    ClientDocument.objects.create(
                        organization=request.organization,
                        client=other,
                        file=base_doc.file,
                        doc_type=base_doc.doc_type,
                        original_name=base_doc.original_name,
                        custom_label=base_doc.custom_label,
                        uploaded_by=request.user,
                    )

            else:
                # файла НЕ загрузили → пробуем подтянуть ДОГОВОРЫ из уже существующих проектов
                existing_docs = ClientDocument.objects.filter(
                    organization=request.organization,
                    client__in=siblings,
                    doc_type="agreement",
                ).distinct()

                for doc in existing_docs:
                    ClientDocument.objects.create(
                        organization=request.organization,
                        client=client,
                        file=doc.file,
                        doc_type=doc.doc_type,
                        original_name=doc.original_name,
                        custom_label=doc.custom_label,
                        uploaded_by=doc.uploaded_by or request.user,
                    )

            return redirect("dashboard")
        else:
            print("\n=== FORM ERRORS (client_create) ===")
            print(form.errors.as_json())
            print("=== END FORM ERRORS ===\n")
    else:
        form = ClientForm()

    return render(request, "core/client_form.html", {"form": form})

@login_required
def client_edit(request, pk):
    # находим клиента только в текущей организации
    client = get_object_or_404(Client, pk=pk, organization=request.organization)

    # ПРАВА: редактировать могут суперюзер или участники команды
    is_manager_group = is_manager(request.user)

    is_in_team = any(
        [
            request.user == client.manager,
            request.user == client.auditor,
            request.user == client.auditor2,
            request.user == client.auditor3,
            request.user == client.assistant,
            request.user == client.assistant2,
            request.user == client.assistant3,
            request.user == client.assistant4,
            request.user == client.qa_manager,
        ]
    )

    if not (request.user.is_superuser or is_manager_group or is_in_team):
        return HttpResponseForbidden("У вас немає прав редагувати цього клієнта.")

    if request.method == "POST":
        form = ClientForm(request.POST, request.FILES, instance=client)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.organization = request.organization

            # SERVER IGNORE (EDIT):
            # Через client_edit мы НЕ меняем аудиторов/ассистентов.
            # Сохраняем текущие значения из БД, даже если кто-то подложил POST.
            locked_team_fields = (
                "auditor", "auditor2", "auditor3",
                "assistant", "assistant2", "assistant3", "assistant4",
            )
            for fname in locked_team_fields:
                if hasattr(updated, fname):
                    setattr(updated, fname, getattr(client, fname))

            updated.save()

            # ---- работа со сканом договора (как в create) ----
            file = request.FILES.get("contract_scan")
            if file:
                base_doc = ClientDocument.objects.create(
                    organization=request.organization,
                    client=updated,
                    file=file,
                    doc_type="agreement",
                    original_name=file.name,
                    custom_label="Скан-копія договору",
                    uploaded_by=request.user,
                )

                siblings = Client.objects.filter(
                    organization=request.organization,
                    name=updated.name,
                    requisites_number=updated.requisites_number,
                    requisites_date=updated.requisites_date,
                ).exclude(pk=updated.pk)

                for other in siblings:
                    ClientDocument.objects.create(
                        organization=request.organization,
                        client=other,
                        file=base_doc.file,
                        doc_type=base_doc.doc_type,
                        original_name=base_doc.original_name,
                        custom_label=base_doc.custom_label,
                        uploaded_by=request.user,
                    )

            return redirect("client_detail", pk=updated.pk)
    else:
        form = ClientForm(instance=client)

    can_complete = bool(client.audit_report_scan) and bool(client.cw_controls_done)

    return render(
        request,
        "core/client_form.html",
        {
            "form": form,
            "edit": True,
            "client": client,
            "is_manager": is_manager(request.user),
            "can_complete": can_complete,
        },
    )

@login_required
def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk, organization=request.organization)

    # только менеджер или суперюзер
    is_manager_flag = is_manager(request.user)
    if not (is_manager_flag or request.user.is_superuser):
        return HttpResponseForbidden("У вас немає прав видаляти клієнтів.")

    # если надо подтверждение – можно оставить GET-страницу.
    # Сейчас просто удаляем и уходим на дашборд.
    client.delete()
    return redirect("dashboard")

@login_required
def client_detail(request, pk):
    # клиент берётся только из списка доступных пользователю проектов
    clients_qs = get_user_clients_qs(request.user, request.organization)
    client = get_object_or_404(clients_qs, pk=pk)

    return render(request, "core/client_detail.html", {"client": client})

# ---------- TEAM / БЮДЖЕТ ----------


@login_required
def client_team(request, pk):
    # клиент берётся только из списка доступных пользователю проектов
    clients_qs = get_user_clients_qs(request.user, request.organization)
    client = get_object_or_404(clients_qs, pk=pk)

    total_hours = client.planned_hours or Decimal("0")
    total_budget = client.requisites_amount or Decimal("0")

    def quant(x: Decimal | None):
        if x is None:
            return None
        return x.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    rows = []

    # Менеджер (0.10)
    manager_coeff = Decimal("0.10")
    rows.append(
        {
            "label": "Менеджер (Партнер)",
            "user": client.manager,
            "hours": quant(total_hours * manager_coeff) if total_hours else None,
            "budget": quant(total_budget * manager_coeff) if total_budget else None,
        }
    )

    # Аудитори (0.47)
    auditors = [
        ("Аудитор 1", client.auditor),
        ("Аудитор 2", client.auditor2),
        ("Аудитор 3", client.auditor3),
    ]
    auditors_used = [a for a in auditors if a[1] is not None]
    auditor_total_coeff = Decimal("0.47")
    per_auditor_coeff = (
        auditor_total_coeff / len(auditors_used) if auditors_used else Decimal("0")
    )

    for label, user in auditors:
        if user:
            coeff = per_auditor_coeff
            hours = quant(total_hours * coeff) if total_hours else None
            budget = quant(total_budget * coeff) if total_budget else None
        else:
            hours = None
            budget = None
        rows.append(
            {
                "label": label,
                "user": user,
                "hours": hours,
                "budget": budget,
            }
        )

    # Асистенти (0.40)
    assistants = [
        ("Асистент 1", client.assistant),
        ("Асистент 2", client.assistant2),
        ("Асистент 3", client.assistant3),
        ("Асистент 4", client.assistant4),
    ]
    assistants_used = [a for a in assistants if a[1] is not None]
    assistant_total_coeff = Decimal("0.40")
    per_assistant_coeff = (
        assistant_total_coeff / len(assistants_used) if assistants_used else Decimal("0")
    )

    for label, user in assistants:
        if user:
            coeff = per_assistant_coeff
            hours = quant(total_hours * coeff) if total_hours else None
            budget = quant(total_budget * coeff) if total_budget else None
        else:
            hours = None
            budget = None
        rows.append(
            {
                "label": label,
                "user": user,
                "hours": hours,
                "budget": budget,
            }
        )

    # Менеджер КК (0.03)
    qa_coeff = Decimal("0.03")
    rows.append(
        {
            "label": "Менеджер КК",
            "user": client.qa_manager,
            "hours": quant(total_hours * qa_coeff) if total_hours else None,
            "budget": quant(total_budget * qa_coeff) if total_budget else None,
        }
    )

    context = {
        "client": client,
        "rows": rows,
        "total_hours": total_hours,
        "total_budget": total_budget,
    }
    return render(request, "core/client_team.html", context)

@login_required
@require_POST
def client_complete(request, pk):
    client = get_object_or_404(Client, pk=pk, organization=request.organization)

    # только менеджеры/супер
    if not (request.user.is_superuser or is_manager(request.user)):
        return HttpResponseForbidden("Доступ лише для менеджерів.")

    # проверка условий завершения
    if not client.audit_report_scan or not client.cw_controls_done:
        messages.warning(
            request,
            "Щоб завершити проєкт, потрібно завантажити «Скан-копія аудиторського звіту» "
            "та відмітити «Контрольні процедури в CW виконані»."
        )
        return redirect("client_edit", pk=client.pk)

    # если уже завершён
    if client.is_completed:
        messages.info(request, "Проєкт уже завершений.")
        return redirect("projects_archive")

    client.is_completed = True
    client.completed_at = timezone.now()
    client.completed_by = request.user
    client.save(update_fields=["is_completed", "completed_at", "completed_by"])

    messages.success(request, "Проєкт завершено та перенесено в Архів.")
    return redirect("projects_archive")

@login_required
def projects_archive(request):
    user = request.user

    if not (user.is_superuser or is_manager(user)):
        return HttpResponseForbidden("Доступ лише для менеджерів.")

    base_qs = get_user_clients_qs(user, request.organization, completed=True)


    # ---------- фильтры из GET ----------
    q = (request.GET.get("q") or "").strip()
    reporting_period = (request.GET.get("reporting_period") or "").strip()
    status = (request.GET.get("status") or "").strip()
    subject = (request.GET.get("subject") or "").strip()

    clients = base_qs

    if q:
        clients = clients.filter(name__icontains=q)

    if reporting_period:
        clients = clients.filter(reporting_period=reporting_period)

    if status:
        clients = clients.filter(status=status)

    if subject:
        clients = clients.filter(engagement_subject=subject)

    clients = clients.order_by("-completed_at", "-updated_at")

    # ---------- значения для селектов ----------
    reporting_period_choices = (
        base_qs.values_list("reporting_period", flat=True)
        .exclude(reporting_period__isnull=True)
        .exclude(reporting_period__exact="")
        .distinct()
        .order_by("reporting_period")
    )

    status_choices = (
        base_qs.values_list("status", flat=True)
        .exclude(status__isnull=True)
        .exclude(status__exact="")
        .distinct()
        .order_by("status")
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

    active_client_id = request.session.get("active_client_id")
    active_client_id_str = str(active_client_id) if active_client_id is not None else ""

    return render(
        request,
        "core/projects_archive.html",
        {
            "clients": clients,
            "reporting_period_choices": reporting_period_choices,
            "status_choices": status_choices,
            "subject_choices": subject_choices,
            "active_client_id": active_client_id_str,
            "is_manager": is_manager(user),
        },
    )

@login_required
@require_POST
def set_active_client(request):
    """
    Сохраняет выбранный проект в сессии из формы на dashboard.
    """
    client_id = request.POST.get("selected_client")
    next_url = request.POST.get("next") or reverse("dashboard")

    if client_id:
        try:
            client = Client.objects.get(
                pk=client_id,
                organization=request.organization,
            )
        except Client.DoesNotExist:
            request.session.pop("active_client_id", None)
        else:
            request.session["active_client_id"] = client.id
    else:
        request.session.pop("active_client_id", None)

    return redirect(next_url)


@login_required
def client_step_1(request):
    # legacy URL: раньше вел на Step 1
    return redirect(reverse("audit_step", args=[1]))


@login_required
def client_step_2(request):
    # legacy URL: раньше вел на Step 2
    return redirect(reverse("audit_step", args=[2]))