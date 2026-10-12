"""All contacts of the domain, every page. This includes the administration itself and Yuki's own contacts.

Calls: one SearchContacts per page of 100 contacts.
"""

from yuki_sdk import ContactSet

from examples.auth.auth import get_cred

yuki_cred = get_cred()

contacts = ContactSet(yuki_cred)
contacts.get()
print(f"{contacts.count} contacts")
for contact in contacts[:5]:
    print(f"{contact.hid}  {contact.code}  {contact.name}  type={contact.type}  customer={contact.is_customer} supplier={contact.is_supplier}")
    print(f"    {contact.address_line_1}, {contact.postcode} {contact.city} {contact.country}")
    print(f"    vat={contact.vat_number}  iban={contact.iban}  email={contact.email_work or contact.email_home}  phone={contact.phone_work}")
    print(f"    modified={contact.modified}  tags={contact.tags}")
