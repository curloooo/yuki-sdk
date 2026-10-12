"""Lines of one general ledger account, in three variants.

Calls: GLAccountTransactions, GLAccountTransactionsAndContact, GLAccountTransactionsFiscal.
"""

from datetime import date

from yuki_sdk import GLAccountTransactionSet

from examples.auth.auth import get_cred

START = date(date.today().year, 1, 1)
END = date(date.today().year, 12, 31)
GL_ACCOUNT_CODE = "400000"

yuki_cred = get_cred()

lines = GLAccountTransactionSet(yuki_cred)
lines.get(GL_ACCOUNT_CODE, START, END)
print(f"{lines.count} lines on {GL_ACCOUNT_CODE}")
for line in lines[:5]:
    print(f"{line.date}  {line.amount}  {line.description}  type={line.transaction_type}  file={line.file_name}")

lines.get(GL_ACCOUNT_CODE, START, END, with_contact=True)
for line in lines[:5]:
    print(f"{line.date}  {line.amount}  contact={line.contact} ({line.contact_id})  project={line.project_code}")

lines.get(GL_ACCOUNT_CODE, START, END, fiscal=True)
print(f"{lines.count} lines in fiscal mode")
