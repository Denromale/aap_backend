from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth.models import Group

# =================== ОРГАНІЗАЦІЯ ===================

class Organization(models.Model):
    name = models.CharField(_("Назва організації"), max_length=255, unique=True)

    def __str__(self) -> str:
        return self.name

def client_audit_report_upload_to(instance, filename):
    # отдельная папка для отчётов, чтобы не мешались с договорами/документами
    return f"clients/{instance.id}/audit_report/{filename}"
# =================== СПРАВОЧНИКИ ===================

# Предмет завдання
ASSIGNMENT_SUBJECT_CHOICES = [
    # О – публічний інтерес
    ("O_AUDIT",      _("Аудит фінансової звітності та/або консолідованої фінансової звітності (О)")),
    ("O_REVIEW",     _("Огляд історичної фінансової звітності та проміжної фінансової інформації (О)")),
    ("O_ASSURANCE",  _("Завдання з надання впевненості, не є аудитом або оглядом (О)")),

    # І – інші завдання
    ("I_AUDIT",      _("Аудит фінансової звітності та/або консолідованої фінансової звітності (І)")),
    ("I_REVIEW",     _("Огляд історичної фінансової звітності та проміжної фінансової інформації (І)")),
    ("I_ASSURANCE",  _("Завдання з надання впевненості, не є аудитом або оглядом (І)")),

    # Інші послуги
    ("RELATED",      _("Супутні послуги")),
    ("NON_AUDIT",    _("Інші неаудиторські послуги")),
]


# Організаційно-правова форма
LEGAL_FORM_CHOICES = [
    ("FOP",            _("Фізична особа-підприємець")),
    ("LLC",            _("Товариство з обмеженою відповідальністю (ТОВ)")),
    ("OAO",            _("Відкрите акціонерне товариство (ВАТ)")),
    ("ZAO",            _("Закрите акціонерне товариство (ЗАТ)")),
    ("CHAO",           _("Приватне акціонерне товариство (ПрАТ)")),
    ("KT",             _("Командитне товариство")),
    ("KOLL",           _("Командитне товариство з обмеженою відповідальністю")),
    ("PARTNER",        _("Партнерства (господарські товариства)")),
    ("COOP",           _("Кооперативи")),
    ("FOREIGN_BRANCH", _("Філія або представництво іноземної компанії")),
    ("FOREIGN_INVEST", _("Підприємства з іноземними інвестиціями")),
    ("INT_ORG",        _("Міжнародні господарські організації")),
    ("FARM",           _("Фермерські господарства")),
    ("STATE_ENT",      _("Державні підприємства")),
    ("KAZENNOE",       _("Казенні підприємства")),
    ("COMMUNAL",       _("Комунальні підприємства")),
    ("LLC2",           _("Товариство з обмеженою відповідальністю (інше)")),
    ("ODD",            _("Товариство з додатковою відповідальністю")),
    ("GOV",            _("Органи державної влади")),
    ("GOV_ORG",        _("Державні організації (установи, заклади)")),
    ("POLITICAL",      _("Політичні партії")),
    ("NGO",            _("Громадські та благодійні організації")),
    ("PAO",            _("Публічні акціонерні товариства")),
    ("APU",            _("Аудиторська палата України")),

    # коди, додані під старі текстові значення з БД
    ("PRIVATE_ENT",    _("Приватне підприємство")),
    ("SUBSIDIARY_ENT", _("Дочірнє підприємство")),
    ("JSC",            _("Акціонерне товариство")),
]


