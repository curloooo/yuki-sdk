from datetime import date, datetime
from decimal import Decimal

from lxml import etree
import pytest
from zeep import xsd

from yuki_sdk import AccountingInfoService, FinancialMode, Transaction
from yuki_sdk.webservices.accountinginfo import DEFAULT_DATA_GROUPS
from yuki_sdk.exceptions import YukiConfigError

ADMINISTRATION_ID = "e7c4b218-deba-437d-844d-d022e355d263"


def _transaction(number: int, **overrides) -> dict:
    """A ``Transaction`` as zeep serialises it (attributes as keys)."""

    row = {
        "id": f"tx-{number}",
        "hID": str(1000 + number),
        "transactionDate": datetime(2026, 10, 8),
        "description": "Factuur voor Numerix",
        "amount": Decimal("144.00"),
        "glAccountCode": "400000",
        "contact": {
            "id": "dd4315ed-7431-4ded-8066-09e9378ee05a",
            "HID": 5,
            "fullName": "Numerix",
            "zipCode": "59299",
            "country": "FR",
            "contactCode": "C005",
            "CoCNumber": "830734745",
            "VATNumber": "FR28830734745",
        },
        "document": {
            "id": "doc-1",
            "HID": 77,
            "reference": "2026-001",
            "type": "6",
            "typeDescription": "Verkoopfactuur",
            "folderId": 2,
            "folder": "Verkoop",
            "folderTabId": 0,
            "folderTab": None,
            "created": datetime(2026, 10, 8, 9, 30),
            "modified": datetime(2026, 10, 8, 9, 31),
            "uploadMethod": "Yuki",
        },
        "documentProcessed": {"processedDate": datetime(2026, 10, 8, 10, 0), "processedBy": "Backoffice"},
        "documentMatched": {"matchDate": datetime(1, 1, 1), "matchedBy": None},
        "foreignCurrency": {"amountFC": Decimal("144.00"), "rate": Decimal("1"), "currency": "EUR"},
        "vat": {"codeType": 1, "codeDescription": "BTW 21%", "codePercentage": Decimal("21")},
        "project": {"code": None, "description": None},
    }
    row.update(overrides)
    return row


class _Credentials:
    debug = False
    domain_id = "domain-1"

    def authenticate(self, force=False):
        return "session-1"

    def wsdl_url(self, service="Sales"):
        return f"https://api.yukiworks.be/ws/{service}.asmx?WSDL"


def _service(monkeypatch, responses):
    """Patch the SOAP layer. ``responses`` maps an operation to a value or a callable(parameters)."""

    calls = []

    def fake_invoke(wsdl_url_value, operation, *, debug=False, on_call=None, **parameters):
        calls.append((operation, parameters))
        response = responses[operation]
        return response(parameters) if callable(response) else response

    monkeypatch.setattr("yuki_sdk.service.soap_invoke", fake_invoke)
    return AccountingInfoService(_Credentials()), calls


def test_transaction_reads_every_group():
    transaction = Transaction.from_plain(_transaction(1))

    assert transaction.id == "tx-1"
    assert transaction.hid == "1001"
    assert transaction.date == date(2026, 10, 8)
    assert transaction.amount == Decimal("144.00")
    assert transaction.contact.contact_code == "C005"
    assert transaction.contact.id == "dd4315ed-7431-4ded-8066-09e9378ee05a"
    assert transaction.document.id == "doc-1"
    assert transaction.document.reference == "2026-001"
    assert transaction.document.type_description == "Verkoopfactuur"
    assert transaction.document.folder_id == 2
    assert transaction.processed_by == "Backoffice"
    # 0001-01-01 is Yuki's empty date.
    assert transaction.matched_date is None
    assert transaction.is_matched is False
    assert transaction.currency == "EUR"
    assert transaction.vat_code_type == 1
    assert transaction.vat_percentage == Decimal("21")
    assert transaction.project_code is None


def test_transaction_without_groups_leaves_them_empty():
    transaction = Transaction.from_plain({"id": "tx-2", "transactionDate": "2026-10-08T00:00:00", "amount": "-5.10"})

    assert transaction.contact is None
    assert transaction.document is None
    assert transaction.amount == Decimal("-5.10")
    assert transaction.date == date(2026, 10, 8)


