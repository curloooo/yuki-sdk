from datetime import date
from decimal import Decimal

from yuki_sdk import (
    ContactDefaultValueSet,
    FinancialMode,
    GLAccountSet,
    PaymentMethodSet,
    Period,
    ProjectSet,
    RGSEntrySet,
    StartBalanceSet,
    TransactionDetailSet,
    TransactionDocument,
    TransactionSet,
)


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
    if transactions.count < 100:
        return
    start, end = period
    # startRecord counts from 1: the second page of 100 starts at record 101.
    second = TransactionSet(yuki_cred, administration_id)
    second.get_page(start, end, start_record=101, number_of_records=100)

    assert not {row.id for row in transactions} & {row.id for row in second}


def test_transaction_details(yuki_cred, administration_id, period, transactions):
    start, end = period
    code = transactions[0].gl_account_code
    details = TransactionDetailSet(yuki_cred, administration_id)
    details.get(start, end, gl_account_code=code)

    assert details
    assert all(detail.gl_account_code in (None, code) for detail in details)


def test_period_and_modified_date(yuki_cred, administration_id, year):
    period = Period(yuki_cred, administration_id)
    period.get(year)

    assert period.start is None or isinstance(period.start, date)
    period.modified()


def test_start_balance(yuki_cred, administration_id, year):
    balances = StartBalanceSet(yuki_cred, administration_id)
    balances.get(year, financial_mode=FinancialMode.FISCAL)

    for balance in balances:
        assert balance.gl_account_code
        # The amount is text in the WSDL; it must still parse.
        assert balance.start_balance_text is None or balance.start_balance is not None


def test_transaction_document(yuki_cred, administration_id, transactions):
    row = next(row for row in transactions if row.document)
    document = TransactionDocument(yuki_cred, administration_id)
    document.get(row.id)

    assert document.data is None or isinstance(document.data, bytes)


def test_contact_default_values(yuki_cred, administration_id, transactions):
    contact_id = next((row.contact.id for row in transactions if row.contact and row.contact.id), None)
    if contact_id is None:
        return
    defaults = ContactDefaultValueSet(yuki_cred, administration_id)
    defaults.get(contact_id)

    assert all(value.contact_id in (None, contact_id) for value in defaults)


def test_payment_methods_projects_and_rgs(yuki_cred, administration_id):
    methods = PaymentMethodSet(yuki_cred, administration_id)
    methods.get()
    projects = ProjectSet(yuki_cred, administration_id)
    projects.get()
    rgs = RGSEntrySet(yuki_cred, administration_id)
    rgs.get()

    assert all(method.description for method in methods)
    assert all(project.id for project in projects)