# Орган нагляду
SUPERVISORY_BODY_CHOICES = [
    ("AGRARIAN",        _("Міністерство аграрної політики та продовольства України")),
    ("MIA",             _("Міністерство внутрішніх справ України")),
    ("ECOLOGY",         _("Міністерство екології та природних ресурсів України")),
    ("ECONOMY",         _("Міністерство економічного розвитку і торгівлі України")),
    ("ENERGY",          _("Міністерство енергетики та вугільної промисловості України")),
    ("INFRA",           _("Міністерство інфраструктури України")),
    ("CULTURE",         _("Міністерство культури України")),
    ("EDU",             _("Міністерство освіти і науки України")),
    ("HEALTH",          _("Міністерство охорони здоров’я України")),
    ("SOCIAL",          _("Міністерство соціальної політики України")),
    ("FINANCE",         _("Міністерство фінансів України")),
    ("DSSZZI",          _("Адміністрація Держспецзв’язку України")),
    ("NUCLEAR",         _("Державна інспекція ядерного регулювання України")),
    ("REG_SERVICE",     _("Державна регуляторна служба України")),
    ("FOOD_SAFETY",     _("Держпродспоживслужба України")),
    ("FORESTRY",        _("Держлісагентство України")),
    ("FISHERIES",       _("Держрибагентство України")),
    ("EMERGENCY",       _("ДСНС України")),
    ("ECO_INSPECTION",  _("Державна екологічна інспекція України")),
    ("GEOLOGY",         _("Державна служба геології та надр України")),
    ("AVIA",            _("Державіаслужба України")),
    ("TRANSPORT",       _("Укртрансбезпека")),
    ("CINEMA",          _("Держкіно України")),
    ("EDU_QUALITY",     _("Державна служба якості освіти України")),
    ("DRUG_CONTROL",    _("Держлікслужба України")),
    ("DABI",            _("ДАБІ України")),
    ("GEO_CADASTRE",    _("Держгеокадастр України")),
    ("LABOR",           _("Державна служба з питань праці")),
    ("PENSION",         _("Пенсійний фонд України")),
    ("TAX",             _("Державна фіскальна служба")),
    ("NCR_FIN",         _("Нацкомфінпослуг")),
    ("NCR_EC",          _("НКРЕКП")),
    ("NCSM",            _("НКЦПФР")),
    ("SBU",             _("Служба безпеки України")),
    ("ENERGY_SUPERV",   _("Інспекція енергетичного нагляду України")),
    ("MINREGION",       _("Міністерство розвитку громад та територій України")),
    ("SEA_RIVER_TRANSPORT", _("Морська адміністрація України")),
    ("NBU",             _("Національний банк України")),
]



REPORT_TYPE_CHOICES = [
    ("QUALIFIED", _("Думка із застереженням")),
    ("ADVERSE", _("Негативна думка")),
    ("DISCLAIMER", _("Відмова від висловлення думки")),
]

REPORT_PARAGRAPH_CHOICES = [
    ("OTHER", _("Параграф: Інше")),
    ("GOING_CONCERN", _("Суттєва невизначеність щодо безперервності діяльності")),
]


# =================== CLIENT ===================

