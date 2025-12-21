from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from core.forms import Step15TeamForm
from core.models import ProcedureFile


from core.models import AuditStep, AuditSubStep, StepAction
from core.utils import require_active_client
from core.permissions import (
    is_manager,
    can_manage_step15,
    action_allowed_for_user,
)
from core.services.documents import _fill_docx_bytes, _step15_save_generated


@login_required
def audit_step_view(request, step_order: int):
    client, redirect_resp = require_active_client(request)
    if redirect_resp:
        return redirect_resp

    step = get_object_or_404(AuditStep, order=step_order, is_active=True)
    substeps = AuditSubStep.objects.filter(step=step, is_active=True).order_by("order")

    # --- Step 1.5 (substep order=5 внутри Step 1) ---
    step15_substep = None
    if step.order == 1:
        step15_substep = substeps.filter(order=5).first()

    team_form = None

    # ===== POST Step 1.5: сохранить команду / сформировать документы =====
    if request.method == "POST" and request.POST.get("form_name") == "step15_team":
        if not step15_substep:
            return HttpResponseForbidden("Step 1.5 не налаштований.")
        if not can_manage_step15(request.user, client):
            return HttpResponseForbidden("Немає прав формувати команду на кроці 1.5.")

        team_form = Step15TeamForm(request.POST, client=client)

        if team_form.is_valid():
            client.manager = team_form.cleaned_data["manager"]
            client.qa_manager = team_form.cleaned_data["qa_manager"]
            client.auditor = team_form.cleaned_data["auditor"]
            client.auditor2 = team_form.cleaned_data["auditor2"]
            client.auditor3 = team_form.cleaned_data["auditor3"]
            client.assistant = team_form.cleaned_data["assistant"]
            client.assistant2 = team_form.cleaned_data["assistant2"]
            client.assistant3 = team_form.cleaned_data["assistant3"]
            client.assistant4 = team_form.cleaned_data["assistant4"]
            client.save()

            action = request.POST.get("action") or "save_team"

            # 1) просто сохранить
            if action == "save_team":
                messages.success(request, "Команду збережено (Step 1.5).")
                return redirect(reverse("audit_step", args=[step_order]) + f"?open={step15_substep.id}")

            # 2) розпорядження (только менеджер-группа/супер)
                        # FIX: генерим здесь, а не редиректим на POST-only view
            if action == "generate_request":
                file_bytes = _fill_docx_bytes("order.docx", client, request.user)
                filename = f"order_{client.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.docx"
                _step15_save_generated(
                    request, client=client, substep=step15_substep,
                    file_bytes=file_bytes, filename=filename, title=filename
                )
                messages.success(request, "Розпорядження сформовано та збережено.")
                return redirect(reverse("audit_step", args=[step_order]) + f"?open={step15_substep.id}")

            if action == "generate_remembrance":
                file_bytes = _fill_docx_bytes("remembrance_team.docx", client, request.user)
                filename = f"remembrance_team_{client.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.docx"
                _step15_save_generated(
                    request, client=client, substep=step15_substep,
                    file_bytes=file_bytes, filename=filename, title=filename
                )
                messages.success(request, "Памʼятку сформовано та збережено.")
                return redirect(reverse("audit_step", args=[step_order]) + f"?open={step15_substep.id}")



            # fallback
            messages.success(request, "Команду збережено (Step 1.5).")
            return redirect(reverse("audit_step", args=[step_order]) + f"?open={step15_substep.id}")

        # если форма невалидна — просто упадём ниже и отрисуем ошибки

    # если не POST Step 1.5 — показываем форму
    if step15_substep and team_form is None:
        team_form = Step15TeamForm(client=client)

    # действия уровня шага
    step_actions_qs = (
        step.actions
        .filter(enabled=True, scope=StepAction.Scope.STEP)
        .order_by("order", "id")
        .prefetch_related("allowed_groups")
    )
    step_actions = [a for a in step_actions_qs if action_allowed_for_user(a, request.user, client)]

    # действия уровня подшагов
    substep_actions_map = {}
    for s in substeps:
        qs = (
            s.actions
            .filter(enabled=True, scope=StepAction.Scope.SUBSTEP)
            .order_by("order", "id")
            .prefetch_related("allowed_groups")
        )
        substep_actions_map[s.id] = [a for a in qs if action_allowed_for_user(a, request.user, client)]

    # файлы по подшагам
    files_qs = ProcedureFile.objects.filter(client=client).order_by("-created_at")
    substep_files_map = {}
    for f in files_qs:
        key = str(f.procedure_code)
        substep_files_map.setdefault(key, []).append(f)

    context = {
        "selected_client": client,
        "step": step,
        "substeps": substeps,
        "step_actions": step_actions,
        "substep_actions_map": substep_actions_map,

        # Step 1.5 extras
        "team_form": team_form,
        "step15_substep_id": step15_substep.id if step15_substep else None,
        "can_manage_step15": can_manage_step15(request.user, client),

        # files
        "substep_files_map": substep_files_map,
    }

    return render(request, "core/audit_step.html", context)

