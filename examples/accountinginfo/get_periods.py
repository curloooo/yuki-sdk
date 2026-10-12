"""Start and end of a financial year, and when it last changed.

Calls: GetPeriodDateTable, GetFinancialYearModifiedDate.
"""

from datetime import date

from yuki_sdk import Period

from examples.auth.auth import get_cred

YEAR = date.today().year

yuki_cred = get_cred()

period = Period(yuki_cred)
period.get(YEAR)
print(f"financial year {YEAR} of {period.name}: {period.start} .. {period.end}")
print(f"last modified: {period.modified()}")