class Client(models.Model):
    organization = models.ForeignKey(
        "Organization",
        on_delete=models.CASCADE,
        related_name="clients",
        verbose_name=_("Організація"),
        null=True,
        blank=True,
    )

    # Основні дані
    name = models.CharField(_("Повна назва клієнта"), max_length=255)
    edrpou = models.CharField(_("ЄДРПОУ"), max_length=20, blank=True, null=True)

    # Адреса
    address_country = models.CharField(_("Країна"), max_length=100, blank=True, null=True)
    address_city = models.CharField(_("Місто"), max_length=100, blank=True, null=True)
    address_street = models.CharField(_("Вулиця"), max_length=255, blank=True, null=True)
    address_building = models.CharField(_("Будинок/корпус"), max_length=50, blank=True, null=True)
    address_office = models.CharField(_("Офіс"), max_length=50, blank=True, null=True)
    address_zip = models.CharField(_("Індекс"), max_length=20, blank=True, null=True)

    # КВЕД і ПОІ
    kved = models.CharField(_("КВЕД"), max_length=255, blank=True, null=True)
    poi = models.BooleanField(_("ПОІ"), default=False)

    # Реквізити договору
    requisites_number = models.CharField(_("№ договору/документа"), max_length=100, blank=True, null=True)
    requisites_date = models.DateField(_("Дата договору/документа"), blank=True, null=True)
    requisites_amount = models.DecimalField(_("Сума договору"), max_digits=14, decimal_places=2, blank=True, null=True)
    requisites_vat = models.DecimalField(_("ПДВ"), max_digits=14, decimal_places=2, blank=True, null=True)

    # Нагляд, форма власності
    supervision_body = models.CharField(
        _("Орган нагляду"),
        max_length=255,
        choices=SUPERVISORY_BODY_CHOICES,
        blank=True,
        null=True,
    )
    legal_form = models.CharField(
        _("Організаційно-правова форма"),
        max_length=255,
        choices=LEGAL_FORM_CHOICES,
        blank=True,
        null=True,
    )
    mandatory_audit = models.BooleanField(_("Обов'язковий аудит (огляд)"), default=False)

    # Період
    reporting_period = models.CharField(_("Звітний період"), max_length=50, blank=True, null=True)
    contract_deadline = models.DateField(_("Кінцевий строк виконання договору"), blank=True, null=True)

    # Предмет завдання
    engagement_subject = models.CharField(
        _("Предмет завдання"),
        max_length=100,
        choices=ASSIGNMENT_SUBJECT_CHOICES,
        blank=True,
        null=True,
    )

    # Уповноважена особа
    authorized_person_name = models.CharField(_("ПІБ уповноваженої особи"), max_length=255, blank=True, null=True)
    authorized_person_email = models.EmailField(_("Email уповноваженої особи"), blank=True, null=True)

    # Аудиторський звіт
    audit_report_number = models.CharField(_("№ аудиторського звіту"), max_length=100, blank=True, null=True)
    audit_report_date = models.DateField(_("Дата аудиторського звіту"), blank=True, null=True)
    audit_report_type = models.CharField(_("Вид аудиторського звіту"),  max_length=255, choices=REPORT_TYPE_CHOICES, blank=True, null=True,)
    audit_report_paragraph = models.CharField(_("Параграф аудиторського звіту"), max_length=255, choices=REPORT_PARAGRAPH_CHOICES, blank=True, null=True,)

    supervision_notice_date = models.DateField(_("Дата повідомлення органу нагляду"), blank=True, null=True)

    cw_controls_done = models.BooleanField(_("Контрольні процедури в CW виконані"), default=False)
    audit_report_scan = models.FileField(_("Скан-копія аудиторського звіту"), upload_to=client_audit_report_upload_to, blank=True, null=True,)

    # Години
    planned_hours = models.DecimalField(_("Робочі години (план)"), max_digits=10, decimal_places=2, blank=True, null=True)

    # Статус
    status = models.CharField(_("Статус"), max_length=50, default="new")

    is_completed = models.BooleanField(default=False, db_index=True, verbose_name=_("Проєкт завершено"))
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name=_("Дата завершення"))
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="completed_clients",
        verbose_name=_("Хто завершив"),
    )


    # Команда
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Менеджер"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients_as_manager",
    )
    auditor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Аудитор 1"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients_as_auditor1",
    )
    auditor2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Аудитор 2"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients_as_auditor2",
    )
    auditor3 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Аудитор 3"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients_as_auditor3",
    )

    assistant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Асистент 1"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients_as_assistant1",
    )
    assistant2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Асистент 2"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients_as_assistant2",
    )
    assistant3 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Асистент 3"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients_as_assistant3",
    )
    assistant4 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Асистент 4"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients_as_assistant4",
    )

    qa_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Менеджер КК"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients_as_qa_manager",
    )

    # username для імпорту
    manager_username = models.CharField(_("Менеджер (username)"), max_length=150, blank=True)
    auditor_username = models.CharField(_("Аудитор 1 (username)"), max_length=150, blank=True)
    auditor2_username = models.CharField(_("Аудитор 2 (username)"), max_length=150, blank=True)
    auditor3_username = models.CharField(_("Аудитор 3 (username)"), max_length=150, blank=True)
    assistant_username = models.CharField(_("Асистент 1 (username)"), max_length=150, blank=True)
    assistant2_username = models.CharField(_("Асистент 2 (username)"), max_length=150, blank=True)
    assistant3_username = models.CharField(_("Асистент 3 (username)"), max_length=150, blank=True)
    assistant4_username = models.CharField(_("Асистент 4 (username)"), max_length=150, blank=True)
    qa_manager_username = models.CharField(_("QA-менеджер (username)"), max_length=150, blank=True)
    is_completed = models.BooleanField(_("Проект завершено"), default=False, db_index=True)
    completed_at = models.DateTimeField(_("Дата завершення"), blank=True, null=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="completed_clients",
        verbose_name=_("Хто завершив"),
    )


    created_at = models.DateTimeField(_("Створено"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Оновлено"), auto_now=True)

    task_subject = models.CharField(_("Предмет завдання (додатково)"), max_length=255, blank=True)
    deadline = models.DateField(_("Кінцевий строк виконання договору (додатково)"), null=True, blank=True)

    def save(self, *args, **kwargs):
        """
        Авто-узгодження команди по всіх «проєктах» з тим самим договором.

        Логіка:
        1) Якщо створюється новий клієнт з номером+датою договору і вже існує
           запис з таким самим договором → команда КОПІЮЄТЬСЯ з першого запису.
           Тобто введена в формі команда ігнорується, щоб всі проєкти за цим
           договором мали одну й ту ж команду.
        2) Якщо це перший запис за договором (ще немає інших клієнтів з тим
           самим номером+датою) → зберігаємо як є і РОЗПОВСЮДЖУЄМО команду
           по всіх майбутніх змінах цього запису.
        3) Якщо змінено команду у наявного клієнта → команда оновлюється в
           усіх записах з тим самим договором.
        """

        team_fields = [
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

        is_new = self.pk is None
        propagate_team = False  # чи треба після збереження оновлювати інших

        # ---------- НОВИЙ ЗАПИС ----------
        if is_new:
            # Якщо немає договору – нічого не розповсюджуємо та не копіюємо
            if not self.requisites_number or not self.requisites_date:
                propagate_team = False
            else:
                # Шукаємо "базовий" запис з таким самим договором
                base_qs = Client.objects.filter(
                    organization=self.organization,
                    name=self.name,
                    requisites_number=self.requisites_number,
                    requisites_date=self.requisites_date,
                )

                base_client = base_qs.first()

                if base_client:
                    # Договір уже існує: КОПІЮЄМО команду з нього
                    for field in team_fields:
                        setattr(self, field, getattr(base_client, field))
                    # Не розповсюджуємо, команда вже узгоджена з базовим
                    propagate_team = False
                else:
                    # Це перший запис з таким договором → після save рознесемо
                    propagate_team = True

        # ---------- ІСНУЮЧИЙ ЗАПИС ----------
        else:
            # Перевіряємо, чи змінилась команда (щоб не робити зайвих оновлень)
            try:
                old = Client.objects.get(pk=self.pk)
            except Client.DoesNotExist:
                old = None

            if old:
                for field in team_fields:
                    if getattr(old, field) != getattr(self, field):
                        propagate_team = True
                        break

        # ---------- ЗБЕРІГАЄМО ПОТОЧНИЙ ЗАПИС ----------
        super().save(*args, **kwargs)

        # Якщо немає договору – нічого не розповсюджуємо
        if not self.requisites_number or not self.requisites_date:
            return

        # Якщо не потрібно розповсюджувати – виходимо
        if not propagate_team:
            return

        # ---------- ОНОВЛЮЄМО ІНШІ ЗАПИСИ З ТИМ САМИМ ДОГОВОРОМ ----------
        qs = Client.objects.filter(
            organization=self.organization,
            name=self.name,
            requisites_number=self.requisites_number,
            requisites_date=self.requisites_date,
        ).exclude(pk=self.pk)

        if not qs.exists():
            return

        update_data = {field: getattr(self, field) for field in team_fields}
        qs.update(**update_data)


    def display_label(self) -> str:
        parts = [self.name or ""]

        if self.reporting_period:
            parts.append(str(self.reporting_period))
        if self.requisites_number:
            parts.append(f"Дог. {self.requisites_number}")
        if self.engagement_subject:
            parts.append(self.get_engagement_subject_display())

        return " | ".join(parts)

    def __str__(self) -> str:
        return self.display_label()


# =================== ДОКУМЕНТИ КЛІЄНТА ===================

class ClientDocument(models.Model):
    DOC_TYPE_CHOICES = [
        ("", "---------"),
        ("charter", _("Установчий документ")),
        ("request", _("Запит / лист")),
        ("agreement", _("Договір")),
        ("other", _("Інше")),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name=_("Організація"),
        null=True,
        blank=True,
    )

    client = models.ForeignKey(
        "Client",
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name=_("Клієнт"),
    )
    file = models.FileField(upload_to="client_docs/", verbose_name=_("Файл"))
    original_name = models.CharField(_("Оригінальна назва"), max_length=255, blank=True, null=True)
    doc_type = models.CharField(_("Тип документа"), max_length=50, choices=DOC_TYPE_CHOICES, blank=True, null=True)
    custom_label = models.CharField(_("Мітка / примітка"), max_length=255, blank=True, null=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Користувач, який завантажив"),
    )
    created_at = models.DateTimeField(_("Створено"), auto_now_add=True)

    def __str__(self) -> str:
        return self.original_name or f"Документ #{self.pk}"


# =================== НОВИНИ ===================

class News(models.Model):
    title = models.CharField(_("Заголовок"), max_length=255)
    body = models.TextField(_("Текст"), blank=True)
    image = models.ImageField(_("Зображення"), upload_to="news/", blank=True, null=True)
    link = models.URLField(_("Посилання (опціонально)"), blank=True)
    is_published = models.BooleanField(_("Опубліковано"), default=True)
    created_at = models.DateTimeField(_("Створено"), auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class ProcedureFile(models.Model):
    client = models.ForeignKey(
        "Client",
        on_delete=models.CASCADE,
        related_name="procedure_files",
    )
    procedure_code = models.CharField(max_length=20)  # "1_1", "2_3" и т.д.

    title = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to="procedure_files/")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.client_id} / {self.procedure_code} / {self.file.name}"

# =================== AUDIT STEP SYSTEM (TEMPLATES) ===================

class AuditStep(models.Model):
    title = models.CharField(_("Назва кроку"), max_length=255)
    purpose = models.TextField(_("Мета"), blank=True)
    documentation = models.TextField(_("Документування"), blank=True)
    procedure_description = models.TextField(_("Опис процедур"), blank=True)
    expected_result = models.TextField(_("Очікуваний результат"), blank=True)

    order = models.PositiveIntegerField(_("Порядок"), default=1, db_index=True)
    is_active = models.BooleanField(_("Активний"), default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("Крок аудиту (шаблон)")
        verbose_name_plural = _("Кроки аудиту (шаблони)")

    def __str__(self) -> str:
        return f"{self.order}. {self.title}"


class AuditSubStep(models.Model):
    step = models.ForeignKey(
        AuditStep,
        on_delete=models.CASCADE,
        related_name="substeps",
        verbose_name=_("Крок"),
    )

    title = models.CharField(_("Назва підкроку"), max_length=255)
    purpose = models.TextField(_("Мета"), blank=True)
    documentation = models.TextField(_("Документування"), blank=True)
    procedure_description = models.TextField(_("Опис процедур"), blank=True)
    expected_result = models.TextField(_("Очікуваний результат"), blank=True)

    order = models.PositiveIntegerField(_("Порядок"), default=1, db_index=True)
    is_active = models.BooleanField(_("Активний"), default=True)

    class Meta:
        ordering = ["step__order", "order", "id"]
        verbose_name = _("Підкрок аудиту (шаблон)")
        verbose_name_plural = _("Підкроки аудиту (шаблони)")
        unique_together = (("step", "order"),)

    def __str__(self) -> str:
        return f"{self.step.order}.{self.order} {self.title}"


class StepAction(models.Model):
    class Scope(models.TextChoices):
        STEP = "step", _("На кроці")
        SUBSTEP = "substep", _("На підкроці")

    class Placement(models.TextChoices):
        TOP = "top", _("Вгорі")
        INLINE = "inline", _("У блоці")
        BOTTOM = "bottom", _("Внизу")

    key = models.SlugField(_("Ключ"), max_length=80)
    label = models.CharField(_("Текст кнопки"), max_length=120)
    description = models.CharField(_("Опис"), max_length=255, blank=True)

    enabled = models.BooleanField(_("Увімкнено"), default=True)
    order = models.PositiveIntegerField(_("Порядок"), default=1, db_index=True)

    scope = models.CharField(_("Де доступна"), max_length=20, choices=Scope.choices, default=Scope.STEP)
    placement = models.CharField(_("Де показувати"), max_length=20, choices=Placement.choices, default=Placement.INLINE)

    # Прив'язка дії або до Step, або до SubStep (залежно від scope)
    step = models.ForeignKey(
        AuditStep,
        on_delete=models.CASCADE,
        related_name="actions",
        verbose_name=_("Крок"),
        null=True,
        blank=True,
    )
    substep = models.ForeignKey(
        AuditSubStep,
        on_delete=models.CASCADE,
        related_name="actions",
        verbose_name=_("Підкрок"),
        null=True,
        blank=True,
    )

    allowed_groups = models.ManyToManyField(
        Group,
        blank=True,
        related_name="aap_step_actions",
        verbose_name=_("Дозволені групи"),
        help_text=_("Хто може бачити/виконувати цю дію."),
    )

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("Дія кроку (кнопка)")
        verbose_name_plural = _("Дії кроків (кнопки)")
        constraints = [
            models.UniqueConstraint(fields=["step", "key"], name="uniq_action_key_per_step"),
            models.UniqueConstraint(fields=["substep", "key"], name="uniq_action_key_per_substep"),
        ]

    def __str__(self) -> str:
        target = self.step or self.substep
        return f"{self.label} ({self.key}) -> {target}"
