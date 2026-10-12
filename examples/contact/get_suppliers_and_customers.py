"""Customers and suppliers, also inactive ones, every page.

Calls: one GetSuppliersAndCustomers per page of 100, per role.
"""

from yuki_sdk import ContactSet

from examples.auth.auth import get_cred

yuki_cred = get_cred()

customers = ContactSet(yuki_cred)
customers.get_customers()
print(f"{customers.count} customers")
for contact in customers[:5]:
    print(f"{contact.hid}  {contact.name}  {contact.vat_number}")

suppliers = ContactSet(yuki_cred)
suppliers.get_suppliers()
print(f"{suppliers.count} suppliers")
