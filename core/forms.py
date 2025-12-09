import re  # <- ДОБАВЬ ЭТУ СТРОКУ

from django import forms
from django.contrib.auth.models import User
from .models import Client


class ClientModelChoiceField(forms.ModelChoiceField):
    """
    На будущее: спец-поле, которое может красиво показывать клиента
    (через метод Client.display_label). Сейчас оно нигде не используется,
    но мешать не будет.
    """
    def label_from_instance(self, obj: Client) -> str:
        return obj.display_label()


class ClientForm(forms.ModelForm):
    # Явно задаём поля дат с форматом под HTML5 date
    requisites_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            format="%Y-%m-%d",
            attrs={"class": "form-control", "type": "date"},
        ),
        input_formats=["%Y-%m-%d"],
        label="Дата договору/документа",
    )

    contract_deadline = forms.DateField(
        required=False,
        widget=forms.DateInput(
            format="%Y-%m-%d",
            attrs={"class": "form-control", "type": "date"},
        ),
        input_formats=["%Y-%m-%d"],
        label="Кінцевий строк виконання договору",
    )

    # Поля команды
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
        label="Асистент 1",
    )
    assistant2 = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label="Асистент 2",
    )
    assistant3 = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label="Асистент 3",
    )
    assistant4 = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label="Асистент 4",
    )

    qa_manager = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=True,
        label="Менеджер КК",
    )

    class Meta:
        model = Client
        fields = [
            # Основные данные
            "name",
            "edrpou",

            # Адрес
            "address_country",
            "address_city",
            "address_street",
            "address_building",
            "address_office",
            "address_zip",

            # КВЭД + ПОІ
            "kved",
            "poi",

            # Реквізити
            "requisites_number",
            "requisites_date",
            "requisites_amount",
            "requisites_vat",

            # Робочі години
            "planned_hours",

            # Нагляд, форма власності
            "supervision_body",
            "legal_form",
            "mandatory_audit",

            # Період і строк
            "reporting_period",
            "contract_deadline",

            # Предмет завдання
            "engagement_subject",

            # Уповноважена особа
            "authorized_person_name",
            "authorized_person_email",

            # Аудиторський звіт
            "audit_report_number",
            "audit_report_date",
            "audit_report_type",
            "audit_report_paragraph",
            "supervision_notice_date",
            "cw_controls_done",

            # Статус
            "status",

            # Команда
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
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "edrpou": forms.TextInput(attrs={"class": "form-control"}),

            "address_country": forms.TextInput(attrs={"class": "form-control"}),
            "address_city": forms.TextInput(attrs={"class": "form-control"}),
            "address_street": forms.TextInput(attrs={"class": "form-control"}),
            "address_building": forms.TextInput(attrs={"class": "form-control"}),
            "address_office": forms.TextInput(attrs={"class": "form-control"}),
            "address_zip": forms.TextInput(attrs={"class": "form-control"}),

            "kved": forms.TextInput(attrs={"class": "form-control"}),
            "poi": forms.CheckboxInput(),

            "requisites_number": forms.TextInput(attrs={"class": "form-control"}),
            # requisites_date задаём выше как отдельное поле

            "requisites_amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "requisites_vat": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),

            "planned_hours": forms.NumberInput(attrs={"class": "form-control", "step": "0.1"}),

            "supervision_body": forms.Select(attrs={"class": "form-control"}),
            "legal_form": forms.Select(attrs={"class": "form-control"}),
            "mandatory_audit": forms.CheckboxInput(),

            "reporting_period": forms.TextInput(attrs={"class": "form-control"}),
            # contract_deadline задаём выше как отдельное поле

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ОБЯЗАТЕЛЬНЫЕ ПОЛЯ
        required_fields = [
            "name",
            "edrpou",

            "address_country",
            "address_city",
            "address_street",
            "address_building",
            "address_office",
            "kved",
            "address_zip",

            "requisites_number",
            "requisites_date",
            "requisites_amount",
            "requisites_vat",

            "planned_hours",

            "supervision_body",
            "legal_form",

            "reporting_period",
            "contract_deadline",

            "engagement_subject",

            "authorized_person_name",
            "authorized_person_email",

            "status",

            "manager",
            "qa_manager",
        ]

        for field_name in required_fields:
            if field_name in self.fields:
                field = self.fields[field_name]

                # делаем поле обязательным на уровне Django
                field.required = True

                # убираем HTML5 required, чтобы не мешал отправке
                field.widget.attrs.pop("required", None)

                # добавляем CSS-класс для подсветки
                css = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = (css + " required-input").strip()

    def clean_reporting_period(self):
        """
        Допустимые варианты:
        - '2022'
        - '1 квартал 2022'
        - '2 квартал 2022'
        - '3 квартал 2022'
        """
        value = self.cleaned_data.get("reporting_period", "")
        value_stripped = (value or "").strip()

        if not value_stripped:
            return value

        pattern_year = r"^\d{4}$"
        pattern_quarter = r"^[1-3]\s*й?\s*квартал\s+\d{4}$"

        if re.match(pattern_year, value_stripped) or re.match(pattern_quarter, value_stripped):
            return value_stripped

        raise forms.ValidationError(
            "Допустимі формати: '2022' або '1 квартал 2022', '2 квартал 2022', '3 квартал 2022'."
        )

    def clean(self):
        cleaned_data = super().clean()

        audit_report_type = cleaned_data.get("audit_report_type")
        audit_report_date = cleaned_data.get("audit_report_date")

        if audit_report_type and not audit_report_date:
            self.add_error(
                "audit_report_date",
                "Укажіть дату аудиторського звіту, оскільки обрано його вид.",
            )

        if audit_report_date and not audit_report_type:
            self.add_error(
                "audit_report_type",
                "Укажіть вид аудиторського звіту, оскільки вказано дату.",
            )

        return cleaned_data
