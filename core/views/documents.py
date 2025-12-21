from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, FileResponse, Http404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from core.views._client_qs import get_user_clients_qs

from django.http import HttpResponseForbidden
from core.services.file_cleanup import delete_file_if_unused

from core.models import ClientDocument, ProcedureFile
from core.utils import require_active_client

import json

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

    # БЛОКИРУЕМ загрузку из "Базы документов"
    if request.method == "POST" and request.POST.get("action") == "upload":
        return HttpResponseForbidden(
            "Завантаження документів з 'Бази документів' тимчасово вимкнено. "
            "Будь ласка, додавайте документи через відповідні кроки аудиту."
        )

    # список документов
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


@require_POST
@login_required
def document_delete(request, pk):
    client, redirect_resp = require_active_client(request)
    if redirect_resp:
        return redirect_resp

    doc = get_object_or_404(ClientDocument, pk=pk, client=client)
    file_name = doc.file.name

    doc.delete()

    delete_file_if_unused(file_name, exclude_doc_id=pk)

    return redirect("documents")


@login_required
def document_download(request, doc_id: int):
    doc = get_object_or_404(
        ClientDocument,
        pk=doc_id,
        organization=request.organization,
    )

    client = doc.client

    # доступ: суперюзер/менеджер или участник команды
    if not (request.user.is_superuser or is_manager(request.user) or user_in_client_team(request.user, client)):
        return HttpResponseForbidden("Немає прав на завантаження цього документа.")

    if not doc.file:
        raise Http404("Файл відсутній.")

    # безопасное имя файла
    filename = doc.original_name or f"document_{doc.id}"
    filename = filename.strip() or f"document_{doc.id}"
    filename = get_valid_filename(filename)

    try:
        f = doc.file.open("rb")
    except Exception:
        # если файл реально отсутствует в текущем storage (как у тебя на локалке)
        raise Http404("Файл не знайдено у сховищі.")

    return FileResponse(f, as_attachment=True, filename=filename)

@require_POST
@login_required
def documents_download_zip(request):
    documents_url = reverse("documents")

    client_id = request.POST.get("client_id") or request.session.get("active_client_id")
    if not client_id:
        messages.error(request, "Не обрано проєкт для завантаження ZIP.")
        return redirect(documents_url)

    ids_raw = (request.POST.get("doc_ids") or "").strip()
    doc_ids = [int(x) for x in ids_raw.split(",") if x.strip().isdigit()]
    if not doc_ids:
        messages.error(request, "Оберіть документи для завантаження.")
        return redirect(f"{documents_url}?client_id={client_id}")

    qs = (
        ClientDocument.objects.filter(
            organization=request.organization,
            client_id=client_id,
            id__in=doc_ids,
        )
        .select_related("client")
    )

    first = qs.first()
    if not first:
        messages.error(request, "Обрані документи не знайдено.")
        return redirect(f"{documents_url}?client_id={client_id}")

    client = first.client
    zip_base = _safe_project_zip_name(client.name)  # эта функция должна быть у тебя
    zip_name = f"{zip_base}.zip"

    buf = io.BytesIO()
    added = 0

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for d in qs:
            if not d.file or not d.file.name:
                continue

            inner_name = (d.original_name or f"doc_{d.id}").strip() or f"doc_{d.id}"
            inner_name = re.sub(r"[<>:/\\|?*\x00-\x1F]", "_", inner_name)

            try:
                # ✅ открываем через storage (важно для R2/S3)
                with d.file.storage.open(d.file.name, "rb") as f:
                    z.writestr(inner_name, f.read())
                added += 1
            except Exception as e:
                print(f"[ZIP] Cannot add file {d.file.name}: {e}")
                continue

        # ✅ если реально ничего не добавили — добавляем README, чтобы zip не был "пустым"
        if added == 0:
            z.writestr("README.txt", "No files could be added to the archive.")

    buf.seek(0)
    resp = HttpResponse(buf.getvalue(), content_type="application/zip")

    # ✅ корректно для кириллицы
    quoted = urllib.parse.quote(zip_name)
    resp["Content-Disposition"] = f"attachment; filename*=UTF-8''{quoted}"

    return resp

