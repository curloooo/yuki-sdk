"""Booking defaults Yuki stores per contact: account, VAT code, payment term, bank account.

Calls: GetContactDefaultValues (plus one GetTransactions page when no contact is given).
"""

from datetime import date

from yuki_sdk import ContactDefaultValueSet, TransactionSet

from examples.auth.auth import get_cred

START = date(date.today().year, 1, 1)
END = date(date.today().year, 12, 31)
CONTACT_ID = None  # a Yuki contact id; None takes the first one found

yuki_cred = get_cred()

contact_id = CONTACT_ID
if contact_id is None:
    transactions = TransactionSet(yuki_cred)
    transactions.get_page(START, END, number_of_records=10)
    contact_id = next((t.contact.id for t in transactions if t.contact and t.contact.id), None)
if contact_id is None:
    print("No contact found on the first transaction page")
    exit()

defaults = ContactDefaultValueSet(yuki_cred)
defaults.get(contact_id)
for contact_defaults in defaults:
    print(f"{contact_defaults.contact_name}  default bank account={contact_defaults.default_bank_account}")
    for value in contact_defaults.default_values:
        print(f"  {value.document_type}  account={value.gl_account}  vat={value.vat_code}  method={value.payment_method}  term={value.payment_term}  {value.text}")
