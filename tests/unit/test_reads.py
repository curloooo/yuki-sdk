from datetime import date
from decimal import Decimal

from lxml import etree
import pytest

from yuki_sdk.webservices.accounting import AccountingService, GLAccountBalance, GLAccountTransaction, OutstandingItem
from yuki_sdk.webservices.contact import Administration, Contact, ContactService, SupportedLanguage
from yuki_sdk.exceptions import YukiSessionError

CONTACT_XML = """
<Contacts xmlns="">
  <Contact ID="dd4315ed-7431-4ded-8066-09e9378ee05a">
    <Type>Company</Type>
    <HID>5</HID>
    <Name>Numerix</Name>
    <City>BOESCHEPE</City>
    <Country>FR</Country>
    <VATNumber>FR28 830734745</VATNumber>
    <CoCNumber>830734745</CoCNumber>
    <IsSupplier>False</IsSupplier>
    <IsCustomer>True</IsCustomer>
  </Contact>
  <Contact ID="person-1">
    <Type>Person</Type>
    <FirstName>Ward</FirstName>
    <LastName>Cornette</LastName>
    <Country>BE</Country>
  </Contact>
</Contacts>
"""

ADMIN_XML = """
<Administrations xmlns="">
  <Administration ID="e7c4b218-deba-437d-844d-d022e355d263">
    <Name>curlo-test</Name>
    <City>Antwerpen</City>
    <DomainID>7c0445a0-99fe-44ec-8f71-2747747955cd</DomainID>
    <Active>true</Active>
    <InternalCustomerCode>C-1</InternalCustomerCode>
  </Administration>
</Administrations>
"""

LANGUAGE_XML = """
<Languages xmlns="">
  <Language Code="nl-be"><Description>Nederlands</Description><NativeDescription>Nederlands</NativeDescription></Language>
</Languages>
"""

BALANCE_XML = """
<GLAccountBalance xmlns="">
  <GLAccount Code="400000" BalanceType="B"><Description>Klanten</Description><Amount>144.00</Amount></GLAccount>
</GLAccountBalance>
"""

TRANSACTION_XML = """
<GLAccountTransactions xmlns="">
  <GLAccountTransaction ID="tx-1">
    <Date>2026-10-08</Date>
    <Description>Factuur voor Numerix</Description>
    <Amount>144.00</Amount>
    <Contact>Numerix</Contact>
    <ContactID>contact-1</ContactID>
    <Project Code="P1"/>
    <GLAccountCode>400000</GLAccountCode>
    <FileName>Invoice 1.pdf</FileName>
    <TransactionType>5</TransactionType>
  </GLAccountTransaction>
</GLAccountTransactions>
"""

ITEM_XML = """
<OutstandingDebtorItems xmlns="">
  <Item ID="item-1">
    <Date>2026-10-08</Date>
    <Description>Factuur voor Numerix</Description>
    <Contact>Numerix</Contact>
    <OpenAmount>144.00</OpenAmount>
    <OriginalAmount>144.00</OriginalAmount>
    <Type ID="6">Verkoopfactuur</Type>
    <Reference>1</Reference>
    <DueDate>2026-10-22</DueDate>
  </Item>
</OutstandingDebtorItems>
"""


class _Credentials:
    debug = False
    domain_id = "domain-1"

    def authenticate(self, force=False):
        return "session-1"

    def wsdl_url(self, service="Sales"):
        return f"https://api.yukiworks.be/ws/{service}.asmx?WSDL"


def test_contact_parser_reads_company_and_person():
    contacts = [Contact.from_plain(row) for row in etree.fromstring(CONTACT_XML)]
    company, person = contacts
    assert company.id == "dd4315ed-7431-4ded-8066-09e9378ee05a"
    assert company.name == "Numerix"
    assert company.is_customer is True
    assert company.is_supplier is False
    assert company.vat_number == "FR28 830734745"
    assert person.name == "Ward Cornette"
    assert person.country == "BE"


