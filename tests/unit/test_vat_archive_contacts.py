from datetime import date, datetime
from decimal import Decimal

from lxml import etree
import pytest

from yuki_sdk import ArchiveService, ContactService, VatService
from yuki_sdk.exceptions import YukiConfigError

ADMINISTRATION_ID = "e7c4b218-deba-437d-844d-d022e355d263"


class _Credentials:
    debug = False
    domain_id = "domain-1"

    def authenticate(self, force=False):
        return "session-1"

    def wsdl_url(self, service="Sales"):
        return f"https://api.yukiworks.be/ws/{service}.asmx?WSDL"


@pytest.fixture
def patch_soap(monkeypatch):
    def install(responses):
        calls = []

        def fake_invoke(wsdl_url_value, operation, *, debug=False, on_call=None, **parameters):
            calls.append((wsdl_url_value, operation, parameters))
            response = responses[operation]
            return response(parameters) if callable(response) else response

        monkeypatch.setattr("yuki_sdk.service.soap_invoke", fake_invoke)
        return calls

    return install


def test_vat_codes_and_returns(patch_soap):
    calls = patch_soap(
        {
            "ActiveVATCodesList": [
                {"description": "BTW 21%", "type": 1, "typeDescription": "Hoog", "percentage": Decimal("21"), "country": "BE", "startDate": datetime(2000, 1, 1), "endDate": datetime(1, 1, 1)},
                {"description": "BTW 6%", "type": 2, "typeDescription": "Laag", "percentage": Decimal("6"), "country": "BE"},
            ],
            "VATReturnList": {"VATReturnInfo": [{"documentID": "ret-1", "startDate": datetime(2026, 7, 1), "endDate": datetime(2026, 9, 30), "status": "Filed"}]},
        }
    )
    service = VatService(_Credentials())

    codes = service.active_vat_codes(ADMINISTRATION_ID)
    returns = service.vat_returns(ADMINISTRATION_ID, 2026)

    assert [code.type for code in codes] == [1, 2]
    assert codes[0].percentage == Decimal("21")
    assert codes[0].end_date is None
    assert returns[0].end_date == date(2026, 9, 30)
    assert calls[0][0].endswith("/ws/Vat.asmx?WSDL")
    assert calls[1][2]["modifiedAfter"] == datetime(1900, 1, 1)
    assert calls[1][2]["year"] == 2026


DOCUMENTS_XML = """
<Documents xmlns="">
  <Document ID="doc-1">
    <Subject>Factuur Numerix</Subject>
    <DocumentDate>2026-10-08</DocumentDate>
    <Amount>144.00</Amount>
    <Folder ID="2">Verkoop</Folder>
    <ContactName>Numerix</ContactName>
    <FileName>factuur.pdf</FileName>
    <Reference>2026-001</Reference>
    <Extra>kept</Extra>
  </Document>
  <Document ID="doc-2">
    <Subject>Factuur 2</Subject>
  </Document>
</Documents>
"""

FOLDERS_XML = """
<DocumentFolders xmlns="">
  <DocumentFolder ID="1"><Description>Inkoop</Description></DocumentFolder>
  <DocumentFolder ID="2"><Description>Verkoop</Description></DocumentFolder>
</DocumentFolders>
"""


def test_archive_listings_parse_untyped_rows(patch_soap):
    calls = patch_soap(
        {
            "DocumentFolders": etree.fromstring(FOLDERS_XML),
            "DocumentsInFolder": etree.fromstring(DOCUMENTS_XML),
            "DocumentBinaryData": b"%PDF-1.4",
            "DocumentXMLData": etree.fromstring("<SalesInvoice><Reference>2026-001</Reference><DueDate>2026-11-07</DueDate></SalesInvoice>"),
            "FindDocument": etree.fromstring(DOCUMENTS_XML),
        }
    )
    service = ArchiveService(_Credentials())

    folders = service.document_folders()
    documents = service.documents_in_folder(2)
    binary = service.document_binary_data("doc-1")
    xml_data = service.document_xml_data("doc-1")
    found = service.find_document("doc-1")

    assert [(folder.id, folder.name) for folder in folders] == [(1, "Inkoop"), (2, "Verkoop")]
    first = documents[0]
    assert first.id == "doc-1"
    assert first.document_date == date(2026, 10, 8)
    assert first.amount == Decimal("144.00")
    assert first.folder == "Verkoop"
    assert first.folder_id == 2
    assert first.fields["Extra"] == "kept"
    assert binary == b"%PDF-1.4"
    assert xml_data["DueDate"] == "2026-11-07"
    assert found.id == "doc-1"

    parameters = calls[1][2]
    assert "administrationID" not in parameters
    assert parameters["folderID"] == 2
    assert parameters["startDate"] == datetime(1, 1, 1)
    assert parameters["endDate"] == datetime(1, 1, 1)
    assert parameters["sortOrder"] == "DocumentDateAsc"


