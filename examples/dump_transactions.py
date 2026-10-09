"""Write all general-ledger transactions for the year to a semicolon CSV.

Amounts use a comma as the decimal separator. The file is written in the
current directory as ``transactions.csv``.
"""

import csv
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from src import AccountingInfoService

from examples.auth.auth import get_cred
from examples.sample_ids import ADMINISTRATION_ID, DOMAIN_ID

START = date(date.today().year, 1, 1)
END = date.today()
PAGE_SIZE = 100
OUTPUT = Path("transactions.csv")
DATA_GROUPS = "contact,document,documentProcessed,documentMatched,foreignCurrency,vat,project"

COLUMNS = (
    "id",
    "hid",
    "date",
    "description",
    "amount",
    "gl_account_code",
    "contact",
    "contact_id",
    "contact_code",
    "contact_vat_number",
    "contact_coc_number",
    "contact_postcode",
    "contact_country",
    "document_id",
    "document_reference",
    "document_type",
    "document_folder",
    "currency",
    "amount_currency",
    "exchange_rate",
    "vat_code",
    "vat_description",
    "vat_percentage",
    "project_code",
    "project_description",
)


def main() -> None:
    credentials = get_cred()
    credentials.set_domain_id(DOMAIN_ID)
    service = AccountingInfoService(credentials)
    rows = list(_transactions(service))
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} transactions written to {OUTPUT.resolve()}")


def _transactions(service: AccountingInfoService):
    seen: set[str] = set()
    start_record = 0
    while True:
        page = service.invoke(
            "GetTransactions",
            administrationID=ADMINISTRATION_ID,
            glAccountCode="",
            startDate=_as_datetime(START),
            endDate=_as_datetime(END),
            financialMode=0,
            dataGroups=DATA_GROUPS,
            numberOfRecords=PAGE_SIZE,
            startRecord=start_record,
        )
        if not page:
            return
        fresh = [row for row in page if row["id"] not in seen]
        if not fresh:
            return
        for row in fresh:
            seen.add(row["id"])
            yield _row(row)
        if len(page) < PAGE_SIZE:
            return
        start_record += len(page)


def _row(transaction) -> dict[str, str]:
    contact = transaction["contact"]
    document = transaction["document"]
    currency = transaction["foreignCurrency"]
    vat = transaction["vat"]
    project = transaction["project"]
    return {
        "id": _text(transaction["id"]),
        "hid": _text(transaction["hID"]),
        "date": _date(transaction["transactionDate"]),
        "description": _text(transaction["description"]),
        "amount": _decimal(transaction["amount"]),
        "gl_account_code": _text(transaction["glAccountCode"]),
        "contact": _text(_get(contact, "fullName")),
        "contact_id": _text(_get(contact, "id")),
        "contact_code": _text(_get(contact, "contactCode")),
        "contact_vat_number": _text(_get(contact, "VATNumber")),
        "contact_coc_number": _text(_get(contact, "CoCNumber")),
        "contact_postcode": _text(_get(contact, "zipCode")),
        "contact_country": _text(_get(contact, "country")),
        "document_id": _text(_get(document, "id")),
        "document_reference": _text(_get(document, "reference")),
        "document_type": _text(_get(document, "typeDescription")),
        "document_folder": _text(_get(document, "folder")),
        "currency": _text(_get(currency, "currency")),
        "amount_currency": _decimal(_get(currency, "amountFC")),
        "exchange_rate": _decimal(_get(currency, "rate")),
        "vat_code": _text(_get(vat, "codeType")),
        "vat_description": _text(_get(vat, "codeDescription")),
        "vat_percentage": _decimal(_get(vat, "codePercentage")),
        "project_code": _text(_get(project, "code")),
        "project_description": _text(_get(project, "description")),
    }


def _get(value, name: str):
    if value is None:
        return None
    return value[name]


def _text(value) -> str:
    if value is None:
        return ""
    return str(value)


def _decimal(value) -> str:
    if value is None:
        return ""
    return format(Decimal(value), "f").replace(".", ",")


def _date(value) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return _text(value)


def _as_datetime(value: date) -> datetime:
    return datetime(value.year, value.month, value.day)


if __name__ == "__main__":
    main()
