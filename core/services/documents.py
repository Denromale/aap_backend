from __future__ import annotations

import os
from io import BytesIO
from typing import Tuple

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from docx import Document

from core.models import Client, ClientDocument, ProcedureFile


def fill_docx(template_path: str, context: dict) -> BytesIO:
    """
    Открывает docx, подставляет значения по меткам и возвращает файл в памяти.
    Логика 1-в-1 как в views.py.
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


def _fill_docx_bytes(template_name: str, client: Client, user):
    """
    Генерация bytes как в views.py (Step 1.5 и др.).
    """
    template_path = os.path.join(settings.BASE_DIR, "core", "docs", template_name)
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
        "{{ CURRENT_USER }}": user.get_full_name() or user.username,
    }

    file_obj = fill_docx(template_path, context_doc)
    return file_obj.getvalue()


def _step15_save_generated(
    request, *, client: Client, substep, file_bytes: bytes, filename: str, title: str
) -> Tuple[ProcedureFile, ClientDocument]:
    """
    Сохраняем один раз в storage через ProcedureFile,
    а ClientDocument ссылаем на тот же file.name.
    Логика 1-в-1 как в views.py.
    """
    # 1) ProcedureFile (для отображения на шаге)
    pf = ProcedureFile.objects.create(
        client=client,
        procedure_code=str(substep.id),
        uploaded_by=request.user,
        title=title or filename,
    )
    pf.file.save(filename, ContentFile(file_bytes), save=True)

    # 2) ClientDocument (База документів)
    step_label = f"Step {substep.step.order}.{substep.order}"

    doc = ClientDocument.objects.create(
        organization=request.organization,
        client=client,
        original_name=filename,
        doc_type="request",
        custom_label=step_label,
        uploaded_by=request.user,
    )

    # НЕ копируем файл, а ссылаемся на уже сохранённый pf.file
    doc.file.name = pf.file.name
    doc.save(update_fields=["file"])

    return pf, doc
