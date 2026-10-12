"""The file behind one general ledger line, written to local/downloads/.

Calls: GetTransactions (one page), GetTransactionDocument.
"""

from datetime import date
from pathlib import Path

from yuki_sdk import TransactionDocument, TransactionSet

from examples.auth.auth import get_cred

START = date(date.today().year, 1, 1)
END = date(date.today().year, 12, 31)

yuki_cred = get_cred()

transactions = TransactionSet(yuki_cred)
transactions.get_page(START, END, number_of_records=10)
transaction = next((t for t in transactions if t.document), None)
if transaction is None:
    print("No transaction with a document on the first page")
    exit()

document = TransactionDocument(yuki_cred)
document.get(transaction.id)
print(f"transaction {transaction.id}: file={document.file_name} bytes={len(document.data or b'')}")
if document.data:
    target = Path("local/downloads") / (document.file_name or f"{transaction.id}.bin")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(document.data)
    print(f"written to {target.resolve()}")
