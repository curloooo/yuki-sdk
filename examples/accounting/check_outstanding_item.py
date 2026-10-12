"""Look up an open item by its reference.

Calls: OutstandingDebtorItems (to find a reference), CheckOutstandingItemAdmin.
"""

from yuki_sdk import OutstandingItemSet

from examples.auth.auth import get_cred

yuki_cred = get_cred()

items = OutstandingItemSet(yuki_cred)
items.get_debtors()
reference = next((item.reference for item in items if item.reference), None)
if reference is None:
    print("No open customer item with a reference")
    exit()

items.check(reference)
for item in items:
    print(f"{item.reference}  {item.contact}  open={item.open_amount}")
