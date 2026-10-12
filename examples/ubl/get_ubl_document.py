"""The UBL XML of an invoice. GetUBLDocument takes the archive document id of the invoice.

Calls: GetTransactions (one page) when no document is given, then GetUBLDocument.
"""

from datetime import date

from yuki_sdk import Document, TransactionSet

from examples.auth.auth import get_cred

START = date(date.today().year, 1, 1)
END = date(date.today().year, 12, 31)
DOCUMENT_ID = None  # a Yuki document id; None takes the first invoice on the first transaction page

yuki_cred = get_cred()

document_id = DOCUMENT_ID
if document_id is None:
    transactions = TransactionSet(yuki_cred)
    transactions.get_page(START, END, number_of_records=10)
    document_id = next((t.document.id for t in transactions if t.document and t.document.type == "6"), None)
if document_id is None:
    print("No sales invoice on the first transaction page")
    exit()

ubl = Document(yuki_cred, id=document_id).ubl()
print(f"{len(ubl or '')} characters of UBL")
print((ubl or "")[:500])
