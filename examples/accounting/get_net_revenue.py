"""Net revenue of a period, commercial and fiscal.

Calls: NetRevenue, NetRevenueFiscal.
"""

from datetime import date

from yuki_sdk import NetRevenue

from examples.auth.auth import get_cred

START = date(date.today().year, 1, 1)
END = date(date.today().year, 12, 31)

yuki_cred = get_cred()

revenue = NetRevenue(yuki_cred)
revenue.get(START, END)
print(f"net revenue {START}..{END}: {revenue.amount}")

revenue.get(START, END, fiscal=True)
print(f"fiscal: {revenue.amount}")
