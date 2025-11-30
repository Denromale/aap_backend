# import_clients.py
import csv
from decimal import Decimal
from datetime import datetime

from django.db import transaction
from core.models import Client

CSV_PATH = "clients.csv"


def cut(value, max_len=90):
    """
    Режем строки до max_len символов,
    чтобы не вылетать по ограничению varchar(100/150) в БД.
    """
    if value is None:
        return ""
    v = str(value).strip()
    return v[:max_len]


def parse_decimal(value):
    if not value:
        return None
    v = str(value).strip().replace(" ", "").replace(",", ".")
    try:
        return Decimal(v)
    except Exception:
        return None


def parse_bool(value):
    if not value:
        return False
    v = str(value).strip().lower()
    return v in ("1", "true", "yes", "y", "так", "да", "oui")


def parse_date(value):
    if not value:
        return None
    v = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    return None


def run():
    count_created = 0
    rows_total = 0
    rows_without_edrpou = 0

    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        first_line = f.readline()
        delimiter = ";"
        if "," in first_line and first_line.count(",") > first_line.count(";"):
            delimiter = ","

        f.seek(0)
        reader = csv.DictReader(f, delimiter=delimiter)

        print("Fieldnames из файла:", reader.fieldnames)
        print("Используем разделитель:", repr(delimiter))

        with transaction.atomic():
            for row in reader:
                rows_total += 1

                edrpou = (row.get("edrpou") or "").strip()
                if not edrpou:
                    rows_without_edrpou += 1
                    if rows_without_edrpou <= 5:
                        print("Строка без edrpou:", row)
                    # ВАЖНО: ты говорил, что такие строки тоже важны —
                    # если нужно, можем тут придумать псевдо-ID.
                    # Пока просто пропускаем:
                    continue

                client = Client(
                    name=cut(row.get("name")),
                    edrpou=edrpou,

                    address_country=cut(row.get("address_country")),
                    address_city=cut(row.get("address_city")),
                    address_street=cut(row.get("address_street")),
                    address_building=cut(row.get("address_building")),
                    address_office=cut(row.get("address_office")),
                    address_zip=cut(row.get("address_zip")),
                    kved=cut(row.get("kved")),
                    # poi не трогаем, т.к. в CSV он не bool
                    # poi=parse_bool(row.get("poi")),

                    requisites_number=cut(row.get("requisites_number")),
                    requisites_date=parse_date(row.get("requisites_date")),
                    requisites_amount=parse_decimal(row.get("requisites_amount")),
                    requisites_vat=parse_decimal(row.get("requisites_vat")),

                    supervision_body=cut(row.get("supervision_body")),
                    legal_form=cut(row.get("legal_form")),
                    mandatory_audit=parse_bool(row.get("mandatory_audit")),
                    reporting_period=cut(row.get("reporting_period")),
                    contract_deadline=parse_date(row.get("contract_deadline")),
                    engagement_subject=cut(row.get("engagement_subject")),

                    authorized_person_name=cut(row.get("authorized_person_name")),
                    authorized_person_email=cut(row.get("authorized_person_email")),

                    audit_report_number=cut(row.get("audit_report_number")),
                    audit_report_date=parse_date(row.get("audit_report_date")),
                    audit_report_type=cut(row.get("audit_report_type")),
                    audit_report_paragraph=cut(row.get("audit_report_paragraph")),

                    supervision_notice_date=parse_date(row.get("supervision_notice_date")),
                    cw_controls_done=parse_bool(row.get("cw_controls_done")),

                    status=cut(row.get("status")),
                    planned_hours=parse_decimal(row.get("planned_hours")),

                    manager_username=cut(row.get("manager_username"), 150),
                    auditor_username=cut(row.get("auditor_username"), 150),
                    auditor2_username=cut(row.get("auditor2_username"), 150),
                    auditor3_username=cut(row.get("auditor3_username"), 150),
                    assistant_username=cut(row.get("assistant_username"), 150),
                    assistant2_username=cut(row.get("assistant2_username"), 150),
                    assistant3_username=cut(row.get("assistant3_username"), 150),
                    assistant4_username=cut(row.get("assistant4_username"), 150),
                    qa_manager_username=cut(row.get("qa_manager_username"), 150),
                )

                client.save()
                count_created += 1

    print("Импорт завершён.")
    print("Всего строк в файле:", rows_total)
    print("Строк без edrpou:", rows_without_edrpou)
    print("Создано (новых Client):", count_created)
