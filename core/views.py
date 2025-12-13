from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
import json
import os

from collections import defaultdict

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date 
from django.views.decorators.http import require_POST
from docx import Document

from .forms import ClientForm
from .models import Client, ClientDocument, News
from .decorators import is_manager, manager_required

from django.contrib import messages




# ---------- CONSTANTS / HELPERS ----------

TEAM_ROLE_FIELDS = (
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


def build_team_q(user) -> Q:
    """
    Q-объект для фильтрации клиентов, где пользователь входит в команду.
    """
    q = Q()
    for field in TEAM_ROLE_FIELDS:
        q |= Q(**{field: user})
    return q


def user_in_client_team(user, client) -> bool:
    """
    Проверка, состоит ли пользователь в команде конкретного клиента.
    """
    for field in TEAM_ROLE_FIELDS:
        if getattr(client, field) == user:
            return True
    return False


def get_user_clients_qs(user, organization, *, completed: bool | None = None):
    """
    Базовий queryset клієнтів, доступних користувачу в рамках організації.
    - суперюзер і менеджер бачать всіх клієнтів організації
    - звичайний користувач бачить тільки проєкти, де він у команді
    completed:
        None  -> всі
        False -> тільки активні
        True  -> тільки завершені
    """
    base = Client.objects.filter(organization=organization)

    if completed is True:
        base = base.filter(is_completed=True)
    elif completed is False:
        base = base.filter(is_completed=False)

    if user.is_superuser or is_manager(user):
        return base

    return base.filter(build_team_q(user)).distinct()


def get_active_client_from_session(request, clients_qs):
    """
    Возвращает клиента из active_client_id в сессии,
    если он принадлежит доступному пользователю queryset'у.
    """
    active_client_id = request.session.get("active_client_id")
    if not active_client_id:
        return None
    return clients_qs.filter(id=active_client_id).first()


# ---------- NEWS ----------


@login_required
def news_detail(request, pk):
    news = get_object_or_404(News, pk=pk, is_published=True)
    return render(request, "core/news_detail.html", {"news": news})


# ---------- DASHBOARD ----------


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


# ---------- DOCX УТИЛИТА ----------


def fill_docx(template_path: str, context: dict) -> BytesIO:
    """
    Открывает docx, подставляет значения по меткам и возвращает файл в памяти.
    """
    doc = Document(template_path)

    def replace_in_paragraph(paragraph):
        original_text = paragraph.text
        for key, value in context.items():
            if key in original_text:
                for run in paragraph.runs:
                    run.text = run.text.replace(key, value)
                if key in paragraph.text and original_text.strip() == key:
                    paragraph.text = original_text.replace(key, value)

    # --- Абзацы ---
    for p in doc.paragraphs:
        replace_in_paragraph(p)

    # --- Таблицы ---
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    replace_in_paragraph(p)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


# ---------- ACTIVE CLIENT В СЕССИИ ----------


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


# ---------- AUTH ----------


def login_view(request):
    """
    Простой логин через username/password + галочка 'Запомнить'.
    Если галочка НЕ отмечена — сессия живёт до закрытия браузера.
    Если отмечена — используется стандартный срок жизни сессии
    (SESSION_COOKIE_AGE в settings.py).
    """
    error = None

    if request.method == "POST":
        username = request.POST.get("username") or ""
        password = request.POST.get("password") or ""
        remember_me = request.POST.get("remember_me")  # 'on' если отмечено, None если нет

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)

            # если галочка НЕ стоит — сессия до закрытия браузера
            if not remember_me:
                request.session.set_expiry(0)

            return redirect("home")
        else:
            error = "Невірний логін або пароль"

    return render(request, "core/login.html", {"error": error})


def logout_view(request):
    logout(request)
    return redirect("login")


# ---------- HOME ----------


@login_required
def home(request):
    """
    Главная страница AAP с новостями.
    Пока новости общие для всех организаций.
    """
    news_list = News.objects.filter(is_published=True).order_by("-created_at")[:5]
    return render(request, "core/home.html", {"news_list": news_list})


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


# ---------- CRUD КЛИЕНТА ----------


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
            client.save()  # логика синхронизации команды уже срабатывает внутри модели/сигнала

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
def client_detail(request, pk):
    # клиент берётся только из списка доступных пользователю проектов
    clients_qs = get_user_clients_qs(request.user, request.organization)
    client = get_object_or_404(clients_qs, pk=pk)

    return render(request, "core/client_detail.html", {"client": client})





