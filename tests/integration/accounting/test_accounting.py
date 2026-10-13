from decimal import Decimal

from yuki_sdk import GLAccountBalanceSet, GLAccountTransactionSet, NetRevenue, OutstandingItemSet


def test_gl_account_balances(yuki_cred, administration_id, period):
    _, end = period
    commercial = GLAccountBalanceSet(yuki_cred, administration_id)
    commercial.get(end)
    fiscal = GLAccountBalanceSet(yuki_cred, administration_id)
    fiscal.get(end, fiscal=True)

    assert commercial and fiscal
    assert all(isinstance(row.amount, Decimal) for row in list(commercial) + list(fiscal))


def test_gl_account_transactions(yuki_cred, administration_id, period, transactions):
    start, end = period
    code = transactions[0].gl_account_code

    lines = GLAccountTransactionSet(yuki_cred, administration_id)
    lines.get(code, start, end, with_contact=True)

    assert lines
    assert all(line.gl_account_code in (None, code) for line in lines)


def test_net_revenue(yuki_cred, administration_id, period):
    start, end = period
    revenue = NetRevenue(yuki_cred, administration_id)
    revenue.get(start, end)

    assert revenue.amount is not None


def test_outstanding_items(yuki_cred, administration_id):
    debtors = OutstandingItemSet(yuki_cred, administration_id)
    debtors.get_debtors_with_language()
    creditors = OutstandingItemSet(yuki_cred, administration_id)
    creditors.get_creditors()

    for item in list(debtors) + list(creditors):
        assert item.id or item.reference
        assert isinstance(item.open_amount, Decimal)
