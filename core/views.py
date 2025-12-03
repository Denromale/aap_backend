from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from decimal import Decimal, ROUND_HALF_UP


from io import BytesIO
from docx import Document
from django.utils import timezone
from django.http import HttpResponse
import os
from django.conf import settings

from django.urls import reverse
from django.core.files.base import ContentFile

from .models import Client, ClientDocument
from .forms import ClientForm
import json
from django.shortcuts import render
from .models import News
from core.models import News

from .models import News
from django.views.decorators.http import require_POST



@login_required
def news_detail(request, pk):
    news = get_object_or_404(News, pk=pk, is_published=True)
    return render(request, "core/news_detail.html", {"news": news})



@login_required
def dashboard(request):
    """
    Призначені проєкти:
    - Адмін бачить усіх клієнтів
    - Звичайний користувач – тільки там, де він у ролі
    + Фільтри по назві, періоду, предмету завдання та статусу
    """
    # базовый queryset с учётом прав доступу
    if request.user.is_superuser:
        base_qs = Client.objects.all()
    else:
        base_qs = (
            Client.objects.filter(
                Q(manager=request.user)
                | Q(auditor=request.user)
                | Q(auditor2=request.user)
                | Q(auditor3=request.user)
                | Q(assistant=request.user)
                | Q(assistant2=request.user)
                | Q(assistant3=request.user)
                | Q(assistant4=request.user)
                | Q(qa_manager=request.user)
            )
            .distinct()
        )

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
        .exclude(engagement_subject__exact(""))
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
    # приводим к строке, чтобы сравнивать с value радио (тоже строка)
    active_client_id_str = str(active_client_id) if active_client_id is not None else ""

    context = {
        "clients": clients,
        "reporting_period_choices": reporting_period_choices,
        "status_choices": status_choices,
        "subject_choices": subject_choices,
        "active_client_id": active_client_id_str,
    }

    return render(request, "core/dashboard.html", context)


def fill_docx(template_path: str, context: dict) -> BytesIO:
    """
    Открывает docx, подставляет значения по меткам и возвращает файл в памяти.
    Основной вариант – замена внутри runs (сохраняет форматирование).
    Доп. вариант – если весь абзац = одному placeholder'у, меняем весь текст,
    чтобы сработало даже если Word разорвал метку на несколько runs.
    """
    from docx import Document
    doc = Document(template_path)

    # --- Абзацы ---
    for p in doc.paragraphs:
        original_text = p.text

        for key, value in context.items():
            if key in original_text:
                # 1) обычная замена по runs (как было)
                for run in p.runs:
                    run.text = run.text.replace(key, value)

                # 2) fallback: если placeholder всё ещё есть в абзаце
                #    и абзац целиком состоит только из этого placeholder'а
                if key in p.text and original_text.strip() == key:
                    p.text = original_text.replace(key, value)

    # --- Таблицы ---
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    original_text = p.text

                    for key, value in context.items():
                        if key in original_text:
                            # 1) обычная замена по runs
                            for run in p.runs:
                                run.text = run.text.replace(key, value)

                            # 2) fallback для целого абзаца = placeholder
                            if key in p.text and original_text.strip() == key:
                                p.text = original_text.replace(key, value)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf



@login_required
@require_POST
def set_active_client(request):
    """
    Сохраняет выбранный проект в сессии из формы на dashboard.
    """
    client_id = request.POST.get("selected_client")  # имя radio в шаблоне
    next_url = request.POST.get("next") or reverse("dashboard")

    if client_id:
        try:
            client = Client.objects.get(pk=client_id)
        except Client.DoesNotExist:
            # если передали мусор — очищаем выбор
            request.session.pop("active_client_id", None)
        else:
            # ВАЖНО: пишем именно active_client_id
            request.session["active_client_id"] = client.id
    else:
        # если пришёл пустой value — тоже убираем
        request.session.pop("active_client_id", None)

    return redirect(next_url)



# ---------- базовые вьюхи ----------
# @login_required(login_url='login')
def login_view(request):
    """
    Простой логин через username/password.
    """
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("home")  # после логина идём на home
        else:
            error = "Невірний логін або пароль"
    else:
        error = None

    return render(request, "core/login.html", {"error": error})



@login_required
def home(request):
    """
    Главная страница AAP с новостями.
    """
    news_list = News.objects.filter(is_published=True).order_by("-created_at")[:5]

    # Жёсткий debug в консоль, чтобы точно видеть, что вьюха вызывается
    print("DEBUG home(): news_count =", news_list.count())

    return render(request, "core/home.html", {
        "news_list": news_list,
    })


