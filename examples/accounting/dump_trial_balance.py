"""Write the trial balance on a date to a semicolon CSV: the balance of every general ledger account.

Run: python -m examples.accounting.dump_trial_balance [YYYY-MM-DD] (default: the end of this year).
Amounts use a comma as decimal separator. The file is local/trial_balance_<date>.csv.
Calls: one GLAccountBalance.
"""

import csv
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from yuki_sdk import GLAccountBalanceSet

from examples.auth.auth import get_cred

ON = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date(date.today().year, 12, 31)
OUTPUT = Path(f"local/trial_balance_{ON:%Y-%m-%d}.csv")


def amount(value) -> str:
    return format(value, "f").replace(".", ",")


yuki_cred = get_cred()

balances = GLAccountBalanceSet(yuki_cred)
balances.get(ON)
if balances.count == 0:
    print(f"No balances on {ON}")
    exit()

rows = []
for balance in sorted(balances, key=lambda b: b.code):
    value = balance.amount or Decimal("0")
    rows.append(
        {
            "code": balance.code,
            "description": balance.description or "",
            "balance_type": balance.balance_type or "",  # B balance sheet, W profit and loss
            "debit": amount(value) if value > 0 else "",
            "credit": amount(-value) if value < 0 else "",
            "balance": amount(value),
        }
    )

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter=";")
    writer.writeheader()
    writer.writerows(rows)
total = sum((b.amount or Decimal("0")) for b in balances)
print(f"{len(rows)} accounts on {ON} written to {OUTPUT.resolve()} (total {total})")