def test_transaction_reads_a_zeep_object():
    contact_type = xsd.ComplexType(
        [xsd.Element("HID", xsd.Integer()), xsd.Element("contactCode", xsd.String())],
        attributes=[xsd.Attribute("id", xsd.String())],
    )
    transaction_type = xsd.ComplexType(
        [
            xsd.Element("id", xsd.String()),
            xsd.Element("amount", xsd.Decimal()),
            xsd.Element("contact", contact_type),
        ]
    )
    value = transaction_type(id="tx-9", amount=Decimal("1.50"), contact=contact_type(HID=3, contactCode="C3", id="c-3"))

    transaction = Transaction.from_plain(value)

    assert transaction.id == "tx-9"
    assert transaction.amount == Decimal("1.50")
    assert transaction.contact.contact_code == "C3"
    assert transaction.contact.id == "c-3"


def test_transactions_sends_the_paging_parameters(monkeypatch):
    service, calls = _service(monkeypatch, {"GetTransactions": [_transaction(1), _transaction(2)]})

    rows = service.transactions(
        ADMINISTRATION_ID,
        date(2026, 1, 1),
        date(2026, 12, 31),
        financial_mode=FinancialMode.COMMERCIAL,
        number_of_records=50,
        start_record=100,
        search_values=[("AmountGreaterThanEqual", 10)],
    )

    assert [row.id for row in rows] == ["tx-1", "tx-2"]
    operation, parameters = calls[0]
    assert operation == "GetTransactions"
    assert parameters["sessionID"] == "session-1"
    assert parameters["administrationID"] == ADMINISTRATION_ID
    assert parameters["glAccountCode"] == ""
    assert parameters["startDate"] == datetime(2026, 1, 1)
    assert parameters["financialMode"] == 0
    assert parameters["dataGroups"] == DEFAULT_DATA_GROUPS
    assert parameters["numberOfRecords"] == 50
    assert parameters["startRecord"] == 100
    assert parameters["searchValues"] == {
        "TransactionSearch": [{"SearchOption": "AmountGreaterThanEqual", "SearchValue": "10"}]
    }


def test_transactions_accepts_the_array_wrapper(monkeypatch):
    service, _ = _service(monkeypatch, {"GetTransactions": {"Transaction": [_transaction(1)]}})

    assert [row.id for row in service.transactions(ADMINISTRATION_ID, date(2026, 1, 1), date(2026, 1, 31))] == ["tx-1"]


def test_iter_transactions_pages_until_a_short_page(monkeypatch):
    rows = [_transaction(number) for number in range(1, 6)]

    def page(parameters):
        # Live: startRecord counts from 1.
        start = parameters["startRecord"] - 1
        return rows[start : start + parameters["numberOfRecords"]]

    service, calls = _service(monkeypatch, {"GetTransactions": page})

    result = list(service.iter_transactions(ADMINISTRATION_ID, date(2026, 1, 1), date(2026, 12, 31), page_size=2))

    assert [row.id for row in result] == ["tx-1", "tx-2", "tx-3", "tx-4", "tx-5"]
    assert [parameters["startRecord"] for _, parameters in calls] == [1, 3, 5]


def test_iter_transactions_survives_one_based_paging(monkeypatch):
    rows = [_transaction(number) for number in range(1, 6)]

    def page(parameters):
        # 1-based: startRecord 0 and 1 both mean the first record.
        start = max(parameters["startRecord"] - 1, 0)
        return rows[start : start + parameters["numberOfRecords"]]

    service, _ = _service(monkeypatch, {"GetTransactions": page})

    result = list(service.iter_transactions(ADMINISTRATION_ID, date(2026, 1, 1), date(2026, 12, 31), page_size=2))

    assert [row.id for row in result] == ["tx-1", "tx-2", "tx-3", "tx-4", "tx-5"]


def test_iter_transactions_stops_when_paging_is_ignored(monkeypatch):
    service, calls = _service(monkeypatch, {"GetTransactions": [_transaction(1), _transaction(2)]})

    result = list(service.iter_transactions(ADMINISTRATION_ID, date(2026, 1, 1), date(2026, 12, 31), page_size=2))

    assert [row.id for row in result] == ["tx-1", "tx-2"]
    assert len(calls) == 2


def test_iter_transactions_respects_max_pages(monkeypatch):
    service, calls = _service(monkeypatch, {"GetTransactions": lambda parameters: [_transaction(parameters["startRecord"] + 1)]})

    result = list(
        service.iter_transactions(ADMINISTRATION_ID, date(2026, 1, 1), date(2026, 12, 31), page_size=1, max_pages=3)
    )

    assert len(result) == 3
    assert len(calls) == 3


def test_transactions_rejects_an_empty_page_size(monkeypatch):
    service, _ = _service(monkeypatch, {})

    with pytest.raises(YukiConfigError):
        service.transactions(ADMINISTRATION_ID, date(2026, 1, 1), date(2026, 1, 31), number_of_records=0)