@login_required
@require_POST
def audit_step_action_run(request, step_order: int, key: str):
    client, redirect_resp = require_active_client(request)
    if redirect_resp:
        return redirect_resp

    step = get_object_or_404(AuditStep, order=step_order, is_active=True)

    action = get_object_or_404(
        StepAction,
        step=step,
        scope=StepAction.Scope.STEP,
        key=key,
        enabled=True,
    )

    if not action_allowed_for_user(action, request.user, client):
        return HttpResponseForbidden("Немає прав виконувати цю дію.")

    messages.success(request, f"Дію виконано: {action.label}")
    return redirect("audit_step", step_order=step_order)

import urllib.parse

def _safe_zip_name(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return "documents"
    # убираем недопустимые символы Windows/Linux + кавычки
    raw = re.sub(r'[\"\'<>:/\\|?*\x00-\x1F]', "", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    raw = raw.strip(". ")  # нельзя заканчивать точкой/пробелом в Windows
    if not raw:
        return "documents"
    return raw[:120]  # чтобы не упереться в лимиты



def _safe_project_zip_name(name: str | None) -> str:
    raw = (name or "documents").strip()
    # убираем кавычки и недопустимые символы Windows/Linux
    raw = re.sub(r'[\"\'<>:/\\|?*\x00-\x1F]', "", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw or "documents"

@login_required
@require_POST
def step15_generate_independence(request):
    client, redirect_resp = require_active_client(request)
    if redirect_resp:
        return redirect_resp

    # FIX: доступ — участник команды или superuser
    if not (request.user.is_superuser or user_in_client_team(request.user, client)):
        return HttpResponseForbidden("Немає прав формувати анкету.")

    # FIX: берём именно substep 1.5
    step = get_object_or_404(AuditStep, order=1, is_active=True)
    step15_substep = AuditSubStep.objects.filter(step=step, order=5, is_active=True).first()
    if not step15_substep:
        return HttpResponseForbidden("Step 1.5 не налаштований.")

    # FIX: генерим bytes и сохраняем И в ProcedureFile (для шага), И ссылку в ClientDocument
    file_bytes = _fill_docx_bytes("team_independence.docx", client, request.user)
    filename = f"team_independence_{client.id}_{request.user.username}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.docx"

    _step15_save_generated(
        request,
        client=client,
        substep=step15_substep,
        file_bytes=file_bytes,
        filename=filename,
        title=filename,
    )

    messages.success(request, "Анкету сформовано та збережено.")
    return redirect(reverse("audit_step", args=[1]) + f"?open={step15_substep.id}")

@login_required
@require_POST
def step15_generate_order__legacy(request):
    client, redirect_resp = require_active_client(request)
    if redirect_resp:
        return redirect_resp

    # доступ: только менеджер-группа или супер
    if not (request.user.is_superuser or is_manager(request.user)):
        return HttpResponseForbidden("Немає прав формувати розпорядження.")

    step = get_object_or_404(AuditStep, order=1, is_active=True)
    step15 = AuditSubStep.objects.filter(step=step, order=5, is_active=True).first()
    open_id = step15.id if step15 else ""

    template_path = os.path.join(settings.BASE_DIR, "core", "docs", "order.docx")
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

    buf = fill_docx(template_path, context_doc)
    filename = f"order_{client.id}.docx"

    doc = ClientDocument(
        organization=request.organization,
        client=client,
        uploaded_by=request.user,
        doc_type="request",
        original_name=filename,
        custom_label="Step 1.5 / Order",
    )
    doc.file.save(filename, ContentFile(buf.getvalue()), save=True)

    messages.success(request, "Розпорядження сформовано та збережено в Базі документів.")
    return redirect(reverse("audit_step", args=[1]) + (f"?open={open_id}" if open_id else ""))

@login_required
@require_POST
def step15_generate_remembrance__legacy(request):
    client, redirect_resp = require_active_client(request)
    if redirect_resp:
        return redirect_resp

    # доступ: только менеджер-группа или супер
    if not (request.user.is_superuser or is_manager(request.user)):
        return HttpResponseForbidden("Немає прав формувати памʼятку.")

    step = get_object_or_404(AuditStep, order=1, is_active=True)
    step15 = AuditSubStep.objects.filter(step=step, order=5, is_active=True).first()
    open_id = step15.id if step15 else ""

    template_path = os.path.join(settings.BASE_DIR, "core", "docs", "remembrance_team.docx")
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

    buf = fill_docx(template_path, context_doc)
    filename = f"remembrance_team_{client.id}.docx"

    doc = ClientDocument(
        organization=request.organization,
        client=client,
        uploaded_by=request.user,
        doc_type="request",
        original_name=filename,
        custom_label="Step 1.5 / Remembrance",
    )
    doc.file.save(filename, ContentFile(buf.getvalue()), save=True)

    messages.success(request, "Памʼятку сформовано та збережено в Базі документів.")
    return redirect(reverse("audit_step", args=[1]) + (f"?open={open_id}" if open_id else ""))