@login_required
def client_edit(request, pk):
    # находим клиента только в текущей организации
    client = get_object_or_404(Client, pk=pk, organization=request.organization)

    # ПРАВА: редактировать могут суперюзер или участники команды
    is_manager_group = request.user.groups.filter(name="Менеджер").exists()

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
        # важно: form.save() сам корректно сохраняет FileField audit_report_scan,
        # и НЕ трогает contract_scan (он не в Meta.fields)
            client = form.save(commit=False)
            client.organization = request.organization
            client.save()
            # form.save_m2m() не нужен (у тебя нет m2m), но можно оставить как привычку:
            # form.save_m2m()

            # ---- работа со сканом договора (как в create) ----
            file = request.FILES.get("contract_scan")
            if file:
                base_doc = ClientDocument.objects.create(
                    organization=request.organization,
                    client=client,
                    file=file,
                    doc_type="agreement",
                    original_name=file.name,
                    custom_label="Скан-копія договору",
                    uploaded_by=request.user,
                )

                siblings = Client.objects.filter(
                    organization=request.organization,
                    name=client.name,
                    requisites_number=client.requisites_number,
                    requisites_date=client.requisites_date,
                ).exclude(pk=client.pk)

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

            return redirect("client_detail", pk=client.pk)
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
            "is_manager": is_manager(request.user),  # у тебя уже есть is_manager()
            "can_complete": can_complete,
        },
    )


    return render(
    request,
    "core/client_form.html",
    {
        "form": form,
        "edit": True,
        "client": client,
        "is_manager": is_manager(request.user),
    },
)



@login_required
@require_POST
def client_complete(request, pk):
    client = get_object_or_404(Client, pk=pk, organization=request.organization)

    # права
    is_manager_group = request.user.groups.filter(name="Менеджер").exists()
    is_in_team = any([
        request.user == client.manager,
        request.user == client.auditor,
        request.user == client.auditor2,
        request.user == client.auditor3,
        request.user == client.assistant,
        request.user == client.assistant2,
        request.user == client.assistant3,
        request.user == client.assistant4,
        request.user == client.qa_manager,
    ])
    if not (request.user.is_superuser or is_manager_group or is_in_team):
        return HttpResponseForbidden("Немає прав завершувати цей проєкт.")

    client.is_completed = True
    client.completed_at = timezone.now()
    client.completed_by = request.user
    client.save(update_fields=["is_completed", "completed_at", "completed_by"])

    # убираем активный, если он был выбран
    if str(request.session.get("active_client_id")) == str(client.pk):
        request.session.pop("active_client_id", None)

    return redirect("projects_archive")



@login_required
def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk, organization=request.organization)

    # только менеджер или суперюзер
    is_manager = request.user.groups.filter(name="manager").exists()
    if not (is_manager or request.user.is_superuser):
        return HttpResponseForbidden("У вас немає прав видаляти клієнтів.")

    # если надо подтверждение – можно оставить GET-страницу.
    # Сейчас просто удаляем и уходим на дашборд.
    client.delete()
    return redirect("dashboard")



# ---------- ЗАПИТИ / ГЕНЕРАЦИЯ DOCX ----------


@login_required
def requests_view(request):
    """
    Страница «Запити».
    Клиент берётся из active_client_id в сессии.
    """
    user = request.user
    clients_qs = get_user_clients_qs(user, request.organization)

    active_client = get_active_client_from_session(request, clients_qs)

    if request.method == "GET":
        return render(
            request,
            "core/requests.html",
            {"selected_client": active_client},
        )

    if not active_client:
        return redirect("requests")

    doc_type = request.POST.get("doc_type")
    if doc_type not in {"remembrance_team", "team_independence", "order"}:
        return redirect("requests")

    client = active_client

    if doc_type == "remembrance_team":
        template_name = "remembrance_team.docx"
        download_name = f"remembrance_team_{client.id}.docx"
    elif doc_type == "team_independence":
        template_name = "team_independence.docx"
        download_name = f"team_independence_{client.id}.docx"
    else:
        template_name = "order.docx"
        download_name = f"order_{client.id}.docx"

    doc_type_code = "request"

    template_path = os.path.join(
        settings.BASE_DIR,
        "core",
        "docs",
        template_name,
    )

    today_str = timezone.now().strftime("%d.%m.%Y")

    context_doc = {
        "{{ CLIENT_NAME }}": client.name or "",
        "{{ REPORTING_PERIOD }}": client.reporting_period or "",
        "{{ MANAGER }}": client.manager.get_full_name() if client.manager else "",
        "{{ AUDITOR_1 }}": client.auditor.get_full_name() if client.auditor else "",
        "{{ AUDITOR_2 }}": client.auditor2.get_full_name() if client.auditor2 else "",
        "{{ AUDITOR_3 }}": client.auditor3.get_full_name() if client.auditor3 else "",
        "{{ ASSISTANT_1 }}": client.assistant.get_full_name() if client.assistant else "",
        "{{ ASSISTANT_2 }}": client.assistant2.get_full_name() if client.assistant2 else "",
        "{{ ASSISTANT_3 }}": client.assistant3.get_full_name() if client.assistant3 else "",
        "{{ ASSISTANT_4 }}": client.assistant4.get_full_name() if client.assistant4 else "",
        "{{ QA_MANAGER }}": client.qa_manager.get_full_name() if client.qa_manager else "",
        "{{ TODAY_DATE }}": today_str,
        "{{ CURRENT_USER }}": request.user.get_full_name() or request.user.username,
    }

    file_obj = fill_docx(template_path, context_doc)
    file_bytes = file_obj.getvalue()

    doc_record = ClientDocument(
        organization=request.organization,
        client=client,
        uploaded_by=request.user,
        doc_type=doc_type_code,
        original_name=download_name,
    )
    doc_record.file.save(download_name, ContentFile(file_bytes), save=True)

    documents_url = reverse("documents")
    return redirect(f"{documents_url}?client_id={client.id}")


