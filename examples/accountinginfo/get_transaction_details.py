"""Lines with period, company and the user who booked them.

Calls: GetTransactionDetails.
"""

from datetime import date

from yuki_sdk import TransactionDetailSet

from examples.auth.auth import get_cred

START = date(date.today().year, 1, 1)
END = date(date.today().year, 12, 31)
GL_ACCOUNT_CODE = "400000"

yuki_cred = get_cred()

details = TransactionDetailSet(yuki_cred)
details.get(START, END, gl_account_code=GL_ACCOUNT_CODE)
print(f"{details.count} transaction details on {GL_ACCOUNT_CODE}")
for detail in details[:5]:
    print(f"{detail.date}  {detail.amount}  hid={detail.hid}  period={detail.period_id}  {detail.description}")
    print(f"    contact={detail.full_name} ({detail.contact_code})  document={detail.document_id} {detail.document_reference}")
    print(f"    tax={detail.tax_code_description}  project={detail.project_code}  booked_by={detail.mutation_user}")
