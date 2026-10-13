"""Check every SDK read against the published WSDL contract.

``fixtures/wsdl_contract.json`` holds the request elements, response types and
enums of the operations the SDK calls, taken from the live WSDLs. These tests
catch a wrong parameter name, a missing required element, a value of the wrong
type or outside its enum, and a parser that drops a field Yuki returns.
"""

from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
import inspect
import json
from pathlib import Path
import re

from lxml import etree
import pytest

import yuki_sdk
from yuki_sdk import (
    AccountingInfoService,
    AccountingService,
    ArchiveService,
    BackofficeService,
    ContactService,
    IntegrationService,
    UblService,
    VatService,
)
from yuki_sdk.webservices.accountinginfo import (
    AccountStartBalance,
    AdministrationPeriod,
    ContactDefaultValues,
    PaymentMethod,
    Project,
    ProjectBalance,
    RGSEntry,
    Transaction,
    TransactionDocumentFile,
    TransactionInfo,
    parse_gl_accounts,
)
from yuki_sdk.webservices.integration import AdministrationData
from yuki_sdk.webservices.ubl import _arg_xml
from yuki_sdk.webservices.vat import VATCode, VATReturnInfo

CONTRACT = json.loads((Path(__file__).parent / "fixtures" / "wsdl_contract.json").read_text(encoding="utf-8"))
ADMIN = "admin-1"
START, END = date(2026, 1, 1), date(2026, 12, 31)


class _Credentials:
    debug = False
    domain_id = "domain-1"

    def authenticate(self, force=False):
        return "session-1"

    def wsdl_url(self, service="Sales"):
        return f"https://api.yukiworks.be/ws/{service}.asmx?WSDL"


