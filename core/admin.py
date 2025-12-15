from django.contrib import admin
from .models import Organization, Client, ClientDocument, News
from .models import ProcedureFile
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (Organization, Client, ClientDocument, News, ProcedureFile, AuditStep, AuditSubStep, StepAction)

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

# =================== AUDIT STEP SYSTEM (ADMIN) ===================

class AuditSubStepInline(admin.TabularInline):
    model = AuditSubStep
    extra = 0
    fields = ("order", "title", "is_active")
    ordering = ("order",)


class StepActionInlineForStep(admin.TabularInline):
    model = StepAction
    extra = 0
    fields = ("order", "label", "key", "enabled", "placement", "scope")
    ordering = ("order",)

    # показываем только actions, привязанные к шагу
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(substep__isnull=True)

    # чтобы случайно не привязать к substep из инлайна шага
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "substep":
            kwargs["queryset"] = AuditSubStep.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class StepActionInlineForSubStep(admin.TabularInline):
    model = StepAction
    extra = 0
    fields = ("order", "label", "key", "enabled", "placement", "scope")
    ordering = ("order",)

    # показываем только actions, привязанные к подшагу
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(step__isnull=True)

    # чтобы случайно не привязать к step из инлайна подшага
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "step":
            kwargs["queryset"] = AuditStep.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(AuditStep)
class AuditStepAdmin(admin.ModelAdmin):
    list_display = ("order", "title", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title",)
    ordering = ("order",)

    fieldsets = (
        (_("Основне"), {
            "fields": ("order", "title", "is_active"),
        }),
        (_("Опис"), {
            "fields": ("purpose", "documentation", "procedure_description", "expected_result"),
        }),
    )

    inlines = [AuditSubStepInline, StepActionInlineForStep]


@admin.register(AuditSubStep)
class AuditSubStepAdmin(admin.ModelAdmin):
    list_display = ("step", "order", "title", "is_active")
    list_filter = ("is_active", "step")
    search_fields = ("title",)
    ordering = ("step__order", "order")

    fieldsets = (
        (_("Прив'язка"), {
            "fields": ("step", "order", "title", "is_active"),
        }),
        (_("Опис"), {
            "fields": ("purpose", "documentation", "procedure_description", "expected_result"),
        }),
    )

    inlines = [StepActionInlineForSubStep]


@admin.register(StepAction)
class StepActionAdmin(admin.ModelAdmin):
    list_display = ("label", "key", "enabled", "scope", "placement", "order", "step", "substep")
    list_filter = ("enabled", "scope", "placement")
    search_fields = ("label", "key")
    ordering = ("scope", "order")
    filter_horizontal = ("allowed_groups",)
