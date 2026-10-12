from decimal import Decimal

from yuki_sdk import AccountingService


def test_gl_account_balances(yuki_cred, administration_id, period):
    service = AccountingService(yuki_cred)
    _, end = period

    commercial = service.gl_account_balance(administration_id, end)
    fiscal = service.gl_account_balance_fiscal(administration_id, end)

    assert commercial and fiscal
    assert all(isinstance(row.amount, Decimal) for row in commercial + fiscal)


def test_gl_account_transactions(yuki_cred, administration_id, period, transactions):
    start, end = period
    code = transactions[0].gl_account_code

    lines = AccountingService(yuki_cred).gl_account_transactions_and_contact(administration_id, code, start, end)

    assert lines
    assert all(line.gl_account_code in (None, code) for line in lines)


def test_net_revenue(yuki_cred, administration_id, period):
    start, end = period

    assert AccountingService(yuki_cred).net_revenue(administration_id, start, end) is not None


def test_outstanding_items(yuki_cred, administration_id):
    service = AccountingService(yuki_cred)

    debtors = service.outstanding_debtor_items_with_language(administration_id)
    creditors = service.outstanding_creditor_items(administration_id)

    for item in debtors + creditors:
        assert item.id or item.reference
        assert isinstance(item.open_amount, Decimal)