@login_required
def dashboard(request):
    """
    Призначені проєкти:
    - Адмін бачить усіх клієнтів
    - Звичайний користувач – тільки там, де він у ролі
    + Фільтри по назві, періоду, предмету завдання та статусу
    """
    # базовый queryset с учётом прав доступа
    if request.user.is_superuser:
        base_qs = Client.objects.all()
    else:
        base_qs = (
            Client.objects.filter(
                Q(manager=request.user)
                | Q(auditor=request.user)
                | Q(auditor2=request.user)
                | Q(auditor3=request.user)
                | Q(assistant=request.user)
                | Q(assistant2=request.user)
                | Q(assistant3=request.user)
                | Q(assistant4=request.user)
                | Q(qa_manager=request.user)
            )
            .distinct()
        )

    # ---------- читаем фильтры из GET ----------
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

    clients = clients.order_by("-created_at")

    # ---------- значения для выпадающих фильтров ----------
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

    # ---------- активный клиент из сессии ----------
    active_client_id = request.session.get("active_client_id")
    # приводим к строке, чтобы удобно сравнивать в шаблоне с value инпута
    active_client_id_str = str(active_client_id) if active_client_id is not None else ""

    context = {
        "clients": clients,
        "reporting_period_choices": reporting_period_choices,
        "status_choices": status_choices,
        "subject_choices": subject_choices,
        "active_client_id": active_client_id_str,
    }

    return render(request, "core/dashboard.html", context)







# ---------- Команда клиента (часы/бюджет) ----------

@login_required
def client_team(request, pk):
    client = get_object_or_404(Client, pk=pk)

    # проверка доступа
    if not request.user.is_superuser:
        if not (
            client.manager == request.user
            or client.auditor == request.user
            or client.auditor2 == request.user
            or client.auditor3 == request.user
            or client.assistant == request.user
            or client.assistant2 == request.user
            or client.assistant3 == request.user
            or client.assistant4 == request.user
            or client.qa_manager == request.user
        ):
            return redirect("dashboard")

    total_hours = client.planned_hours or Decimal("0")
    total_budget = client.requisites_amount or Decimal("0")

    def quant(x: Decimal | None):
        if x is None:
            return None
        return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

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

    # Аудиторы (0.47 суммарно, делим между не-null)
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

    # Ассистенты (0.40 суммарно)
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


# ---------- Создание / просмотр / редактирование / удаление клиента ----------

@login_required
def client_create(request):
    # клиентов создаёт только админ
    if not request.user.is_superuser:
        return redirect("dashboard")

    if request.method == "POST":
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("dashboard")
    else:
        form = ClientForm()

    return render(request, "core/client_form.html", {"form": form})


@login_required
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)

    # доступ только админу или участникам команды
    if not request.user.is_superuser:
        if not (
            client.manager == request.user
            or client.auditor == request.user
            or client.auditor2 == request.user
            or client.auditor3 == request.user
            or client.assistant == request.user
            or client.assistant2 == request.user
            or client.assistant3 == request.user
            or client.assistant4 == request.user
            or client.qa_manager == request.user
        ):
            return redirect("dashboard")

    return render(
        request,
        "core/client_detail.html",
        {
            "client": client,
        },
    )



@login_required
def client_edit(request, pk):
    client = get_object_or_404(Client, pk=pk)

    # редактирование – админ или участник команды
    if not request.user.is_superuser:
        if not (
            client.manager == request.user
            or client.auditor == request.user
            or client.auditor2 == request.user
            or client.auditor3 == request.user
            or client.assistant == request.user
            or client.assistant2 == request.user
            or client.assistant3 == request.user
            or client.assistant4 == request.user
            or client.qa_manager == request.user
        ):
            return redirect("dashboard")

    if request.method == "POST":
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            return redirect("dashboard")
    else:
        form = ClientForm(instance=client)

    return render(
        request,
        "core/client_form.html",
        {
            "form": form,
            "edit": True,
            "client": client,
        },
    )


@login_required
def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk)

    # удалять может только админ
    if not request.user.is_superuser:
        return redirect("dashboard")

    if request.method == "POST":
        client.delete()
        return redirect("dashboard")

    return render(request, "core/client_confirm_delete.html", {"client": client})


# ---------- Страница «Запити» / генерация DOCX ----------

