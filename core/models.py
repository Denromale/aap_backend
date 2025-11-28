from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _



# =================== СПРАВОЧНИКИ ===================

ASSIGNMENT_SUBJECT_CHOICES = [
    ("O_AUDIT", _("Аудит фінансової звітності та/або консолідованої фінансової звітності (О)")),
    ("O_REVIEW", _("Огляд історичної фінансової звітності та проміжної фінансової інформації (О)")),
    ("O_ASSURANCE", _("Завдання з надання впевненості, не є аудитом або оглядом (О)")),

    ("I_AUDIT", _("Аудит фінансової звітності та/або консолідованої фінансової звітності (І)")),
    ("I_REVIEW", _("Огляд історичної фінансової звітності та проміжної фінансової інформації (І)")),
    ("I_ASSURANCE", _("Завдання з надання впевненості, не є аудитом або оглядом (І)")),

    ("RELATED", _("Супутні послуги")),
    ("NON_AUDIT", _("Інші неаудиторські послуги")),
]


LEGAL_FORM_CHOICES = [
    ("FOP", _("Фізична особа-підприємець")),
    ("LLC", _("Товариство з обмеженою відповідальністю (ТОВ)")),
    ("OAO", _("Відкрите акціонерне товариство (ВАТ)")),
    ("ZAO", _("Закрите акціонерне товариство (ЗАТ)")),
    ("CHAO", _("Приватне акціонерне товариство (ПрАТ)")),
    ("KT", _("Командитне товариство")),
    ("KOLL", _("Командитне товариство з обмеженою відповідальністю")),
    ("PARTNER", _("Партнерства (господарські товариства)")),
    ("COOP", _("Кооперативи")),
    ("FOREIGN_BRANCH", _("Філія або представництво іноземної компанії")),
    ("FOREIGN_INVEST", _("Підприємства з іноземними інвестиціями")),
    ("INT_ORG", _("Міжнародні господарські організації")),
    ("FARM", _("Фермерські господарства")),
    ("STATE_ENT", _("Державні підприємства")),
    ("KAZENNOE", _("Казенні підприємства")),
    ("COMMUNAL", _("Комунальні підприємства")),
    ("LLC2", _("Товариство з обмеженою відповідальністю (інше)")),
    ("ODD", _("Товариство з додатковою відповідальністю")),
    ("GOV", _("Органи державної влади")),
    ("GOV_ORG", _("Державні організації (установи, заклади)")),
    ("POLITICAL", _("Політичні партії")),
    ("NGO", _("Громадські та благодійні організації")),
    ("PAO", _("Публічні акціонерні товариства")),
    ("APU", _("Аудиторська палата України")),
]


