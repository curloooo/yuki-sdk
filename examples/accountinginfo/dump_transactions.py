"""Write every general ledger line of the period to a semicolon CSV.

Amounts use a comma as decimal separator. The file is local/transactions.csv.
Calls: one GetTransactions per page of 100 lines.
"""

import csv
from datetime import date
from pathlib import Path

from yuki_sdk import FinancialMode, TransactionSet

from examples.auth.auth import get_cred

START = date(date.today().year, 1, 1)
END = date(date.today().year, 12, 31)
OUTPUT = Path("local/transactions.csv")


def text(value) -> str:
    return "" if value is None else str(value)


def amount(value) -> str:
    return "" if value is None else format(value, "f").replace(".", ",")


yuki_cred = get_cred()

transactions = TransactionSet(yuki_cred)
transactions.get(START, END, financial_mode=FinancialMode.COMMERCIAL)
if transactions.count == 0:
    print(f"No transactions in {START}..{END}")
    exit()

rows = []
for transaction in transactions:
    contact = transaction.contact
    document = transaction.document
    rows.append(
        {
            "id": transaction.id,
            "hid": text(transaction.hid),
            "date": text(transaction.date),
            "description": text(transaction.description),
            "amount": amount(transaction.amount),
            "gl_account_code": text(transaction.gl_account_code),
            "contact": text(contact and contact.full_name),
            "contact_id": text(contact and contact.id),
            "contact_vat_number": text(contact and contact.vat_number),
            "document_id": text(document and document.id),
            "document_reference": text(document and document.reference),
            "document_type": text(document and document.type),
            "document_folder_id": text(document and document.folder_id),
            "matched_date": text(transaction.matched_date),
            "currency": text(transaction.currency),
            "amount_currency": amount(transaction.amount_currency),
            "vat_code": text(transaction.vat_code_type),
            "vat_percentage": amount(transaction.vat_percentage),
            "project_code": text(transaction.project_code),
        }
    )

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter=";")
    writer.writeheader()
    writer.writerows(rows)
print(f"{len(rows)} transactions written to {OUTPUT.resolve()}")