@login_required
def requests_view(request):
    """
    Страница «Запити».

    Клиент берётся из active_client_id в сессии (ставится галочкой на dashboard).
    Никаких выпадающих списков, только 3 кнопки генерации документов
    для уже выбранного проекта.
    """

    # те же клиенты, что пользователь видит на dashboard
    if request.user.is_superuser:
        clients_qs = Client.objects.all()
    else:
        clients_qs = (
            Client.objects.filter(
                Q(manager=request.user)
                | Q(auditor=request.user)
                | Q(auditor2=request.user)
                | Q(auditor3=request.user)
                | Q(assistant=request.user)
                | Q(assistant2=request.user)
                | Q(assistant3=request.user)
                | Q(assistant4=request.user)
                | Q(qa_manager=request.user)
            )
            .distinct()
        )

    # активный клиент из сессии
    active_client_id = request.session.get("active_client_id")
    selected_client = (
        clients_qs.filter(id=active_client_id).first() if active_client_id else None
    )

    # если ничего не выбрано – просто показываем шаблон с сообщением
    if request.method == "GET":
        return render(
            request,
            "core/requests.html",
            {
                "selected_client": selected_client,
            },
        )

    # ------- POST: сформировать документ для выбранного клиента -------

    if not selected_client:
        # на всякий случай: запрос пришёл без выбранного проекта
        return redirect("requests")

    doc_type = request.POST.get("doc_type")  # remembrance_team / team_independence / order
    if doc_type not in {"remembrance_team", "team_independence", "order"}:
        return redirect("requests")

    client = selected_client

    # выбор шаблона
    if doc_type == "remembrance_team":
        template_name = "remembrance_team.docx"
        download_name = f"remembrance_team_{client.id}.docx"
    elif doc_type == "team_independence":
        template_name = "team_independence.docx"
        download_name = f"team_independence_{client.id}.docx"
    else:  # "order"
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

    # генерируем DOCX
    file_obj = fill_docx(template_path, context_doc)
    file_bytes = file_obj.getvalue()

    # сохраняем в ClientDocument
    doc_record = ClientDocument(
        client=client,
        uploaded_by=request.user,
        doc_type=doc_type_code,
        original_name=download_name,
    )
    doc_record.file.save(download_name, ContentFile(file_bytes), save=True)

    # и сразу переходим в Базу документів этого клиента
    documents_url = reverse("documents")
    return redirect(f"{documents_url}?client_id={client.id}")







@login_required
def documents_view(request):
    # 1. Клиенты, доступные пользователю
    if request.user.is_superuser:
        clients = Client.objects.all().order_by("name")
    else:
        clients = (
            Client.objects.filter(
                Q(manager=request.user)
                | Q(auditor=request.user)
                | Q(auditor2=request.user)
                | Q(auditor3=request.user)
                | Q(assistant=request.user)
                | Q(assistant2=request.user)
                | Q(assistant3=request.user)
                | Q(assistant4=request.user)
                | Q(qa_manager=request.user)
            )
            .distinct()
            .order_by("name")
        )

    # если вообще нет клиентов
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

    # ---------- данные для JS (если ещё используешь) ----------
    clients_list = []
    for c in clients:
        clients_list.append(
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
        )
    clients_json = json.dumps(clients_list, ensure_ascii=False)

    # ---------- определяем выбранного клиента ----------

    # 1) пробуем взять из GET (если вдруг ?client_id=... всё ещё используется)
    client_id = request.GET.get("client_id")

    # 2) если нет — берём активного з dashboard
    if not client_id:
        client_id = request.session.get("active_client_id")

    selected_client = None
    if client_id:
        selected_client = clients.filter(id=client_id).first()

    # ---------- загрузка файла (POST) ----------
    if request.method == "POST" and request.POST.get("action") == "upload":
        # сюда придём только когда уже выбран клиент
        if selected_client:
            file = request.FILES.get("file")
            if file:
                ClientDocument.objects.create(
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
        else:
            return redirect(docs_url)

    # ---------- список документов выбранного клиента ----------
    if selected_client:
        documents = (
            ClientDocument.objects.filter(client=selected_client)
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
    doc = get_object_or_404(ClientDocument, pk=doc_id)

    # проверка доступа: пользователь должен иметь доступ к клиенту
    client = doc.client
    if not request.user.is_superuser:
        if not (
            client.manager == request.user
            or client.auditor == request.user
            or client.auditor2 == request.user
            or client.auditor3 == request.user
            or client.assistant == request.user
            or client.assistant2 == request.user
            or client.assistant3 == request.user
            or client.assistant4 == request.user
            or client.qa_manager == request.user
        ):
            return redirect("documents")

    if request.method == "POST":
        doc.doc_type = request.POST.get("doc_type") or ""
        doc.custom_label = request.POST.get("custom_label") or ""
        doc.save()

    return redirect(f"/documents/?client_id={client.id}")


@login_required
def document_delete(request, pk):
    """
    Удаление документа клиента:
    - удаляет файл с диска
    - удаляет запись из базы
    Доступ: суперюзер или тот, кто загрузил документ.
    """
    doc = get_object_or_404(ClientDocument, pk=pk)
    client_id = doc.client_id

    # Простая проверка прав
    if not request.user.is_superuser and doc.uploaded_by != request.user:
        documents_url = reverse("documents")
        return redirect(f"{documents_url}?client_id={client_id}")

    if request.method == "POST":
        # удалить физический файл
        if doc.file:
            doc.file.delete(save=False)
        # удалить запись
        doc.delete()

    documents_url = reverse("documents")
    return redirect(f"{documents_url}?client_id={client_id}")


# ---------- logout ----------

def logout_view(request):
    logout(request)
    return redirect("login")
