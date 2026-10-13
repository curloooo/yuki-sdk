"""Invoices as listed in a screen of the Yuki web app (here: all sales invoices).

Calls: FindInvoices. No search document is passed, so the call sends an empty
argXML element. Yuki rejects the call when that parameter is missing.
"""

from yuki_sdk import FoundInvoices, InvoiceMode

from examples.auth.auth import get_cred

yuki_cred = get_cred()

invoices = FoundInvoices(yuki_cred)
invoices.get(InvoiceMode.SALES_ALL_INVOICES)
print(str(invoices.data)[:1000])
