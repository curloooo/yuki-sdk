"""Open supplier items: now, on a date, and with payment reference.

Calls: OutstandingCreditorItems, OutstandingCreditorItemsByDateOutstanding,
OutstandingCreditorWithPaymentReference.
"""

from datetime import date

from yuki_sdk import OutstandingItemSet

from examples.auth.auth import get_cred

START = date(date.today().year, 1, 1)
END = date(date.today().year, 12, 31)

yuki_cred = get_cred()

items = OutstandingItemSet(yuki_cred)
items.get_creditors(include_bank_transactions=True)
print(f"{items.count} open supplier items (bank transactions included)")
for item in items[:5]:
    print(f"{item.date}  {item.contact}  open={item.open_amount}/{item.original_amount}  ref={item.reference}  type={item.item_type}")

items.get_creditors(outstanding_on=END)
print(f"{items.count} items were open on {END}")

items.get_creditors_with_payment_reference(START, END)
for item in items[:3]:
    print(f"  {item.reference}  payment reference={item.payment_reference}")