def test_administration_language_balance_transaction_and_item_parsers():
    administration = Administration.from_plain(etree.fromstring(ADMIN_XML)[0])
    assert administration.name == "curlo-test"
    assert administration.domain_id == "7c0445a0-99fe-44ec-8f71-2747747955cd"
    assert administration.active is True
    assert administration.internal_customer_code == "C-1"

    language = SupportedLanguage.from_plain(etree.fromstring(LANGUAGE_XML)[0])
    assert language.code == "nl-be"
    assert language.description == "Nederlands"

    balance = GLAccountBalance.from_plain(etree.fromstring(BALANCE_XML)[0])
    assert balance.code == "400000"
    assert balance.balance_type == "B"
    assert balance.amount == Decimal("144.00")

    transaction = GLAccountTransaction.from_plain(etree.fromstring(TRANSACTION_XML)[0])
    assert transaction.contact == "Numerix"
    assert transaction.project_code == "P1"
    assert transaction.file_name == "Invoice 1.pdf"
    assert transaction.amount == Decimal("144.00")

    item = OutstandingItem.from_plain(etree.fromstring(ITEM_XML)[0])
    assert item.reference == "1"
    assert item.item_type == "Verkoopfactuur"
    assert item.item_type_id == "6"
    assert item.open_amount == Decimal("144.00")


@pytest.fixture
def calls(monkeypatch):
    recorded = []

    def fake_invoke(wsdl_url_value, operation, *, debug=False, on_call=None, **parameters):
        recorded.append((wsdl_url_value, operation, parameters))
        if operation in {"NetRevenue", "NetRevenueFiscal"}:
            return Decimal("144.00")
        if operation in {"Language", "AdministrationID"}:
            return "nl-be" if operation == "Language" else "admin-1"
        samples = {
            "SearchContacts": CONTACT_XML,
            "GetSuppliersAndCustomers": CONTACT_XML,
            "Administrations": ADMIN_XML,
            "AdministrationsWithInternalCustomerCode": ADMIN_XML,
            "Companies": ADMIN_XML.replace("Administration", "Company"),
            "SupportedLanguages": LANGUAGE_XML,
            "GLAccountBalance": BALANCE_XML,
            "GLAccountBalanceFiscal": BALANCE_XML,
            "GLAccountBalanceYearEnd": BALANCE_XML,
            "GLAccountTransactions": TRANSACTION_XML,
            "GLAccountTransactionsAndContact": TRANSACTION_XML,
            "GLAccountTransactionsFiscal": TRANSACTION_XML,
            "OutstandingCreditorItems": ITEM_XML,
            "OutstandingCreditorItemsByDate": ITEM_XML,
            "OutstandingCreditorItemsByDateOutstanding": ITEM_XML,
            "OutstandingCreditorWithPaymentReference": ITEM_XML,
            "OutstandingDebtorItems": ITEM_XML,
            "OutstandingDebtorItemsByDate": ITEM_XML,
            "OutstandingDebtorItemsByDateOutstanding": ITEM_XML,
            "OutstandingDebtorItemsWithLanguage": ITEM_XML,
            "OutstandingDebtorWithPaymentReference": ITEM_XML,
            "CheckOutstandingItem": ITEM_XML,
            "CheckOutstandingItemAdmin": ITEM_XML,
        }
        return etree.fromstring(samples[operation])

    monkeypatch.setattr("yuki_sdk.service.soap_invoke", fake_invoke)
    return recorded


def test_contact_read_methods_call_the_matching_operation(calls):
    service = ContactService(_Credentials())
    assert service.search("Numerix")[0].name == "Numerix"
    assert service.suppliers_and_customers(contact_type="Customer")[1].name == "Ward Cornette"
    assert service.administrations()[0].city == "Antwerpen"
    assert service.administrations_with_internal_customer_code()[0].internal_customer_code == "C-1"
    assert service.companies()[0].name == "curlo-test"
    assert service.administration_id("curlo-test") == "admin-1"
    assert service.language() == "nl-be"
    assert service.supported_languages()[0].code == "nl-be"

    operations = [call[1] for call in calls]
    assert operations == [
        "SearchContacts",
        "GetSuppliersAndCustomers",
        "Administrations",
        "AdministrationsWithInternalCustomerCode",
        "Companies",
        "AdministrationID",
        "Language",
        "SupportedLanguages",
    ]
    assert calls[0][0] == "https://api.yukiworks.be/ws/Contact.asmx?WSDL"
    assert calls[0][2]["sessionID"] == "session-1"
    assert calls[0][2]["domainID"] == "domain-1"
    assert calls[0][2]["searchValue"] == "Numerix"
    assert calls[0][2]["searchOption"] == "Name"
    assert calls[0][2]["sortOrder"] == "Name"
    assert calls[0][2]["active"] == "Both"
    assert calls[1][2]["contactType"] == "Customer"