# Every public read of the SDK, called once. The iter_* helpers delegate to these.
READS = {
    AccountingInfoService: {
        "gl_account_scheme": lambda s: s.gl_account_scheme(ADMIN),
        "transactions": lambda s: s.transactions(ADMIN, START, END, search_values=[("AmountGreaterThanEqual", 1)]),
        "transaction_details": lambda s: s.transaction_details(ADMIN, START, END),
        "period_date_table": lambda s: s.period_date_table(ADMIN, 2026),
        "financial_year_modified_date": lambda s: s.financial_year_modified_date(ADMIN, 2026),
        "start_balance_by_gl_account": lambda s: s.start_balance_by_gl_account(ADMIN, 2026),
        "transaction_document": lambda s: s.transaction_document(ADMIN, "tx-1"),
        "contact_default_values": lambda s: s.contact_default_values(ADMIN, "c-1"),
        "custom_payment_methods": lambda s: s.custom_payment_methods(ADMIN),
        "projects": lambda s: s.projects(ADMIN),
        "project_balance": lambda s: s.project_balance(ADMIN, START, END),
        "rgs_scheme": lambda s: s.rgs_scheme(ADMIN),
    },
    AccountingService: {
        "gl_account_balance": lambda s: s.gl_account_balance(ADMIN, END),
        "gl_account_balance_fiscal": lambda s: s.gl_account_balance_fiscal(ADMIN, END),
        "gl_account_balance_year_end": lambda s: s.gl_account_balance_year_end(ADMIN, END),
        "gl_account_transactions": lambda s: s.gl_account_transactions(ADMIN, "400000", START, END),
        "gl_account_transactions_and_contact": lambda s: s.gl_account_transactions_and_contact(ADMIN, "400000", START, END),
        "gl_account_transactions_fiscal": lambda s: s.gl_account_transactions_fiscal(ADMIN, "400000", START, END),
        "net_revenue": lambda s: s.net_revenue(ADMIN, START, END),
        "net_revenue_fiscal": lambda s: s.net_revenue_fiscal(ADMIN, START, END),
        "outstanding_creditor_items": lambda s: s.outstanding_creditor_items(ADMIN),
        "outstanding_creditor_items_by_date": lambda s: s.outstanding_creditor_items_by_date(ADMIN, START, END),
        "outstanding_creditor_items_by_date_outstanding": lambda s: s.outstanding_creditor_items_by_date_outstanding(ADMIN, END),
        "outstanding_creditor_with_payment_reference": lambda s: s.outstanding_creditor_with_payment_reference(ADMIN, START, END),
        "outstanding_debtor_items": lambda s: s.outstanding_debtor_items(ADMIN),
        "outstanding_debtor_items_by_date": lambda s: s.outstanding_debtor_items_by_date(ADMIN, START, END),
        "outstanding_debtor_items_by_date_outstanding": lambda s: s.outstanding_debtor_items_by_date_outstanding(ADMIN, END),
        "outstanding_debtor_items_with_language": lambda s: s.outstanding_debtor_items_with_language(ADMIN),
        "outstanding_debtor_with_payment_reference": lambda s: s.outstanding_debtor_with_payment_reference(ADMIN, START, END),
        "check_outstanding_item": lambda s: s.check_outstanding_item("2026-001"),
        "check_outstanding_item_admin": lambda s: s.check_outstanding_item_admin(ADMIN, "2026-001"),
    },
    ContactService: {
        "search": lambda s: s.search("x"),
        "suppliers_and_customers": lambda s: s.suppliers_and_customers(contact_type="Customer"),
        "administrations": lambda s: s.administrations(),
        "administrations_with_internal_customer_code": lambda s: s.administrations_with_internal_customer_code(),
        "administration_id": lambda s: s.administration_id("x"),
        "companies": lambda s: s.companies(),
        "language": lambda s: s.language(),
        "supported_languages": lambda s: s.supported_languages(),
    },
    ArchiveService: {
        "document_folders": lambda s: s.document_folders(),
        "document_folder_tabs": lambda s: s.document_folder_tabs(2),
        "document_folder_counts": lambda s: s.document_folder_counts(2026),
        "documents": lambda s: s.documents(),
        "documents_in_folder": lambda s: s.documents_in_folder(2, start_date=START, end_date=END),
        "documents_in_tab": lambda s: s.documents_in_tab(5),
        "documents_by_type": lambda s: s.documents_by_type(6),
        "search_documents": lambda s: s.search_documents("x"),
        "modified_documents_in_folder": lambda s: s.modified_documents_in_folder(2, START),
        "modified_documents_by_type": lambda s: s.modified_documents_by_type(6, START),
        "find_document": lambda s: s.find_document("doc-1"),
        "document_bundle": lambda s: s.document_bundle("doc-1"),
        "document_binary_data": lambda s: s.document_binary_data("doc-1"),
        "document_file": lambda s: s.document_file("doc-1"),
        "document_download_url": lambda s: s.document_download_url("doc-1"),
        "document_xml_data": lambda s: s.document_xml_data("doc-1"),
        "document_xml_data_as_string": lambda s: s.document_xml_data_as_string("doc-1"),
    },
    VatService: {
        "active_vat_codes": lambda s: s.active_vat_codes(ADMIN),
        "vat_returns": lambda s: s.vat_returns(ADMIN, 2026),
    },
    IntegrationService: {
        "administration_data": lambda s: s.administration_data(ADMIN),
    },
    UblService: {
        "ubl_document": lambda s: s.ubl_document(ADMIN, "inv-1"),
        "find_invoices": lambda s: s.find_invoices(ADMIN, "Sales_AllInvoices", "<Search/>"),
    },
    BackofficeService: {
        "workflow": lambda s: s.workflow(ADMIN),
        "outstanding_questions": lambda s: s.outstanding_questions(ADMIN),
    },
}

_NOT_READS = {"invoke", "read_rows"}


def _public_reads(cls) -> set[str]:
    return {
        name
        for name, member in inspect.getmembers(cls, inspect.isfunction)
        if not name.startswith(("_", "iter_")) and name not in _NOT_READS
    }


@pytest.mark.parametrize("cls", list(READS), ids=lambda cls: cls.__name__)
def test_every_public_read_is_checked(cls):
    assert _public_reads(cls) == set(READS[cls])


@pytest.fixture
def recorded(monkeypatch):
    calls = []

    def fake_invoke(wsdl_url_value, operation, *, debug=False, on_call=None, **parameters):
        calls.append((re.search(r"/ws/(\w+)\.asmx", wsdl_url_value).group(1), operation, parameters))
        return None

    monkeypatch.setattr("yuki_sdk.service.soap_invoke", fake_invoke)
    return calls


