"""The record and record-set classes, with the service layer replaced (no SOAP)."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from yuki_sdk import (
    AccountingInfoService,
    AccountingService,
    ArchiveService,
    Company,
    ContactService,
    ContactSet,
    Document,
    FinancialMode,
    GLAccountBalanceSet,
    GLAccountTransactionSet,
    IntegrationService,
    NetRevenue,
    OutstandingItemSet,
    Period,
    TransactionDocument,
    TransactionSet,
    UblService,
    YukiConfigError,
    YukiError,
)
from yuki_sdk.webservices.accounting import GLAccountBalance
from yuki_sdk.webservices.accountinginfo import AdministrationPeriod, Transaction, TransactionDocumentFile
from yuki_sdk.webservices.archive import ArchiveDocument
from yuki_sdk.webservices.contact import Contact, ContactSearchOption
from yuki_sdk.webservices.integration import AdministrationData


class _Credentials:
    admin_id = "admin-1"
    domain_id = "domain-1"


@pytest.fixture
def calls(monkeypatch):
    """Replace a service method; record each call as (name, args, kwargs)."""

    class Calls(list):
        def stub(self, cls, name, result):
            def method(service, *args, **kwargs):
                self.append((name, args, kwargs))
                return result(*args, **kwargs) if callable(result) else result

            monkeypatch.setattr(cls, name, method)

    return Calls()


def _line(line_id, amount="1.00"):
    return Transaction(id=line_id, amount=Decimal(amount))


def test_set_is_filled_by_get_and_read_like_a_list(calls):
    calls.stub(AccountingInfoService, "iter_transactions", lambda *a, **k: iter([_line("a"), _line("b", "-1.00")]))
    transactions = TransactionSet(_Credentials())

    assert transactions.count == 0 and not transactions
    transactions.get(date(2026, 1, 1), date(2026, 12, 31))

    assert transactions.count == 2 and len(transactions) == 2
    assert [t.id for t in transactions] == ["a", "b"]
    assert transactions[1].amount == Decimal("-1.00")
    assert transactions.to_json()[0]["id"] == "a"
    assert transactions.to_json()[0]["amount"] == "1.00"
    name, args, kwargs = calls[0]
    assert args[0] == "admin-1"
    assert kwargs["financial_mode"] == FinancialMode.FISCAL


def test_get_replaces_the_previous_content(calls):
    pages = iter([[_line("a")], [_line("b")]])
    calls.stub(AccountingInfoService, "transactions", lambda *a, **k: next(pages))
    transactions = TransactionSet(_Credentials())

    transactions.get_page(date(2026, 1, 1), date(2026, 1, 31))
    transactions.get_page(date(2026, 2, 1), date(2026, 2, 28))

    assert [t.id for t in transactions] == ["b"]


def test_administration_comes_from_the_credentials_or_the_argument(calls):
    calls.stub(AccountingInfoService, "iter_transactions", lambda *a, **k: iter([]))

    TransactionSet(_Credentials(), administration_id="admin-2").get(date(2026, 1, 1), date(2026, 1, 31))
    assert calls[-1][1][0] == "admin-2"

    class NoAdministration:
        admin_id = ""

    with pytest.raises(YukiConfigError, match="TransactionSet needs an administration"):
        TransactionSet(NoAdministration()).get(date(2026, 1, 1), date(2026, 1, 31))


def test_period_reads_start_and_end_from_the_whole_period(calls):
    calls.stub(
        AccountingInfoService,
        "period_date_table",
        AdministrationPeriod(name="curlo-test", period=date(2026, 1, 1), whole_period="2026-01-01T00:00:00 2026-12-31T00:00:00"),
    )
    calls.stub(AccountingInfoService, "financial_year_modified_date", datetime(2026, 10, 8, 16, 36))
    period = Period(_Credentials())

    with pytest.raises(AttributeError, match="Period is empty"):
        period.name
    period.get(2026)

    assert period.name == "curlo-test"
    assert (period.start, period.end) == (date(2026, 1, 1), date(2026, 12, 31))
    assert period.modified() == datetime(2026, 10, 8, 16, 36)
    assert calls[0][1] == ("admin-1", 2026)


def test_balance_and_account_line_variants(calls):
    calls.stub(AccountingService, "gl_account_balance", [GLAccountBalance(code="400000", balance_type="B", description="Klanten", amount=Decimal("1"))])
    calls.stub(AccountingService, "gl_account_balance_fiscal", [])
    calls.stub(AccountingService, "gl_account_transactions_and_contact", [])
    calls.stub(AccountingService, "gl_account_transactions_fiscal", [])

    balances = GLAccountBalanceSet(_Credentials())
    balances.get(date(2026, 12, 31))
    assert balances[0].code == "400000"
    balances.get(date(2026, 12, 31), fiscal=True)
    assert balances.count == 0

    lines = GLAccountTransactionSet(_Credentials())
    lines.get("400000", date(2026, 1, 1), date(2026, 12, 31), with_contact=True)
    lines.get("400000", date(2026, 1, 1), date(2026, 12, 31), fiscal=True)
    assert [name for name, _, _ in calls] == [
        "gl_account_balance",
        "gl_account_balance_fiscal",
        "gl_account_transactions_and_contact",
        "gl_account_transactions_fiscal",
    ]
    with pytest.raises(YukiConfigError, match="no fiscal variant"):
        lines.get("400000", date(2026, 1, 1), date(2026, 12, 31), fiscal=True, with_contact=True)


def test_outstanding_items_pick_the_operation_from_the_arguments(calls):
    for name in ("outstanding_debtor_items", "outstanding_debtor_items_by_date", "outstanding_debtor_items_by_date_outstanding"):
        calls.stub(AccountingService, name, [])
    items = OutstandingItemSet(_Credentials())

    items.get_debtors()
    items.get_debtors(start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
    items.get_debtors(outstanding_on=date(2026, 12, 31))

    assert [name for name, _, _ in calls] == [
        "outstanding_debtor_items",
        "outstanding_debtor_items_by_date",
        "outstanding_debtor_items_by_date_outstanding",
    ]
    with pytest.raises(YukiConfigError, match="both start_date and end_date"):
        items.get_debtors(start_date=date(2026, 1, 1))
    with pytest.raises(YukiConfigError, match="not both"):
        items.get_debtors(start_date=date(2026, 1, 1), end_date=date(2026, 2, 1), outstanding_on=date(2026, 2, 1))


def test_net_revenue_amount(calls):
    calls.stub(AccountingService, "net_revenue_fiscal", Decimal("144.00"))
    revenue = NetRevenue(_Credentials())

    revenue.get(date(2026, 1, 1), date(2026, 12, 31), fiscal=True)

    assert revenue.amount == Decimal("144.00") and revenue


def test_contacts_read_by_id_keeps_only_exact_matches(calls):
    calls.stub(ContactService, "search", lambda value, **k: [Contact(id=value, name="x"), Contact(id="other", name="y")])
    contacts = ContactSet(_Credentials())

    contacts.read(["c-1", "c-2"])

    assert [c.id for c in contacts] == ["c-1", "c-2"]
    assert all(kwargs["search_option"] == ContactSearchOption.ID for _, _, kwargs in calls)


def test_document_read_file_bundle_and_ubl(calls):
    calls.stub(ArchiveService, "find_document", lambda document_id: ArchiveDocument(id=document_id, subject="Factuur"))
    calls.stub(ArchiveService, "document_bundle", [ArchiveDocument(id="att-1")])
    calls.stub(UblService, "ubl_document", "<Invoice/>")
    document = Document(_Credentials())

    with pytest.raises(YukiError, match="read"):
        document.id
    document.read(id="doc-1")

    assert document.subject == "Factuur"
    assert [d.id for d in document.bundle()] == ["att-1"]
    assert document.ubl() == "<Invoice/>"
    assert calls[-1][1] == ("admin-1", "doc-1")

    by_id = Document(_Credentials(), id="doc-2")
    assert by_id.ubl() == "<Invoice/>"
    assert calls[-1][1] == ("admin-1", "doc-2")


def test_document_not_found(calls):
    calls.stub(ArchiveService, "find_document", None)

    with pytest.raises(YukiError, match="not found"):
        Document(_Credentials()).read(id="missing")


def test_company_record(calls):
    calls.stub(IntegrationService, "administration_data", AdministrationData(company_name="curlo-test", iban="BE00"))
    company = Company(_Credentials())

    company.get()

    assert company.company_name == "curlo-test"
    assert company.to_json()["iban"] == "BE00"


@pytest.mark.parametrize(
    "record, value_type",
    [
        (Period, AdministrationPeriod),
        (Company, AdministrationData),
        (Document, ArchiveDocument),
        (TransactionDocument, TransactionDocumentFile),
    ],
)
def test_records_declare_every_field_of_their_value(record, value_type):
    """The fields on the class are what the IDE shows; they must match what get() fills."""

    from dataclasses import fields

    from yuki_sdk.record import _declared_fields

    declared = set(_declared_fields(record))
    properties = {name for name in dir(record) if isinstance(getattr(record, name, None), property)}

    assert declared | (properties & {f.name for f in fields(value_type)}) == {f.name for f in fields(value_type)}


def test_record_fields_are_plain_attributes_after_get(calls):
    calls.stub(AccountingInfoService, "transaction_document", TransactionDocumentFile(file_name="a.pdf", data=b"%PDF"))
    document = TransactionDocument(_Credentials())

    document.get("line-1")

    assert vars(document)["file_name"] == "a.pdf"
    assert document.data == b"%PDF"
    with pytest.raises(AttributeError, match="no attribute 'nope'"):
        document.nope
