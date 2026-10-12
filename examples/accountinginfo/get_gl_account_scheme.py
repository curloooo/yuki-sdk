"""The chart of accounts of the administration.

Calls: GetGLAccountScheme.
"""

from yuki_sdk import GLAccountSet

from examples.auth.auth import get_cred

yuki_cred = get_cred()

accounts = GLAccountSet(yuki_cred)
accounts.get()
print(f"{accounts.count} general ledger accounts")
for account in accounts[:10]:
    print(f"{account.code}  type={account.account_type}/{account.subtype}  enabled={account.is_enabled}  {account.description}")
    print(f"    nl={account.description_nl}  fr={account.description_fr}  en={account.description_en}")
    print(f"    vat={account.is_vat_applicable}  deductible={account.deductible_vat_percentage}  professional={account.professional_percentage}")

# find() looks in the filled set; it does not call Yuki. It raises YukiError for an unknown code.
if accounts.count:
    print(accounts.find(accounts[0].code))
