# ===== Python stdlib =====
import io
import os
import re
import json
import zipfile
import zlib
from io import BytesIO
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
import urllib.parse
from urllib.parse import urlparse, parse_qs

# ===== Django =====
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction, connection
from django.db.models import Q
from django.http import (HttpResponse, JsonResponse, FileResponse, HttpResponseForbidden, Http404,)
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.text import get_valid_filename
from django.views.decorators.http import require_POST

# ===== Third-party =====
from docx import Document

# ===== App imports =====
from .models import (Client, ClientDocument, News, AuditStep, AuditSubStep, StepAction, ProcedureFile,)
from .forms import ClientForm, Step15TeamForm
from .decorators import manager_required
from .permissions import is_manager, can_manage_step15, user_in_client_team, action_allowed_for_user
from .utils import require_active_client
from core.services.documents import fill_docx, _fill_docx_bytes, _step15_save_generated

from core.views import *  # noqa




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







# ---------- ACTIVE CLIENT В СЕССИИ ----------









# ---------- CRUD КЛИЕНТА ----------


















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













# ===== Step 1.5: generate документов из кнопок =====

def _step15_get_substep_or_403(request, substep_id: str):
    """
    Возвращает AuditSubStep для Step 1.5 (step=1, substep order=5) или 403/ошибку.
    """
    if not substep_id:
        raise Http404("substep_id is required")

    substep = get_object_or_404(AuditSubStep, pk=substep_id)

    # жестко фиксируем: это именно Step 1.5
    if not (substep.step.order == 1 and substep.order == 5):
        raise Http404("This action is only for Step 1.5")

    return substep





















@login_required
def client_step_1(request):
    return redirect("audit_step", step_order=1)

@login_required
def client_step_2(request):
    return redirect("audit_step", step_order=2)




# =================== AUDIT STEP SYSTEM (NEW UNIVERSAL PAGE) ===================






