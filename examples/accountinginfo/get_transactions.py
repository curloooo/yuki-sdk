"""General ledger lines of a period, with contact, document, matching, currency, VAT and project.

Calls: one GetTransactions per page of 100 lines.
"""

from datetime import date

from yuki_sdk import FinancialMode, TransactionSet

from examples.auth.auth import get_cred

START = date(date.today().year, 1, 1)
END = date(date.today().year, 12, 31)

yuki_cred = get_cred()

# Every page
transactions = TransactionSet(yuki_cred)
transactions.get(START, END)
print(f"{transactions.count} transactions in {START}..{END}")
for transaction in transactions[:5]:
    print(f"{transaction.date}  {transaction.gl_account_code}  {transaction.amount}  hid={transaction.hid}  {transaction.description}")
    if transaction.contact:
        print(f"    contact: {transaction.contact.full_name}  code={transaction.contact.contact_code}  vat={transaction.contact.vat_number}")
    if transaction.document:
        document = transaction.document
        print(f"    document: {document.id}  ref={document.reference}  type={document.type}  folder={document.folder_id}/{document.folder_tab_id}")
    print(f"    processed={transaction.processed_date}  matched={transaction.matched_date}  by={transaction.matched_by}")
    print(f"    currency={transaction.currency} {transaction.amount_currency} @ {transaction.currency_rate}")
    print(f"    vat={transaction.vat_code_type} {transaction.vat_percentage}%  project={transaction.project_code}")

if transactions.count == 0:
    exit()

# Commercial instead of fiscal, one account, first page only
on_account = TransactionSet(yuki_cred)
on_account.get_page(START, END, gl_account_code=transactions[0].gl_account_code, financial_mode=FinancialMode.COMMERCIAL)
print(f"{on_account.count} commercial transactions on {transactions[0].gl_account_code}")
