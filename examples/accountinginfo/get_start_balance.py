"""Opening balance per general ledger account, fiscal and commercial.

Calls: GetStartBalanceByGlAccount twice.
"""

from datetime import date

from yuki_sdk import FinancialMode, StartBalanceSet

from examples.auth.auth import get_cred

YEAR = date.today().year

yuki_cred = get_cred()

fiscal = StartBalanceSet(yuki_cred)
fiscal.get(YEAR)
print(f"{fiscal.count} accounts with a fiscal start balance in {YEAR}")
for balance in fiscal[:10]:
    print(f"{balance.gl_account_code}  {balance.start_balance}  (sent as {balance.start_balance_text!r})  {balance.description}")

commercial = StartBalanceSet(yuki_cred)
commercial.get(YEAR, financial_mode=FinancialMode.COMMERCIAL)
fiscal_by_code = {balance.gl_account_code: balance.start_balance for balance in fiscal}
different = [b.gl_account_code for b in commercial if fiscal_by_code.get(b.gl_account_code) != b.start_balance]
print(f"{len(different)} accounts differ between fiscal and commercial: {different[:10]}")
