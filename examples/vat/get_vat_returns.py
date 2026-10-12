"""Filed VAT returns of a year.

Calls: VATReturnList.
"""

from datetime import date

from yuki_sdk import VATReturnSet

from examples.auth.auth import get_cred

YEAR = date.today().year

yuki_cred = get_cred()

returns = VATReturnSet(yuki_cred)
returns.get(YEAR)
print(f"{returns.count} VAT returns in {YEAR}")
for vat_return in returns:
    print(f"{vat_return.start_date}..{vat_return.end_date}  {vat_return.status}  sent={vat_return.send_date}  document={vat_return.document_id}")
