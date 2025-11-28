import csv
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from core.models import Client


def parse_bool(val):
    """
    Преобразует строку в булево.
    Ожидаем TRUE/FALSE, 1/0, yes/no, так/ні и т.п.
    """
    if val is None:
        return False
    s = str(val).strip().lower()
    return s in ("true", "1", "t", "yes", "y", "так", "истина")


def parse_decimal(val, field_name):
    """
    Преобразуем значение в Decimal или возвращаем None.
    Если формат некорректный — кидаем ошибку, чтобы заметить проблему в CSV.
    """
    if val is None or str(val).strip() == "":
        return None
    s = str(val).replace(",", ".").strip()
    try:
        return Decimal(s)
    except InvalidOperation:
        raise CommandError(f"Не могу преобразовать значение '{val}' поля '{field_name}' в число.")


class Command(BaseCommand):
    help = "Импорт клиентов из CSV-файла"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Путь к CSV-файлу")

    def handle(self, *args, **options):
        csv_path = options["csv_path"]

        try:
            with open(csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                count = 0

                for row in reader:
                    # --- Основные числовые/булевы поля ---
                    poi = parse_bool(row.get("poi"))
                    mandatory_audit = parse_bool(row.get("mandatory_audit"))
                    cw_controls_done = parse_bool(row.get("cw_controls_done"))

                    requisites_amount = parse_decimal(row.get("requisites_amount"), "requisites_amount")
                    requisites_vat = parse_decimal(row.get("requisites_vat"), "requisites_vat")
                    planned_hours = parse_decimal(row.get("planned_hours"), "planned_hours")

                    # --- Создаём объект клиента (без ролей) ---
                    client = Client(
                        name=row.get("name") or "",
                        edrpou=row.get("edrpou") or "",

                        address_country=row.get("address_country") or "",
                        address_city=row.get("address_city") or "",
                        address_street=row.get("address_street") or "",
                        address_building=row.get("address_building") or "",
                        address_office=row.get("address_office") or "",
                        address_zip=row.get("address_zip") or "",

                        kved=row.get("kved") or "",
                        poi=poi,

                        requisites_number=row.get("requisites_number") or "",
                        requisites_date=row.get("requisites_date") or None,
                        requisites_amount=requisites_amount,
                        requisites_vat=requisites_vat,

                        supervision_body=row.get("supervision_body") or "",
                        legal_form=row.get("legal_form") or "",
                        mandatory_audit=mandatory_audit,

                        reporting_period=row.get("reporting_period") or "",
                        contract_deadline=row.get("contract_deadline") or None,

                        engagement_subject=row.get("engagement_subject") or "",

                        authorized_person_name=row.get("authorized_person_name") or "",
                        authorized_person_email=row.get("authorized_person_email") or "",

                        audit_report_number=row.get("audit_report_number") or "",
                        audit_report_date=row.get("audit_report_date") or None,
                        audit_report_type=row.get("audit_report_type") or "",
                        audit_report_paragraph=row.get("audit_report_paragraph") or "",
                        supervision_notice_date=row.get("supervision_notice_date") or None,
                        cw_controls_done=cw_controls_done,

                        status=row.get("status") or "",
                        planned_hours=planned_hours,
                    )

                    # --- Привязка пользователей по username ---

                    def get_user(field_name):
                        username = (row.get(field_name) or "").strip()
                        if not username:
                            return None
                        try:
                            return User.objects.get(username=username)
                        except User.DoesNotExist:
                            raise CommandError(
                                f"Пользователь с username='{username}' "
                                f"(из колонки '{field_name}') не найден. "
                                f"Создайте его заранее через админку."
                            )

                    client.manager = get_user("manager_username")
                    client.auditor = get_user("auditor_username")
                    client.auditor2 = get_user("auditor2_username")
                    client.auditor3 = get_user("auditor3_username")

                    client.assistant = get_user("assistant_username")
                    client.assistant2 = get_user("assistant2_username")
                    client.assistant3 = get_user("assistant3_username")
                    client.assistant4 = get_user("assistant4_username")

                    client.qa_manager = get_user("qa_manager_username")

                    client.save()
                    count += 1

                self.stdout.write(self.style.SUCCESS(f"Импортировано клиентов: {count}"))

        except FileNotFoundError:
            raise CommandError(f"Файл не найден: {csv_path}")