def _check_value(service: str, name: str, type_name: str, value):
    enums = CONTRACT[service]["enums"]
    if type_name in enums:
        assert value in enums[type_name], f"{name}={value!r} is not a {type_name}"
    elif type_name == "int" or type_name == "short":
        assert isinstance(value, int) and not isinstance(value, bool), f"{name} must be int"
    elif type_name == "boolean":
        assert isinstance(value, bool), f"{name} must be bool"
    elif type_name == "dateTime":
        assert isinstance(value, datetime), f"{name} must be datetime"
    elif type_name == "string":
        assert isinstance(value, str), f"{name} must be str"
    elif type_name == "any":
        assert isinstance(value, etree._Element), f"{name} must be an XML element"
    elif type_name.startswith("ArrayOf"):
        inner = type_name[len("ArrayOf"):]
        assert set(value) == {inner}, f"{name} must wrap {inner}"
        for item in value[inner]:
            for spec in CONTRACT[service]["types"][inner]:
                field_name, field_type = spec.split(":")
                _check_value(service, f"{name}.{field_name}", field_type, item[field_name])
    else:
        pytest.fail(f"no check for type {type_name}")


@pytest.mark.parametrize(
    "cls,method",
    [(cls, method) for cls, methods in READS.items() for method in methods],
    ids=lambda item: item if isinstance(item, str) else item.__name__,
)
def test_request_matches_the_wsdl(recorded, cls, method):
    READS[cls][method](cls(_Credentials()))

    assert len(recorded) == 1
    service, operation, parameters = recorded[0]
    assert operation in CONTRACT[service]["ops"], f"{service}.{operation} is not in the contract"
    specs = {}
    for spec in CONTRACT[service]["ops"][operation]["p"]:
        name, type_name = spec.split(":")
        specs[name] = (type_name.rstrip("!"), type_name.endswith("!"))
    unknown = set(parameters) - set(specs)
    assert not unknown, f"{operation}: parameters not in the WSDL: {unknown}"
    missing = {name for name, (_, required) in specs.items() if required and name not in parameters}
    assert not missing, f"{operation}: required parameters missing: {missing}"
    for name, value in parameters.items():
        if value is not None:
            _check_value(service, name, specs[name][0], value)


def test_find_invoices_sends_an_empty_document_when_omitted(recorded):
    UblService(_Credentials()).find_invoices(ADMIN, "Sales_AllInvoices")

    parameters = recorded[0][2]
    assert parameters["argXML"] == _arg_xml(None)
    assert parameters["invoiceMode"] == "Sales_AllInvoices"


_FIND_INVOICES_WSDL = """<?xml version="1.0"?>
<definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
    xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
    xmlns:s="http://www.w3.org/2001/XMLSchema"
    xmlns:tns="http://www.theyukicompany.com/"
    targetNamespace="http://www.theyukicompany.com/">
  <types>
    <s:schema elementFormDefault="qualified" targetNamespace="http://www.theyukicompany.com/">
      <s:element name="FindInvoices">
        <s:complexType>
          <s:sequence>
            <s:element minOccurs="0" maxOccurs="1" name="sessionID" type="s:string"/>
            <s:element minOccurs="0" maxOccurs="1" name="administrationID" type="s:string"/>
            <s:element minOccurs="1" maxOccurs="1" name="invoiceMode" type="s:string"/>
            <s:element minOccurs="0" maxOccurs="1" name="argXML">
              <s:complexType mixed="true"><s:sequence><s:any/></s:sequence></s:complexType>
            </s:element>
          </s:sequence>
        </s:complexType>
      </s:element>
      <s:element name="FindInvoicesResponse">
        <s:complexType>
          <s:sequence>
            <s:element minOccurs="0" maxOccurs="1" name="FindInvoicesResult" type="s:string"/>
          </s:sequence>
        </s:complexType>
      </s:element>
    </s:schema>
  </types>
  <message name="FindInvoicesSoapIn"><part name="parameters" element="tns:FindInvoices"/></message>
  <message name="FindInvoicesSoapOut"><part name="parameters" element="tns:FindInvoicesResponse"/></message>
  <portType name="UBLSoap">
    <operation name="FindInvoices">
      <input message="tns:FindInvoicesSoapIn"/>
      <output message="tns:FindInvoicesSoapOut"/>
    </operation>
  </portType>
  <binding name="UBLSoap" type="tns:UBLSoap">
    <soap:binding transport="http://schemas.xmlsoap.org/soap/http"/>
    <operation name="FindInvoices">
      <soap:operation soapAction="http://www.theyukicompany.com/FindInvoices"/>
      <input><soap:body use="literal"/></input>
      <output><soap:body use="literal"/></output>
    </operation>
  </binding>
  <service name="UBL">
    <port name="UBLSoap" binding="tns:UBLSoap">
      <soap:address location="https://api.yukiworks.be/ws/UBL.asmx"/>
    </port>
  </service>
</definitions>
"""


