from django import forms
from django.contrib.auth.models import User
from .models import Client


class ClientForm(forms.ModelForm):
    manager = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=True,
        label="Менеджер",
    )

    auditor = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label="Аудитор 1",
    )
    auditor2 = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label="Аудитор 2",
    )
    auditor3 = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label="Аудитор 3",
    )

    assistant = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label="Ассистент 1",
    )
    assistant2 = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label="Ассистент 2",
    )
    assistant3 = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label="Ассистент 3",
    )
    assistant4 = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label="Ассистент 4",
    )

    qa_manager = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=True,
        label="Менеджер КК",
    )

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            # 1–2. Основные данные
            "name",
            "edrpou",

            # Адрес
            "address_country",
            "address_city",
            "address_street",
            "address_building",
            "address_office",
            "address_zip",

            # КВЭД + ПОИ
            "kved",
            "poi",

            # Реквизиты
            "requisites_number",
            "requisites_date",
            "requisites_amount",
            "requisites_vat",

            # >>> НОВОЕ ПОЛЕ
            "planned_hours",

            # Надзор, ОПФ, обязательный аудит
            "supervision_body",
            "legal_form",
            "mandatory_audit",

            # Период и срок
            "reporting_period",
            "contract_deadline",

            # Предмет задания
            "engagement_subject",

            # Уполномоченное лицо
            "authorized_person_name",
            "authorized_person_email",

            # Аудиторский отчёт
            "audit_report_number",
            "audit_report_date",
            "audit_report_type",
            "audit_report_paragraph",
            "supervision_notice_date",
            "cw_controls_done",

            # Статус
            "status",

            # Роли
            "manager",
            "auditor",
            "auditor2",
            "auditor3",
            "assistant",
            "assistant2",
            "assistant3",
            "assistant4",
            "qa_manager",
        ]

        widgets = {
            # пример, подставь свои уже существующие виджеты
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "edrpou": forms.TextInput(attrs={"class": "form-control"}),

            "requisites_number": forms.TextInput(attrs={"class": "form-control"}),
            "requisites_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "requisites_amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "requisites_vat": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),

            # >>> ВИДЖЕТ ДЛЯ РАБОЧИХ ЧАСОВ
            "planned_hours": forms.NumberInput(attrs={"class": "form-control", "step": "0.1"}),

            "supervision_body": forms.Select(attrs={"class": "form-control"}),
            "legal_form": forms.Select(attrs={"class": "form-control"}),
            "mandatory_audit": forms.CheckboxInput(),

            "reporting_period": forms.TextInput(attrs={"class": "form-control"}),
            "contract_deadline": forms.DateInput(attrs={"type": "date", "class": "form-control"}),

            "engagement_subject": forms.Select(attrs={"class": "form-control"}),

            "authorized_person_name": forms.TextInput(attrs={"class": "form-control"}),
            "authorized_person_email": forms.EmailInput(attrs={"class": "form-control"}),

            "audit_report_number": forms.TextInput(attrs={"class": "form-control"}),
            "audit_report_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "audit_report_type": forms.Select(attrs={"class": "form-control"}),
            "audit_report_paragraph": forms.Select(attrs={"class": "form-control"}),
            "supervision_notice_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "cw_controls_done": forms.CheckboxInput(),

            "status": forms.TextInput(attrs={"class": "form-control"}),

            "manager": forms.Select(attrs={"class": "form-control"}),

            "auditor": forms.Select(attrs={"class": "form-control"}),
            "auditor2": forms.Select(attrs={"class": "form-control"}),
            "auditor3": forms.Select(attrs={"class": "form-control"}),

            "assistant": forms.Select(attrs={"class": "form-control"}),
            "assistant2": forms.Select(attrs={"class": "form-control"}),
            "assistant3": forms.Select(attrs={"class": "form-control"}),
            "assistant4": forms.Select(attrs={"class": "form-control"}),

            "qa_manager": forms.Select(attrs={"class": "form-control"}),
        }