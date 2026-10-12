"""Invoices as listed in a screen of the Yuki web app (here: all sales invoices).

Calls: FindInvoices. No search document is passed, so the call sends an empty
argXML element. Yuki rejects the call when that parameter is missing.
"""

from yuki_sdk import InvoiceMode, UblService

from examples.auth.auth import get_cred

yuki_cred = get_cred()

result = UblService(yuki_cred).find_invoices(yuki_cred.admin_id, InvoiceMode.SALES_ALL_INVOICES)
print(str(result)[:1000])
