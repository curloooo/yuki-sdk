"""Balance per general ledger account on a date: commercial, fiscal and at year end.

Calls: GLAccountBalance, GLAccountBalanceFiscal, GLAccountBalanceYearEnd.
"""

from datetime import date

from yuki_sdk import GLAccountBalanceSet

from examples.auth.auth import get_cred

END = date(date.today().year, 12, 31)

yuki_cred = get_cred()

commercial = GLAccountBalanceSet(yuki_cred)
commercial.get(END)
print(f"{commercial.count} accounts with a commercial balance on {END}")
for balance in commercial[:10]:
    print(f"{balance.code}  {balance.balance_type}  {balance.amount}  {balance.description}")

fiscal = GLAccountBalanceSet(yuki_cred)
fiscal.get(END, fiscal=True)
by_code = {balance.code: balance.amount for balance in commercial}
print(f"{sum(1 for b in fiscal if by_code.get(b.code) != b.amount)} accounts differ in fiscal mode")

year_end = GLAccountBalanceSet(yuki_cred)
year_end.get_year_end(END)
print(f"{year_end.count} accounts in the year-end balance")