def test_archive_iter_documents_pages(patch_soap):
    rows = [f'<Document ID="doc-{number}"><Subject>S{number}</Subject></Document>' for number in range(1, 6)]

    def page(parameters):
        start = parameters["startRecord"]
        return etree.fromstring("<Documents>" + "".join(rows[start : start + parameters["numberOfRecords"]]) + "</Documents>")

    calls = patch_soap({"DocumentsInFolder": page})
    service = ArchiveService(_Credentials())

    documents = list(service.iter_documents_in_folder(2, page_size=2, start_date=date(2026, 1, 1)))

    assert [document.id for document in documents] == ["doc-1", "doc-2", "doc-3", "doc-4", "doc-5"]
    assert [call[2]["startRecord"] for call in calls] == [0, 2, 4]
    assert calls[0][2]["startDate"] == datetime(2026, 1, 1)
    assert calls[0][2]["folderID"] == 2


def test_archive_rejects_an_empty_page_size(patch_soap):
    patch_soap({})

    with pytest.raises(YukiConfigError):
        ArchiveService(_Credentials()).documents(number_of_records=0)


def test_document_bundle_and_file(patch_soap):
    calls = patch_soap(
        {
            "DocumentBundle": etree.fromstring(
                '<Documents><Document ID="doc-2"><FileName>bijlage.pdf</FileName></Document>'
                '<Document ID="doc-3"><FileName>factuur.xml</FileName></Document></Documents>'
            ),
            "DocumentFile": etree.fromstring(
                "<File><FileName>factuur.pdf</FileName><Data>JVBERi0xLjQ=</Data><ContentType>application/pdf</ContentType></File>"
            ),
        }
    )
    service = ArchiveService(_Credentials())

    bundle = service.document_bundle("doc-1")
    file = service.document_file("doc-1")

    assert [(document.id, document.file_name) for document in bundle] == [("doc-2", "bijlage.pdf"), ("doc-3", "factuur.xml")]
    assert file.file_name == "factuur.pdf"
    assert file.data == b"%PDF-1.4"
    assert file.fields == {"FileName": "factuur.pdf", "ContentType": "application/pdf"}
    assert [call[2]["documentID"] for call in calls] == ["doc-1", "doc-1"]


def _contacts_page(numbers):
    contacts = "".join(f'<Contact ID="c-{number}"><Name>Contact {number}</Name></Contact>' for number in numbers)
    return etree.fromstring(f"<Contacts>{contacts}</Contacts>")


def test_iter_suppliers_and_customers_follows_pages(patch_soap):
    pages = {1: range(1, 101), 2: range(101, 151)}
    calls = patch_soap({"GetSuppliersAndCustomers": lambda parameters: _contacts_page(pages.get(parameters["pageNumber"], []))})
    service = ContactService(_Credentials())

    contacts = list(service.iter_suppliers_and_customers("Customer"))

    assert len(contacts) == 150
    assert [call[2]["pageNumber"] for call in calls] == [1, 2]
    parameters = calls[0][2]
    assert parameters["contactType"] == "Customer"
    assert parameters["searchOption"] == "All"
    assert parameters["active"] == "Both"
    assert parameters["modifiedAfter"] == datetime(1900, 1, 1)
    assert parameters["domainID"] == "domain-1"


def test_iter_contacts_stops_when_a_page_repeats(patch_soap):
    calls = patch_soap({"SearchContacts": lambda parameters: _contacts_page(range(1, 101))})
    service = ContactService(_Credentials())

    contacts = list(service.iter_contacts())

    assert len(contacts) == 100
    assert len(calls) == 2