@login_required
@require_POST
def procedure_file_upload(request):
    client, redirect_resp = require_active_client(request)
    if redirect_resp:
        return redirect_resp

    substep_id = (request.POST.get("substep_id") or "").strip()

    # FIX: если фронт не передал substep_id, пробуем взять из Referer (?open=<substep_id>)
    if not substep_id:
        ref = request.META.get("HTTP_REFERER", "") or ""
        try:
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(ref).query)
            substep_id = (qs.get("open") or [""])[0]
        except Exception:
            substep_id = ""

    if not substep_id:
        messages.error(request, "Не обрано підкрок для завантаження.")
        return redirect(reverse("audit_step", args=[1]))

    substep = get_object_or_404(AuditSubStep, pk=substep_id)

    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        messages.error(request, "Файл не обрано.")
        return redirect(reverse("audit_step", args=[substep.step.order]) + f"?open={substep.id}")

    max_size = 20 * 1024 * 1024
    if uploaded_file.size > max_size:
        messages.error(request, "Файл завеликий (макс 20MB).")
        return redirect(reverse("audit_step", args=[substep.step.order]) + f"?open={substep.id}")

    # --- Atomic anti-duplicate guard (Postgres advisory lock) ---
    # Блокирует параллельные загрузки одного и того же файла для одного юзера/подшага.
    lock_str = f"pf:{client.id}:{substep.id}:{request.user.id}:{uploaded_file.name}"
    lock_key = zlib.crc32(lock_str.encode("utf-8")) & 0xFFFFFFFF

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s);", [lock_key])

        now = timezone.now()
        recent_dup = (
            ProcedureFile.objects.filter(
                client=client,
                procedure_code=str(substep.id),
                uploaded_by=request.user,
                title=uploaded_file.name,
                created_at__gte=now - timedelta(seconds=60),
            )
            .order_by("-created_at")
            .first()
        )

        if recent_dup:
            is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
            if is_ajax:
                return JsonResponse(
                    {
                        "ok": True,
                        "message": "Файл вже був завантажений (дубль запиту відфільтровано).",
                        "substep_id": substep.id,
                        "step_order": substep.step.order,
                        "file": {
                            "id": recent_dup.id,
                            "name": recent_dup.title or uploaded_file.name,
                            "created_at": recent_dup.created_at.isoformat(),
                        },
                        "doc_label": f"Step {substep.step.order}.{substep.order}",
                    }
                )

            messages.info(request, "Файл вже був завантажений (дубль запиту відфільтровано).")
            return redirect(reverse("audit_step", args=[substep.step.order]) + f"?open={substep.id}")

        # 1) сохраняем как ProcedureFile
        pf = ProcedureFile.objects.create(
            client=client,
            procedure_code=str(substep.id),
            file=uploaded_file,
            uploaded_by=request.user,
            title=uploaded_file.name,
        )

        # 2) создаём запись в "База документів" (ClientDocument)
        step_label = f"Step {substep.step.order}.{substep.order}"

        doc = ClientDocument.objects.create(
            organization=request.organization,
            client=client,
            original_name=uploaded_file.name,
            doc_type="other",
            custom_label=step_label,
            uploaded_by=request.user,
        )

        doc.file.name = pf.file.name
        doc.save(update_fields=["file"])

    # ajax ответ
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
    if is_ajax:
        return JsonResponse(
            {
                "ok": True,
                "message": "Файл успішно завантажено.",
                "substep_id": substep.id,
                "step_order": substep.step.order,
                "file": {
                    "id": pf.id,
                    "name": uploaded_file.name,
                    "created_at": pf.created_at.isoformat(),
                },
                "doc_label": step_label,
            }
        )

    messages.success(request, "Файл успішно завантажено.")
    return redirect(reverse("audit_step", args=[substep.step.order]) + f"?open={substep.id}")

@require_POST
@login_required
def procedure_file_delete(request, pk):
    client, redirect_resp = require_active_client(request)
    if redirect_resp:
        return redirect_resp

    f = get_object_or_404(ProcedureFile, pk=pk, client=client)
    code = f.procedure_code
    file_name = f.file.name

    f.delete()

    # удалить физический файл, если он больше нигде не используется
    delete_file_if_unused(file_name, exclude_pf_id=pk)

    return redirect(reverse("audit_step", args=[1]) + f"?open={code}")
