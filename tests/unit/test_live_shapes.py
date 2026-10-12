"""Parsers against response layouts recorded live from the curlo-test administration (12 October 2026)."""

from datetime import date, datetime
from decimal import Decimal

from lxml import etree

from yuki_sdk.webservices.accountinginfo import Transaction
from yuki_sdk.webservices.archive import ArchiveDocument, ArchiveFile
from yuki_sdk.webservices.contact import Contact
from yuki_sdk.parsing import unwrap_rows

DOCUMENTS = """<Documents xmlns=""><Document ID="doc-1"><Subject>Factuur voor Klant</Subject><DocumentDate>2026-10-08</DocumentDate>
<Amount>144.00</Amount><Folder ID="2">Verkoop</Folder><Tab ID="201">Facturen</Tab><Type>6</Type><TypeDescription>Verkoopfactuur</TypeDescription>
<FileName>Invoice 1.pdf</FileName><ContentType>application/pdf</ContentType><FileSize>8177</FileSize><ContactName>Klant</ContactName>
<ContactId>contact-1</ContactId><Reference>1</Reference><VATAmount>0.00</VATAmount><Created>2026-10-08T16:36:04</Created>
<Creator>Boekhouder</Creator><Modified>2026-10-08T16:36:08</Modified><Modifier>Boekhouder</Modifier></Document></Documents>"""

DOCUMENT_FILE = """<Document xmlns="" ID="doc-1"><FileName>Invoice 1.pdf</FileName><FileSize>8177.00</FileSize><FileData>JVBERg==</FileData></Document>"""

CONTACTS = """<Contacts xmlns=""><Contact ID="contact-1"><Type>Company</Type><HID>5</HID><Code/><Name>Klant</Name>
<AddressLine_1>Rue de la Gare 1</AddressLine_1><AddressLine_2/><Postcode>59299</Postcode><City>Boeschepe</City><Country>FR</Country>
<EMailWork/><VATNumber>FR28 830734745</VATNumber><Created>10/08/2026 16:35:39</Created><Modified>10/08/2026 16:35:39</Modified>
<IsSupplier>False</IsSupplier><IsCustomer>True</IsCustomer><Tags/><BackofficeStatus>Actief</BackofficeStatus></Contact></Contacts>"""

# GetTransactions line of the year-end correction Yuki books itself.
YEAR_END_LINE = {
    "id": "line-4", "hID": "4", "transactionDate": "2026-12-31T00:00:00", "description": "Overboeking onverdeelde resultaten",
    "amount": "-144.00", "glAccountCode": "140000",
    "contact": {"HID": 0, "fullName": None, "zipCode": None, "country": None, "contactCode": None, "CoCNumber": None, "VATNumber": None, "id": None},
    "document": {"HID": 3, "reference": None, "type": "37", "typeDescription": "TRMEnd-of-year correction", "folderId": 8,
                 "folder": "TRMOther financial", "folderTabId": 804, "folderTab": "TRMEnd-of-year-corrections",
                 "created": "2026-10-08T16:36:49.163000", "modified": "2026-10-08T16:36:49.163000", "uploadMethod": "Overig", "id": "doc-3"},
    "documentProcessed": None, "documentMatched": None,
    "foreignCurrency": {"amountFC": "-144.00", "rate": "1.000000", "currency": "EUR"},
    "vat": {"codeType": None, "codeDescription": None, "codePercentage": None}, "project": None,
}


def test_archive_document_reads_every_field():
    document = ArchiveDocument.from_plain(unwrap_rows(etree.fromstring(DOCUMENTS), "Document")[0])

    assert document.id == "doc-1"
    assert (document.folder_id, document.folder, document.tab_id, document.tab) == (2, "Verkoop", 201, "Facturen")
    assert (document.type, document.type_description) == ("6", "Verkoopfactuur")
    assert document.contact_id == "contact-1"
    assert document.content_type == "application/pdf"
    assert document.file_size == 8177
    assert document.vat_amount == Decimal("0.00")
    assert document.created == datetime(2026, 10, 8, 16, 36, 4)
    assert document.creator == "Boekhouder"


def test_document_file_decodes_file_data():
    archived = ArchiveFile.from_plain(etree.fromstring(DOCUMENT_FILE))

    assert archived.file_name == "Invoice 1.pdf"
    assert archived.data == b"%PDF"


def test_contact_dates_are_month_first():
    contact = Contact.from_plain(unwrap_rows(etree.fromstring(CONTACTS), "Contact")[0])

    assert contact.created == datetime(2026, 10, 8, 16, 35, 39)
    assert contact.is_customer is True and contact.is_supplier is False
    assert contact.code is None


def test_line_without_contact_has_no_contact():
    line = Transaction.from_plain(YEAR_END_LINE)

    assert line.contact is None
    assert line.document.type == "37"
    assert line.date == date(2026, 12, 31)