# ---------- ДОКУМЕНТЫ ----------


@login_required
def documents_view(request):
    user = request.user

    # 1. Клиенты, доступные пользователю
    clients = get_user_clients_qs(user, request.organization).order_by("name")

    if not clients.exists():
        return render(
            request,
            "core/documents.html",
            {
                "clients": clients,
                "selected_client": None,
                "documents": [],
                "doc_type_choices": ClientDocument.DOC_TYPE_CHOICES,
                "clients_json": "[]",
            },
        )

    # список для фронта (select + js)
    clients_list = [
        {
            "id": c.id,
            "name": c.name or "",
            "reporting_period": c.reporting_period or "",
            "requisites_number": c.requisites_number or "",
            "engagement_subject": c.engagement_subject or "",
            "engagement_subject_display": c.get_engagement_subject_display()
            if c.engagement_subject
            else "",
        }
        for c in clients
    ]
    clients_json = json.dumps(clients_list, ensure_ascii=False)

    client_id = request.GET.get("client_id") or request.session.get("active_client_id")
    selected_client = clients.filter(id=client_id).first() if client_id else None

    # загрузка файла
    if request.method == "POST" and request.POST.get("action") == "upload":
        if selected_client:
            file = request.FILES.get("file")
            if file:
                ClientDocument.objects.create(
                    organization=request.organization,
                    client=selected_client,
                    file=file,
                    original_name=file.name,
                    uploaded_by=request.user,
                    doc_type=request.POST.get("doc_type") or "",
                    custom_label=request.POST.get("label") or "",
                )

        docs_url = reverse("documents")
        if selected_client:
            return redirect(f"{docs_url}?client_id={selected_client.id}")
        return redirect(docs_url)

    if selected_client:
        documents = (
            ClientDocument.objects.filter(
                organization=request.organization,
                client=selected_client,
            )
            .order_by("-created_at")
        )
    else:
        documents = []

    return render(
        request,
        "core/documents.html",
        {
            "clients": clients,
            "selected_client": selected_client,
            "documents": documents,
            "doc_type_choices": ClientDocument.DOC_TYPE_CHOICES,
            "clients_json": clients_json,
        },
    )


@login_required
def document_update_type(request, doc_id):
    """
    Обновляет тип и мітку конкретного документа из строки таблицы.
    """
    doc = get_object_or_404(
        ClientDocument,
        pk=doc_id,
        organization=request.organization,
    )

    client = doc.client

    if not request.user.is_superuser and not user_in_client_team(request.user, client):
        return redirect("documents")

    if request.method == "POST":
        doc.doc_type = request.POST.get("doc_type") or ""
        doc.custom_label = request.POST.get("custom_label") or ""
        doc.save()

    documents_url = reverse("documents")
    return redirect(f"{documents_url}?client_id={client.id}")


@login_required
def document_delete(request, pk):
    """
    Удаление документа клиента:
    - удаляет файл с диска
    - удаляет запись из базы
    """
    doc = get_object_or_404(
        ClientDocument,
        pk=pk,
        organization=request.organization,
    )
    client_id = doc.client_id

    if not request.user.is_superuser and doc.uploaded_by != request.user:
        documents_url = reverse("documents")
        return redirect(f"{documents_url}?client_id={client_id}")

    if request.method == "POST":
        if doc.file:
            doc.file.delete(save=False)
        doc.delete()

    documents_url = reverse("documents")
    return redirect(f"{documents_url}?client_id={client_id}")





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