def test_accounting_read_methods_call_the_matching_operation(calls):
    service = AccountingService(_Credentials())
    on = date(2026, 10, 9)
    start = date(2026, 1, 1)
    assert service.gl_account_balance("admin-1", on)[0].code == "400000"
    assert service.gl_account_balance_fiscal("admin-1", on)[0].description == "Klanten"
    assert service.gl_account_balance_year_end("admin-1", on)[0].balance_type == "B"
    assert service.gl_account_transactions("admin-1", "400000", start, on)[0].gl_account_code == "400000"
    assert service.gl_account_transactions_and_contact("admin-1", "400000", start, on)[0].file_name == "Invoice 1.pdf"
    assert service.gl_account_transactions_fiscal("admin-1", "400000", start, on)[0].id == "tx-1"
    assert service.net_revenue("admin-1", start, on) == Decimal("144.00")
    assert service.net_revenue_fiscal("admin-1", start, on) == Decimal("144.00")
    assert service.outstanding_creditor_items("admin-1")[0].reference == "1"
    assert service.outstanding_creditor_items_by_date("admin-1", start, on)[0].contact == "Numerix"
    assert service.outstanding_creditor_items_by_date_outstanding("admin-1", on)[0].item_type_id == "6"
    assert service.outstanding_creditor_with_payment_reference("admin-1", start, on)[0].open_amount == Decimal("144.00")
    assert service.outstanding_debtor_items("admin-1")[0].due_date == date(2026, 10, 22)
    assert service.outstanding_debtor_items_by_date("admin-1", start, on)[0].description.startswith("Factuur")
    assert service.outstanding_debtor_items_by_date_outstanding("admin-1", on)[0].id == "item-1"
    assert service.outstanding_debtor_items_with_language("admin-1")[0].item_type == "Verkoopfactuur"
    assert service.outstanding_debtor_with_payment_reference("admin-1", start, on)[0].original_amount == Decimal("144.00")
    assert service.check_outstanding_item("1")[0].reference == "1"
    assert service.check_outstanding_item_admin("admin-1", "1")[0].contact == "Numerix"

    assert [call[1] for call in calls] == [
        "GLAccountBalance",
        "GLAccountBalanceFiscal",
        "GLAccountBalanceYearEnd",
        "GLAccountTransactions",
        "GLAccountTransactionsAndContact",
        "GLAccountTransactionsFiscal",
        "NetRevenue",
        "NetRevenueFiscal",
        "OutstandingCreditorItems",
        "OutstandingCreditorItemsByDate",
        "OutstandingCreditorItemsByDateOutstanding",
        "OutstandingCreditorWithPaymentReference",
        "OutstandingDebtorItems",
        "OutstandingDebtorItemsByDate",
        "OutstandingDebtorItemsByDateOutstanding",
        "OutstandingDebtorItemsWithLanguage",
        "OutstandingDebtorWithPaymentReference",
        "CheckOutstandingItem",
        "CheckOutstandingItemAdmin",
    ]
    assert calls[0][0] == "https://api.yukiworks.be/ws/Accounting.asmx?WSDL"
    assert calls[3][2]["GLAccountCode"] == "400000"
    assert calls[8][2]["includeBankTransactions"] is False
    assert calls[8][2]["sortOrder"] == "DateDesc"
    assert calls[17][2]["Reference"] == "1"
    assert "administrationID" not in calls[17][2]


def test_rejected_session_is_retried_once(monkeypatch):
    attempts = {"count": 0}
    forces = []

    class Credentials(_Credentials):
        def authenticate(self, force=False):
            forces.append(force)
            return "session-1"

    def fake_invoke(wsdl_url_value, operation, *, debug=False, on_call=None, **parameters):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise YukiSessionError("Invalid session ID")
        return Decimal("1")

    monkeypatch.setattr("yuki_sdk.service.soap_invoke", fake_invoke)
    amount = AccountingService(Credentials()).net_revenue("admin-1", date(2026, 1, 1), date(2026, 10, 9))

    assert amount == Decimal("1")
    assert forces == [False, True]
