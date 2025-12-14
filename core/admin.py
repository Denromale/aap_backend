from django.contrib import admin
from .models import Organization, Client, ClientDocument, News
from .models import ProcedureFile


# ---------- ORGANIZATION ----------
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


# ---------- CLIENT ----------
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "organization",      # ← показываем организацию в списке
        "edrpou",
        "reporting_period",
        "status",
        "created_at",
    )
    search_fields = ("name", "edrpou", "kved", "requisites_number")
    list_filter = (
        "organization",      # ← фильтр по организации
        "status",
        "poi",
        "mandatory_audit",
        "cw_controls_done",
    )

    fieldsets = (
        ("Організація", {
            "fields": ("organization",),   # ← организация теперь явно в форме
        }),
        ("Основные данные", {
            "fields": ("name", "edrpou", "kved", "poi"),
        }),
        ("Адрес (местонахождение)", {
            "fields": (
                "address_country",
                "address_city",
                "address_street",
                "address_building",
                "address_office",
                "address_zip",
            ),
        }),
        ("Реквизиты договора", {
            "fields": (
                "requisites_number",
                "requisites_date",
                "requisites_amount",
                "requisites_vat",
                "planned_hours",
            ),
        }),
        ("Надзор, ОПФ, обязательный аудит", {
            "fields": ("supervision_body", "legal_form", "mandatory_audit"),
        }),
        ("Период и срок", {
            "fields": ("reporting_period", "contract_deadline"),
        }),
        ("Предмет задания", {
            "fields": ("engagement_subject", "task_subject", "deadline"),
        }),
        ("Уполномоченное лицо клиента", {
            "fields": ("authorized_person_name", "authorized_person_email"),
        }),
        ("Аудиторский отчёт", {
            "fields": (
                "audit_report_number",
                "audit_report_date",
                "audit_report_type",
                "audit_report_paragraph",
                "supervision_notice_date",
                "cw_controls_done",
            ),
        }),
        ("Статус и команда", {
            "fields": (
                "status",
                "manager",
                "auditor", "auditor2", "auditor3",
                "assistant", "assistant2", "assistant3", "assistant4",
                "qa_manager",
            ),
        }),
    )


# ---------- DOCUMENTS ----------
@admin.register(ClientDocument)
class ClientDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "original_name", "client", "organization", "doc_type", "created_at")
    search_fields = ("original_name",)
    list_filter = ("organization", "doc_type")


# ---------- NEWS ----------
@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at", "is_published")
    list_filter = ("is_published", "created_at")
    search_fields = ("title", "body")

@admin.register(ProcedureFile)
class ProcedureFileAdmin(admin.ModelAdmin):
    list_display = ("id", "client", "procedure_code", "file", "uploaded_by", "created_at")
    list_filter = ("procedure_code", "created_at")
    search_fields = ("client__name", "procedure_code", "file")
    ordering = ("-created_at",)