"""Open customer items: now, on a date, with language and with payment reference.

Calls: OutstandingDebtorItems, OutstandingDebtorItemsByDateOutstanding,
OutstandingDebtorItemsWithLanguage, OutstandingDebtorWithPaymentReference.
"""

from datetime import date

from yuki_sdk import OutstandingItemSet

from examples.auth.auth import get_cred

START = date(date.today().year, 1, 1)
END = date(date.today().year, 12, 31)

yuki_cred = get_cred()

items = OutstandingItemSet(yuki_cred)
items.get_debtors()
print(f"{items.count} open customer items")
for item in items[:5]:
    print(f"{item.date}  {item.contact}  open={item.open_amount}/{item.original_amount}  ref={item.reference}  due={item.due_date}  document={item.document_id}")

items.get_debtors(outstanding_on=END)
print(f"{items.count} items were open on {END}")

items.get_debtors_with_language()
print(f"languages: {sorted({item.language for item in items if item.language})}")
for item in items[:3]:
    print(f"  {item.contact}  {item.address_line_1}, {item.postcode} {item.city}  mail: {item.mail_address_line_1}, {item.mail_postcode} {item.mail_city}")

items.get_debtors_with_payment_reference(START, END)
for item in items[:3]:
    print(f"  {item.reference}  payment reference={item.payment_reference}  method={item.payment_method}")
