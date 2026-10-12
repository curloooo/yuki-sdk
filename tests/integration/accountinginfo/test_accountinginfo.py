from datetime import date
from decimal import Decimal

from yuki_sdk import AccountingInfoService, FinancialMode, GLAccountSet


def test_gl_account_scheme(yuki_cred, administration_id, transactions):
    accounts = GLAccountSet(yuki_cred, administration_id)
    accounts.get()

    assert accounts.count
    codes = {account.code for account in accounts}
    assert all(account.description for account in accounts)
    # Every account used in the ledger is in the scheme.
    assert {row.gl_account_code for row in transactions} <= codes


def test_transactions_first_page(transactions, period):
    start, end = period

    for row in transactions:
        assert row.id
        assert start <= row.date <= end
        assert isinstance(row.amount, Decimal)
        assert row.gl_account_code
    # Requested data groups come back filled on at least some lines.
    assert any(row.document for row in transactions)
    assert any(row.contact for row in transactions)


def test_transactions_pages_do_not_overlap(yuki_cred, administration_id, period, transactions):
    if len(transactions) < 100:
        return
    start, end = period
    second = AccountingInfoService(yuki_cred).transactions(administration_id, start, end, number_of_records=100, start_record=100)

    assert not {row.id for row in transactions} & {row.id for row in second}


def test_transaction_details(yuki_cred, administration_id, period, transactions):
    start, end = period
    code = transactions[0].gl_account_code
    details = AccountingInfoService(yuki_cred).transaction_details(administration_id, start, end, gl_account_code=code)

    assert details
    assert all(detail.gl_account_code in (None, code) for detail in details)


def test_period_and_modified_date(yuki_cred, administration_id, year):
    service = AccountingInfoService(yuki_cred)

    period = service.period_date_table(administration_id, year)
    assert period.period is None or isinstance(period.period, date)
    service.financial_year_modified_date(administration_id, year)


def test_start_balance(yuki_cred, administration_id, year):
    balances = AccountingInfoService(yuki_cred).start_balance_by_gl_account(administration_id, year, financial_mode=FinancialMode.FISCAL)

    for balance in balances:
        assert balance.gl_account_code
        # The amount is text in the WSDL; it must still parse.
        assert balance.start_balance_text is None or balance.start_balance is not None


def test_transaction_document(yuki_cred, administration_id, transactions):
    row = next(row for row in transactions if row.document)
    document = AccountingInfoService(yuki_cred).transaction_document(administration_id, row.id)

    assert document.data is None or isinstance(document.data, bytes)


def test_contact_default_values(yuki_cred, administration_id, transactions):
    contact_id = next((row.contact.id for row in transactions if row.contact and row.contact.id), None)
    if contact_id is None:
        return
    for defaults in AccountingInfoService(yuki_cred).contact_default_values(administration_id, contact_id):
        assert defaults.contact_id in (None, contact_id)


def test_payment_methods_projects_and_rgs(yuki_cred, administration_id):
    service = AccountingInfoService(yuki_cred)

    assert all(method.description for method in service.custom_payment_methods(administration_id))
    assert all(project.id for project in service.projects(administration_id))
    service.rgs_scheme(administration_id)