SUPERVISORY_BODY_CHOICES = [
    ("AGRARIAN", _("Міністерство аграрної політики та продовольства України")),
    ("MIA", _("Міністерство внутрішніх справ України")),
    ("ECOLOGY", _("Міністерство екології та природних ресурсів України")),
    ("ECONOMY", _("Міністерство економічного розвитку і торгівлі України")),
    ("ENERGY", _("Міністерство енергетики та вугільної промисловості України")),
    ("INFRA", _("Міністерство інфраструктури України")),
    ("CULTURE", _("Міністерство культури України")),
    ("EDU", _("Міністерство освіти і науки України")),
    ("HEALTH", _("Міністерство охорони здоров’я України")),
    ("SOCIAL", _("Міністерство соціальної політики України")),
    ("FINANCE", _("Міністерство фінансів України")),
    ("DSSZZI", _("Адміністрація Держспецзв’язку України")),
    ("NUCLEAR", _("Державна інспекція ядерного регулювання України")),
    ("REG_SERVICE", _("Державна регуляторна служба України")),
    ("FOOD_SAFETY", _("Держпродспоживслужба України")),
    ("FORESTRY", _("Держлісагентство України")),
    ("FISHERIES", _("Держрибагентство України")),
    ("EMERGENCY", _("ДСНС України")),
    ("ECO_INSPECTION", _("Державна екологічна інспекція України")),
    ("GEOLOGY", _("Державна служба геології та надр України")),
    ("AVIA", _("Державіаслужба України")),
    ("TRANSPORT", _("Укртрансбезпека")),
    ("CINEMA", _("Держкіно України")),
    ("EDU_QUALITY", _("Державна служба якості освіти України")),
    ("DRUG_CONTROL", _("Держлікслужба України")),
    ("DABI", _("ДАБІ України")),
    ("GEO_CADASTRE", _("Держгеокадастр України")),
    ("LABOR", _("Державна служба з питань праці")),
    ("PENSION", _("Пенсійний фонд України")),
    ("TAX", _("Державна фіскальна служба")),
    ("NCR_FIN", _("Нацкомфінпослуг")),
    ("NCR_EC", _("НКРЕКП")),
    ("NCSM", _("НКЦПФР")),
    ("SBU", _("Служба безпеки України")),
    ("ENERGY_SUPERV", _("Інспекція енергетичного нагляду України")),
    ("MINREGION", _("Міністерство розвитку громад та територій України")),
    ("SEA_RIVER_TRANSPORT", _("Морська адміністрація України")),
    ("NBU", _("Національний банк України")),
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



# =================== МОДЕЛЬ CLIENT ===================

class Client(models.Model):
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
    supervision_body = models.CharField(_("Орган нагляду"), max_length=255,
                                         choices=SUPERVISORY_BODY_CHOICES, blank=True, null=True)

    legal_form = models.CharField(_("Організаційно-правова форма"), max_length=255,
                                  choices=LEGAL_FORM_CHOICES, blank=True, null=True)

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
    audit_report_type = models.CharField(_("Вид аудиторського звіту"), max_length=255,
                                         choices=REPORT_TYPE_CHOICES, blank=True, null=True)

    audit_report_paragraph = models.CharField(_("Параграф аудиторського звіту"), max_length=255,
                                              choices=REPORT_PARAGRAPH_CHOICES, blank=True, null=True)

    supervision_notice_date = models.DateField(_("Дата повідомлення органу нагляду"), blank=True, null=True)

    cw_controls_done = models.BooleanField(_("Контрольні процедури в CW виконані"), default=False)

    # Години
    planned_hours = models.DecimalField(_("Робочі години (план)"), max_digits=10, decimal_places=2,
                                        blank=True, null=True)

    # Статус
    status = models.CharField(_("Статус"), max_length=50, default="new")

    # Команда
    manager = models.ForeignKey(User, verbose_name=_("Менеджер"),
                                on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="clients_as_manager")

    auditor = models.ForeignKey(User, verbose_name=_("Аудитор 1"),
                                on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="clients_as_auditor1")

    auditor2 = models.ForeignKey(User, verbose_name=_("Аудитор 2"),
                                 on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="clients_as_auditor2")

    auditor3 = models.ForeignKey(User, verbose_name=_("Аудитор 3"),
                                 on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="clients_as_auditor3")

    assistant = models.ForeignKey(User, verbose_name=_("Асистент 1"),
                                  on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name="clients_as_assistant1")

    assistant2 = models.ForeignKey(User, verbose_name=_("Асистент 2"),
                                   on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="clients_as_assistant2")

    assistant3 = models.ForeignKey(User, verbose_name=_("Асистент 3"),
                                   on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="clients_as_assistant3")

    assistant4 = models.ForeignKey(User, verbose_name=_("Асистент 4"),
                                   on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="clients_as_assistant4")

    qa_manager = models.ForeignKey(User, verbose_name=_("Менеджер КК"),
                                   on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="clients_as_qa_manager")

    # Службова інформація
    created_at = models.DateTimeField(_("Створено"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Оновлено"), auto_now=True)

    def __str__(self):
        return self.name or f"Клієнт #{self.pk}"

class ClientDocument(models.Model):
    DOC_TYPE_CHOICES = [
        ("", "---------"),
        ("charter", "Установчий документ"),
        ("request", "Запит / лист"),
        ("agreement", "Договір"),
        ("other", "Інше"),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name=_("Клієнт"),
    )
    file = models.FileField(
        upload_to="client_docs/",
        verbose_name=_("Файл"),
    )
    original_name = models.CharField(
        _("Оригінальна назва"),
        max_length=255,
        blank=True,
        null=True,
    )
    doc_type = models.CharField(
        _("Тип документа"),
        max_length=50,
        choices=DOC_TYPE_CHOICES,
        blank=True,
        null=True,
    )
    custom_label = models.CharField(
        _("Мітка / примітка"),
        max_length=255,
        blank=True,
        null=True,
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Користувач, який завантажив"),
    )
    created_at = models.DateTimeField(
        _("Створено"),
        auto_now_add=True,
    )

    def __str__(self):
        return self.original_name or f"Документ #{self.pk}"
    
