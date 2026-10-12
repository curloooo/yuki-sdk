"""The VAT codes active in the administration. A type is not unique: key on type and percentage.

Calls: ActiveVATCodesList.
"""

from yuki_sdk import VATCodeSet

from examples.auth.auth import get_cred

yuki_cred = get_cred()

codes = VATCodeSet(yuki_cred)
codes.get()
print(f"{codes.count} active VAT codes")
for code in codes:
    print(f"type={code.type}  {code.percentage}%  {code.description}  ({code.type_description})  {code.country}  {code.start_date}..{code.end_date}")
