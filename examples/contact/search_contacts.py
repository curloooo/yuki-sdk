"""Search contacts by VAT number, by Yuki id, or changed since a date.

Calls: SearchContacts three times (one page each).
"""

from datetime import datetime

from yuki_sdk import ContactSet
from src.contact import ContactSearchOption, ContactSortOrder

from examples.auth.auth import get_cred

yuki_cred = get_cred()

contacts = ContactSet(yuki_cred)
contacts.search("BE0", search_option=ContactSearchOption.VAT_NUMBER)
print(f"{contacts.count} contacts with a Belgian VAT number on the first page")
for contact in contacts[:5]:
    print(f"{contact.name}  {contact.vat_number}")

if contacts.count:
    by_id = ContactSet(yuki_cred)
    by_id.read([contacts[0].id])
    print(f"read by id: {by_id[0].name}")

contacts.search("", search_option=ContactSearchOption.ALL, sort_order=ContactSortOrder.MODIFIED_DESC, modified_after=datetime(datetime.now().year, 1, 1))
print(f"{contacts.count} contacts changed this year on the first page")
