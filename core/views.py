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


# ---------- helper для работы с DOCX ----------

def fill_docx(template_path: str, context: dict) -> BytesIO:
    """
    Открывает docx, подставляет значения по меткам и возвращает файл в памяти.
    """
    doc = Document(template_path)

    # абзацы
    for p in doc.paragraphs:
        for key, value in context.items():
            if key in p.text:
                for run in p.runs:
                    run.text = run.text.replace(key, value)

    # таблицы
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    for key, value in context.items():
                        if key in p.text:
                            for run in p.runs:
                                run.text = run.text.replace(key, value)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


# ---------- базовые вьюхи ----------

def home(request):
    """
    Головна сторінка AAP.
    Доступна тільки авторизованим користувачам.
    """
    return render(request, "core/home.html")


def login_view(request):
    if request.user.is_authenticated:
        # уже вошёл – сразу на главную
        return redirect("home")

    error = None

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # если был параметр next – идём туда, иначе на home
            next_url = request.GET.get("next")
            if next_url:
                return redirect(next_url)
            return redirect("home")
        else:
            error = "Неверный логин или пароль"

    return render(request, "core/login.html", {"error": error})


@login_required
def dashboard(request):
    """
    Админ видит всех клиентов.
    Обычный пользователь – только клиентов, где он есть в какой-то роли.
    """
    if request.user.is_superuser:
        clients = Client.objects.all().order_by("-created_at")
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
            .order_by("-created_at")
        )

    return render(request, "core/dashboard.html", {"clients": clients})


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

    form = ClientForm(instance=client)
    # делаем форму read-only
    for field in form.fields.values():
        field.disabled = True

    return render(
        request,
        "core/client_form.html",
        {
            "form": form,
            "client": client,
            "read_only": True,
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
    Сторінка «Запити» – формування Word-документів для обраного клієнта.
    Одновременно сохраняем созданный документ в базу (ClientDocument),
    чтобы он появился в «Базі документів».
    """
    # ті ж клієнти, що користувач бачить у dashboard
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

    # данные для каскадных селектів (назва / період / договір / предмет)
    clients_for_js = list(
        clients.values(
            "id",
            "name",
            "reporting_period",
            "requisites_number",
            "engagement_subject",
        )
    )
    clients_json = json.dumps(clients_for_js, ensure_ascii=False)

    if request.method == "POST":
        client_id = request.POST.get("client_id")
        doc_type = request.POST.get("doc_type")

        if not client_id or not doc_type:
            return redirect("requests")

        client = get_object_or_404(Client, pk=client_id)

        # выбираем шаблон И ИМЯ ФАЙЛА
        if doc_type == "remembrance_team":
            template_name = "remembrance_team.docx"
            download_name = f"remembrance_team_{client.id}.docx"
            doc_type_code = "request"   # або свій код
        elif doc_type == "team_independence":
            template_name = "team_independence.docx"
            download_name = f"team_independence_{client.id}.docx"
            doc_type_code = "request"
        elif doc_type == "order":
            template_name = "order.docx"
            download_name = f"order_{client.id}.docx"
            doc_type_code = "request"
        else:
            return redirect("requests")

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

        # 1) генерируем DOCX в памяти
        file_obj = fill_docx(template_path, context_doc)
        file_bytes = file_obj.getvalue()

        # 2) СОХРАНЯЕМ в ClientDocument (чтобы появился в «Базі документів»)
        doc_record = ClientDocument(
            client=client,
            uploaded_by=request.user,
            doc_type=doc_type_code,
            original_name=download_name,
        )
        # сохраняем файл в FileField
        doc_record.file.save(download_name, ContentFile(file_bytes), save=True)

        # 3) редиректим в «База документів» на этого клиента
        documents_url = reverse("documents")
        return redirect(f"{documents_url}?client_id={client.id}")

    # GET-запрос – просто показываем страницу
    return render(
        request,
        "core/requests.html",
        {
            "clients": clients,
            "clients_json": clients_json,
        },
    )


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

    # ---------- данные для JS (зависимые списки) ----------
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
    client_id = request.GET.get("client_id")
    selected_client = None
    if client_id:
        selected_client = clients.filter(id=client_id).first()

    # ---------- загрузка файла (POST) ----------
    if request.method == "POST" and request.POST.get("action") == "upload":
        # сюда придём только когда уже выбран клиент,
        # форма отправляется с ?client_id=...
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
    return redirect("home")