def test_transaction_details(monkeypatch):
    detail = {
        "id": "tx-1",
        "hID": "1001",
        "transactionDate": datetime(2026, 10, 8),
        "transactionAmount": Decimal("144.00"),
        "transactionAmountForeignCurrency": Decimal("150.00"),
        "currencyRate": Decimal("0.96"),
        "currency": "USD",
        "taxCodeDescription": "BTW 21%",
        "contactCode": "C005",
        "contactID": "contact-1",
        "glAccountCode": "400000",
        "documentID": "doc-1",
        "documentReference": "2026-001",
        "documentType": "Verkoopfactuur",
        "documentFolder": "Verkoop",
        "periodId": "2026-10",
    }
    service, calls = _service(monkeypatch, {"GetTransactionDetails": {"TransactionInfo": [detail]}})

    rows = service.transaction_details(ADMINISTRATION_ID, date(2026, 10, 1), date(2026, 10, 31))

    assert rows[0].amount_currency == Decimal("150.00")
    assert rows[0].document_id == "doc-1"
    assert rows[0].period_id == "2026-10"
    assert calls[0][1]["GLAccountCode"] == ""
    assert calls[0][1]["financialMode"] == 1


def test_periods_balances_and_modified_date(monkeypatch):
    service, calls = _service(
        monkeypatch,
        {
            "GetPeriodDateTable": {"name": "2026", "period": datetime(2025, 10, 1), "wholePeriod": "2025-10-01/2026-09-30", "ISO8601Period": True},
            "GetStartBalanceByGlAccount": [
                {"accountID": "400000", "startBalance": "1250.50", "accountDescription": "Klanten"},
                {"accountID": "550000", "startBalance": "-10", "accountDescription": "Bank"},
            ],
            "GetFinancialYearModifiedDate": datetime(2026, 10, 9, 14, 0),
        },
    )

    period = service.period_date_table(ADMINISTRATION_ID, 2026)
    balances = service.start_balance_by_gl_account(ADMINISTRATION_ID, 2026, financial_mode=FinancialMode.COMMERCIAL)
    modified = service.financial_year_modified_date(ADMINISTRATION_ID, 2026)

    assert period.period == date(2025, 10, 1)
    assert period.iso8601_period is True
    assert balances[0].start_balance == Decimal("1250.50")
    assert balances[1].gl_account_code == "550000"
    assert modified == datetime(2026, 10, 9, 14, 0)
    assert calls[0][1]["yearID"] == 2026
    assert calls[1][1] == {"administrationID": ADMINISTRATION_ID, "bookyear": 2026, "financialMode": 0, "sessionID": "session-1"}


def test_document_defaults_and_payment_methods(monkeypatch):
    service, _ = _service(
        monkeypatch,
        {
            "GetTransactionDocument": {"fileName": "factuur.pdf", "filedata": b"%PDF-1.4"},
            "GetContactDefaultValues": [
                {
                    "ContactId": "contact-1",
                    "ContactName": "Numerix",
                    "DefaultBankAccount": "BE68539007547034",
                    "DefaultValues": {
                        "DefaultValue": [
                            {
                                "InputFields": {"DocumentType": "Inkoopfactuur", "Priority": 1},
                                "OutputFields": {"GLAccount": "604000", "VATCode": "1", "PaymentMethod": "1", "PaymentTerm": "30"},
                                "Created": datetime(2025, 1, 1),
                            }
                        ]
                    },
                }
            ],
            "GetCustomPaymentMethods": [{"ID": 4, "Description": "Domiciliëring"}],
        },
    )

    document = service.transaction_document(ADMINISTRATION_ID, "tx-1")
    defaults = service.contact_default_values(ADMINISTRATION_ID, "contact-1")
    methods = service.custom_payment_methods(ADMINISTRATION_ID)

    assert document.file_name == "factuur.pdf"
    assert document.data == b"%PDF-1.4"
    assert defaults[0].default_bank_account == "BE68539007547034"
    assert defaults[0].default_values[0].payment_term == "30"
    assert defaults[0].default_values[0].priority == 1
    assert methods[0].id == 4


def test_parsers_read_lxml_elements():
    element = etree.fromstring(
        """
        <Transaction xmlns="http://www.theyukicompany.com/">
          <id>tx-1</id>
          <transactionDate>2026-10-08T00:00:00</transactionDate>
          <amount>-12.40</amount>
          <contact id="c-1"><HID>5</HID><contactCode>C005</contactCode></contact>
        </Transaction>
        """
    )

    transaction = Transaction.from_plain(element)

    assert transaction.amount == Decimal("-12.40")
    assert transaction.contact.id == "c-1"
    assert transaction.contact.hid == 5