def test_empty_arg_xml_is_an_empty_element(tmp_path):
    """The omitted search document is <argXML/> on the wire. No call to Yuki."""

    from zeep import Client, Settings

    wsdl = tmp_path / "ubl.wsdl"
    wsdl.write_text(_FIND_INVOICES_WSDL, encoding="utf-8")
    client = Client(str(wsdl), settings=Settings(strict=False))
    envelope = client.create_message(
        client.service,
        "FindInvoices",
        sessionID="s",
        administrationID="a",
        invoiceMode="Sales_AllInvoices",
        argXML=_arg_xml(None),
    )

    element = envelope.find(".//{http://www.theyukicompany.com/}argXML")
    assert element is not None
    assert len(element) == 0
    assert not (element.text or "").strip()


# --- responses: every field of a typed response reaches the parsed value ---

def _sample(service: str, type_name: str, counter: list):
    counter[0] += 1
    n = counter[0]
    if type_name.startswith("ArrayOf"):
        inner = type_name[len("ArrayOf"):]
        return {inner: [_sample(service, inner, counter)]}
    types = CONTRACT[service]["types"]
    if type_name in types:
        result = {}
        for spec in types[type_name]:
            if spec.startswith("@"):
                result[spec[1:]] = f"attr-{n}-{spec[1:]}"
                continue
            name, inner = spec.split(":")
            result[name] = _sample(service, inner, counter)
        return result
    return {
        "string": f"text-{n}",
        "int": 1000 + n,
        "short": 1000 + n,
        "decimal": Decimal(f"{n}.25"),
        "dateTime": datetime(2020, 1, 1 + n % 28, n % 24),
        "boolean": True,
        "base64Binary": f"bytes-{n}".encode(),
        "any": "aGVsbG8=",  # base64 text, as the logos arrive
    }[type_name]


def _leaves(value) -> list:
    if isinstance(value, dict):
        return [leaf for item in value.values() for leaf in _leaves(item)]
    if isinstance(value, list):
        return [leaf for item in value for leaf in _leaves(item)]
    return [value]


def _parsed_values(value) -> list:
    if is_dataclass(value):
        return [leaf for item in fields(value) for leaf in _parsed_values(getattr(value, item.name))]
    if isinstance(value, (list, tuple)):
        return [leaf for item in value for leaf in _parsed_values(item)]
    if isinstance(value, dict):
        return []
    return [value]


def _found(leaf, parsed: list) -> bool:
    if isinstance(leaf, bool):
        return True in parsed
    if isinstance(leaf, datetime):
        return leaf in parsed or leaf.date() in parsed
    if leaf == "aGVsbG8=":
        return b"hello" in parsed
    return leaf in parsed or str(leaf) in [str(item) for item in parsed]


RESPONSES = [
    ("AccountingInfo", "Transaction", Transaction.from_plain),
    ("AccountingInfo", "TransactionInfo", TransactionInfo.from_plain),
    ("AccountingInfo", "AdministrationPeriod", AdministrationPeriod.from_plain),
    ("AccountingInfo", "AccountStartBalance", AccountStartBalance.from_plain),
    ("AccountingInfo", "TransactionDocument", TransactionDocumentFile.from_plain),
    ("AccountingInfo", "ContactDefaultValues", ContactDefaultValues.from_plain),
    ("AccountingInfo", "PaymentMethod", PaymentMethod.from_plain),
    ("AccountingInfo", "Project", Project.from_plain),
    ("AccountingInfo", "ProjectBalance", ProjectBalance.from_plain),
    ("AccountingInfo", "RGSEntry", RGSEntry.from_plain),
    ("AccountingInfo", "GlAccount", lambda data: parse_gl_accounts([data])[0]),
    ("Vat", "VATCode", VATCode.from_plain),
    ("Vat", "VATReturnInfo", VATReturnInfo.from_plain),
    ("Integration", "AdministrationDataForIntegration", AdministrationData.from_plain),
]


@pytest.mark.parametrize("service,type_name,parser", RESPONSES, ids=[item[1] for item in RESPONSES])
def test_parser_keeps_every_field(service, type_name, parser):
    sample = _sample(service, type_name, [0])

    parsed = _parsed_values(parser(sample))

    dropped = [leaf for leaf in _leaves(sample) if not _found(leaf, parsed)]
    assert not dropped, f"{type_name}: values not in the parsed result: {dropped}"


def test_every_typed_response_has_a_parser():
    parsed_types = {(service, type_name) for service, type_name, _ in RESPONSES}
    typed = set()
    for service, spec in CONTRACT.items():
        if service.startswith("_"):
            continue
        for op in spec["ops"].values():
            result = op["r"]
            inner = result[len("ArrayOf"):] if result.startswith("ArrayOf") else result
            if inner in spec["types"]:
                typed.add((service, inner))
    assert typed <= parsed_types, f"typed responses without a parser check: {typed - parsed_types}"
    assert yuki_sdk.TransactionSet  # the package imports cleanly


# --- untyped responses: the layouts documented in Yuki's support articles ---

DOCUMENTED = [
    (
        "OutstandingItems (support: CheckOutstandingItem, OutstandingDebtorItems)",
        '<OutstandingItems><Item ID="i-1"><Date>2026-01-02</Date><Description>d-1</Description><Contact>c-1</Contact>'
        "<ContactID>cid-1</ContactID><OpenAmount>1.25</OpenAmount><OriginalAmount>2.25</OriginalAmount>"
        '<Type ID="6">t-1</Type><Reference>r-1</Reference><DueDate>2026-02-03</DueDate><ContactCode>cc-1</ContactCode>'
        "<CoCNumber>coc-1</CoCNumber><VATNumber>vat-1</VATNumber><AddressLine_1>a-1</AddressLine_1>"
        "<AddressLine_2>a-2</AddressLine_2><Postcode>p-1</Postcode><City>ci-1</City>"
        "<MailAddressLine_1>m-1</MailAddressLine_1><MailAddressLine_2>m-2</MailAddressLine_2>"
        "<MailPostcode>mp-1</MailPostcode><MailCity>mc-1</MailCity><Country>BE</Country></Item></OutstandingItems>",
        lambda element: yuki_sdk.OutstandingItem.from_plain(yuki_sdk.plain(element)["Item"]),
    ),
    (
        "Administrations (support: Accounting - Administrations)",
        '<Administrations><Administration ID="a-1"><Name>n-1</Name><AddressLine>al-1</AddressLine>'
        "<AddressLine_2>al-2</AddressLine_2><Postcode>p-1</Postcode><City>c-1</City><Country>BE</Country>"
        "<CoCNumber>coc-1</CoCNumber><VATNumber>vat-1</VATNumber><StartDate>2020-01-01</StartDate>"
        "</Administration></Administrations>",
        lambda element: yuki_sdk.Administration.from_plain(yuki_sdk.plain(element)["Administration"]),
    ),
    (
        "GLAccountBalance (support: Accounting - GLAccountBalance)",
        '<GLAccountBalance><GLAccount Code="400000" BalanceType="B"><Description>d-1</Description>'
        "<Amount>1.25</Amount></GLAccount></GLAccountBalance>",
        lambda element: yuki_sdk.GLAccountBalance.from_plain(yuki_sdk.plain(element)["GLAccount"]),
    ),
    (
        "GLAccountTransactions (support: Accounting - GLAccountTransactions)",
        '<GLAccountTransactions><GLAccountTransaction ID="t-1"><Date>2026-01-02</Date><Description>d-1</Description>'
        '<Amount>1.25</Amount><Contact>c-1</Contact><Project Code="pr-1"/><GLAccountCode>400000</GLAccountCode>'
        "</GLAccountTransaction></GLAccountTransactions>",
        lambda element: yuki_sdk.GLAccountTransaction.from_plain(yuki_sdk.plain(element)["GLAccountTransaction"]),
    ),
]


def _xml_leaves(element) -> list[str]:
    values = [value for value in element.attrib.values()]
    for child in element:
        values.extend(_xml_leaves(child))
    if element.text and element.text.strip():
        values.append(element.text.strip())
    return values


@pytest.mark.parametrize("name,xml,parser", DOCUMENTED, ids=[item[0].split(" ")[0] for item in DOCUMENTED])
def test_documented_untyped_fields_are_kept(name, xml, parser):
    element = etree.fromstring(xml)

    parsed = [str(value) for value in _parsed_values(parser(element))]

    dropped = [leaf for leaf in _xml_leaves(element) if leaf not in parsed and str(_as_parsed(leaf)) not in parsed]
    assert not dropped, f"{name}: values not in the parsed result: {dropped}"


def _as_parsed(leaf: str):
    try:
        return date.fromisoformat(leaf)
    except ValueError:
        try:
            return Decimal(leaf)
        except Exception:
            return leaf
