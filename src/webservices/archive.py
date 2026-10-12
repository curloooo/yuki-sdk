"""Read methods for the Archive webservice (``Archive.asmx``).

Archive operations take no administration id: they act on the domain the
session is bound to (``SetCurrentDomain``, done by ``authenticate()``).

Most responses are untyped (``<any>``) and their layout is not documented.
The dataclasses read the fields seen so far and keep every field of the row in
``fields``, so nothing is lost when Yuki returns more.

Date filters: Yuki treats ``0001-01-01`` as "no date selection"; that is the
default here. Upload operations are not wrapped.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Callable, Iterator

from ..parsing import (
    first_rows,
    get,
    iter_unique_pages,
    plain,
    to_bytes,
    to_date,
    to_datetime,
    to_decimal,
    to_int,
    to_text,
)
from ..service import YukiService, as_datetime, require_positive, require_text, soap_value
from ..exceptions import YukiError
from ..record import YukiRecord, YukiRecordSet
from .ubl import UblService

NO_DATE = datetime(1, 1, 1)
DEFAULT_PAGE_SIZE = 100


class DocumentSortOrder(str, Enum):
    CREATED_DESC = "CreatedDesc"
    CREATED_ASC = "CreatedAsc"
    MODIFIED_DESC = "ModifiedDesc"
    MODIFIED_ASC = "ModifiedAsc"
    DOCUMENT_DATE_DESC = "DocumentDateDesc"
    DOCUMENT_DATE_ASC = "DocumentDateAsc"
    CONTACT_NAME_ASC = "ContactNameAsc"
    CONTACT_NAME_DESC = "ContactNameDesc"


class DocumentSearchOption(str, Enum):
    ALL = "All"
    CREATOR = "Creator"
    CONTACT = "Contact"
    SUBJECT = "Subject"
    TAG = "Tag"
    TYPE = "Type"


@dataclass(frozen=True)
class DocumentFolder:
    """An archive folder or folder tab."""

    id: int | None
    name: str | None = None
    fields: dict = field(default_factory=dict, compare=False, repr=False)

    @classmethod
    def from_plain(cls, data) -> "DocumentFolder":
        data = plain(data)
        if not isinstance(data, dict):
            data = {"_text": data}
        return cls(
            id=to_int(get(data, "ID", "FolderID", "TabID")),
            name=to_text(get(data, "Description", "Name", "_text")),
            fields=data,
        )


@dataclass(frozen=True)
class ArchiveDocument:
    """Metadata of one archived document."""

    id: str
    subject: str | None = None
    document_date: date | None = None
    amount: Decimal | None = None
    currency: str | None = None
    folder: str | None = None
    folder_id: int | None = None
    tab: str | None = None
    tab_id: int | None = None
    contact_name: str | None = None
    file_name: str | None = None
    reference: str | None = None
    type: str | None = None
    type_description: str | None = None
    contact_id: str | None = None
    vat_amount: Decimal | None = None
    content_type: str | None = None
    file_size: int | None = None
    created: datetime | None = None
    creator: str | None = None
    modified: datetime | None = None
    modifier: str | None = None
    fields: dict = field(default_factory=dict, compare=False, repr=False)

    @classmethod
    def from_plain(cls, data) -> "ArchiveDocument":
        data = plain(data) or {}
        folder = get(data, "Folder")
        tab = get(data, "Tab", "FolderTab")
        return cls(
            id=to_text(get(data, "ID", "DocumentID")) or "",
            subject=to_text(get(data, "Subject")),
            document_date=to_date(get(data, "DocumentDate", "Date")),
            amount=to_decimal(get(data, "Amount")),
            currency=to_text(get(data, "Currency")),
            folder=to_text(folder),
            folder_id=to_int(get(folder, "ID") or get(data, "FolderID")),
            tab=to_text(tab),
            tab_id=to_int(get(tab, "ID") or get(data, "TabID")),
            contact_name=to_text(get(data, "ContactName", "Contact")),
            file_name=to_text(get(data, "FileName")),
            reference=to_text(get(data, "Reference")),
            type=to_text(get(data, "Type", "DocumentType")),
            type_description=to_text(get(data, "TypeDescription")),
            contact_id=to_text(get(data, "ContactId", "ContactID")),
            vat_amount=to_decimal(get(data, "VATAmount")),
            content_type=to_text(get(data, "ContentType")),
            file_size=to_int(get(data, "FileSize")),
            created=to_datetime(get(data, "Created")),
            creator=to_text(get(data, "Creator")),
            modified=to_datetime(get(data, "Modified")),
            modifier=to_text(get(data, "Modifier")),
            fields=data,
        )


@dataclass(frozen=True)
class ArchiveFile:
    """The file of a document from ``DocumentFile``.

    The response layout is not documented; ``fields`` keeps everything except
    the binary content.
    """

    file_name: str | None
    data: bytes | None
    fields: dict = field(default_factory=dict, compare=False, repr=False)

    @classmethod
    def from_plain(cls, data) -> "ArchiveFile":
        data = plain(data)
        if not isinstance(data, dict):
            return cls(file_name=None, data=to_bytes(data))
        content_keys = ("Data", "FileData", "Content", "Base64")
        return cls(
            file_name=to_text(get(data, "FileName", "Name")),
            data=to_bytes(get(data, *content_keys)),
            fields={key: value for key, value in data.items() if key.lower() not in {k.lower() for k in content_keys}},
        )


@dataclass(frozen=True)
class DocumentFilter:
    start_date: date | datetime | None = None
    end_date: date | datetime | None = None
    sort_order: str = DocumentSortOrder.DOCUMENT_DATE_ASC


def _date_or_none(value: date | datetime | None) -> datetime:
    return as_datetime(value) if value is not None else NO_DATE


class ArchiveService(YukiService):
    """Read data from ``Archive.asmx``."""

    service_name = "Archive"

    def document_folders(self) -> list[DocumentFolder]:
        result = self.invoke("DocumentFolders")
        return [DocumentFolder.from_plain(row) for row in first_rows(result, "DocumentFolder", "Folder")]

    def document_folder_tabs(self, folder_id: int | str) -> list[DocumentFolder]:
        result = self.invoke("DocumentFolderTabs", folderID=str(folder_id))
        return [
            DocumentFolder.from_plain(row)
            for row in first_rows(result, "DocumentFolderTab", "FolderTab", "Tab")
        ]

    def document_folder_counts(self, year: int) -> list[DocumentFolder]:
        """Return each folder with its document count for ``year`` (the count is in ``fields``)."""

        result = self.invoke("DocumentFolderCounts", year=int(year))
        return [DocumentFolder.from_plain(row) for row in first_rows(result, "DocumentFolder", "Folder")]

    # Paged listings. Each returns one page (one call). The iter_ variants read
    # every page and take the same keyword filters (start_date, end_date, sort_order).

    def documents(
        self,
        *,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        sort_order: str = DocumentSortOrder.DOCUMENT_DATE_ASC,
        start_record: int = 0,
        number_of_records: int = DEFAULT_PAGE_SIZE,
    ) -> list[ArchiveDocument]:
        """All documents of the domain."""

        return self._documents("Documents", DocumentFilter(start_date, end_date, sort_order), start_record, number_of_records)

    def documents_in_folder(
        self,
        folder_id: int,
        *,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        sort_order: str = DocumentSortOrder.DOCUMENT_DATE_ASC,
        start_record: int = 0,
        number_of_records: int = DEFAULT_PAGE_SIZE,
    ) -> list[ArchiveDocument]:
        return self._documents("DocumentsInFolder", DocumentFilter(start_date, end_date, sort_order), start_record, number_of_records, folderID=int(folder_id))

    def documents_in_tab(
        self,
        tab_id: int,
        *,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        sort_order: str = DocumentSortOrder.DOCUMENT_DATE_ASC,
        start_record: int = 0,
        number_of_records: int = DEFAULT_PAGE_SIZE,
    ) -> list[ArchiveDocument]:
        return self._documents("DocumentsInTab", DocumentFilter(start_date, end_date, sort_order), start_record, number_of_records, tabID=int(tab_id))

    def documents_by_type(
        self,
        document_type: int,
        *,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        sort_order: str = DocumentSortOrder.DOCUMENT_DATE_ASC,
        start_record: int = 0,
        number_of_records: int = DEFAULT_PAGE_SIZE,
    ) -> list[ArchiveDocument]:
        return self._documents("DocumentsByType", DocumentFilter(start_date, end_date, sort_order), start_record, number_of_records, documentType=int(document_type))

    def search_documents(
        self,
        search_text: str,
        *,
        search_option: str = DocumentSearchOption.ALL,
        folder_id: int = -1,
        tab_id: int = -1,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        sort_order: str = DocumentSortOrder.DOCUMENT_DATE_ASC,
        start_record: int = 0,
        number_of_records: int = DEFAULT_PAGE_SIZE,
    ) -> list[ArchiveDocument]:
        """Search the archive. ``-1`` for folder or tab searches all of them."""

        return self._documents(
            "SearchDocuments",
            DocumentFilter(start_date, end_date, sort_order),
            start_record,
            number_of_records,
            searchOption=soap_value(search_option),
            searchText=search_text or "",
            folderID=int(folder_id),
            tabID=int(tab_id),
        )

    def iter_documents(self, *, page_size: int = DEFAULT_PAGE_SIZE, **filters) -> Iterator[ArchiveDocument]:
        return self._iter(lambda start, size: self.documents(start_record=start, number_of_records=size, **filters), page_size)

    def iter_documents_in_folder(self, folder_id: int, *, page_size: int = DEFAULT_PAGE_SIZE, **filters) -> Iterator[ArchiveDocument]:
        return self._iter(
            lambda start, size: self.documents_in_folder(folder_id, start_record=start, number_of_records=size, **filters),
            page_size,
        )

    def iter_documents_in_tab(self, tab_id: int, *, page_size: int = DEFAULT_PAGE_SIZE, **filters) -> Iterator[ArchiveDocument]:
        return self._iter(
            lambda start, size: self.documents_in_tab(tab_id, start_record=start, number_of_records=size, **filters),
            page_size,
        )

    def iter_documents_by_type(self, document_type: int, *, page_size: int = DEFAULT_PAGE_SIZE, **filters) -> Iterator[ArchiveDocument]:
        return self._iter(
            lambda start, size: self.documents_by_type(document_type, start_record=start, number_of_records=size, **filters),
            page_size,
        )

    def modified_documents_in_folder(
        self,
        folder_id: int,
        modified_since: date | datetime,
        *,
        sort_order: str = DocumentSortOrder.MODIFIED_ASC,
        start_record: int = 0,
        number_of_records: int = DEFAULT_PAGE_SIZE,
    ) -> list[ArchiveDocument]:
        """Documents of a folder changed since a moment, for a refresh after the bulk extract."""

        return self._modified("ModifiedDocumentsInFolder", modified_since, sort_order, start_record, number_of_records, folderID=int(folder_id))

    def modified_documents_by_type(
        self,
        document_type: int,
        modified_since: date | datetime,
        *,
        sort_order: str = DocumentSortOrder.MODIFIED_ASC,
        start_record: int = 0,
        number_of_records: int = DEFAULT_PAGE_SIZE,
    ) -> list[ArchiveDocument]:
        return self._modified("ModifiedDocumentsByType", modified_since, sort_order, start_record, number_of_records, documentType=int(document_type))

    def iter_modified_documents_in_folder(
        self, folder_id: int, modified_since: date | datetime, *, page_size: int = DEFAULT_PAGE_SIZE, **filters
    ) -> Iterator[ArchiveDocument]:
        return self._iter(
            lambda start, size: self.modified_documents_in_folder(
                folder_id, modified_since, start_record=start, number_of_records=size, **filters
            ),
            page_size,
        )

    def iter_modified_documents_by_type(
        self, document_type: int, modified_since: date | datetime, *, page_size: int = DEFAULT_PAGE_SIZE, **filters
    ) -> Iterator[ArchiveDocument]:
        return self._iter(
            lambda start, size: self.modified_documents_by_type(
                document_type, modified_since, start_record=start, number_of_records=size, **filters
            ),
            page_size,
        )

    # One document. Each call below is one call per document.

    def find_document(self, document_id: str) -> ArchiveDocument | None:
        result = self.invoke("FindDocument", documentID=require_text(document_id, "document_id"))
        rows = first_rows(result, "Document")
        if rows:
            return ArchiveDocument.from_plain(rows[0])
        data = plain(result)
        return ArchiveDocument.from_plain(data) if isinstance(data, dict) and data else None

    def document_bundle(self, document_id: str) -> list[ArchiveDocument]:
        """Return the documents bundled with a main document (attachments, the PDF of a UBL invoice)."""

        result = self.invoke("DocumentBundle", documentID=require_text(document_id, "document_id"))
        return [ArchiveDocument.from_plain(row) for row in first_rows(result, "Document")]

    def document_binary_data(self, document_id: str) -> bytes:
        """Return the file of a document, without its name."""

        result = self.invoke("DocumentBinaryData", documentID=require_text(document_id, "document_id"))
        return to_bytes(result) or b""

    def document_file(self, document_id: str) -> ArchiveFile:
        """Return the file of a document, with its name when Yuki sends one."""

        result = self.invoke("DocumentFile", documentID=require_text(document_id, "document_id"))
        rows = first_rows(result, "File", "DocumentFile")
        return ArchiveFile.from_plain(rows[0] if rows else result)

    def document_download_url(self, document_id: str) -> str:
        """Return a presigned URL for the file of a document."""

        result = self.invoke("DocumentDownloadUrl", documentID=require_text(document_id, "document_id"))
        return str(result or "").strip()

    def document_xml_data(self, document_id: str) -> dict | None:
        """Return the structured data of a processed document as a plain dict.

        For invoices this presumably follows Yuki's sales/purchase invoice layout
        (Reference, Date, DueDate, PaymentReference, lines). The read layout is not
        documented; check the keys before relying on one.
        """

        result = self.invoke("DocumentXMLData", documentID=require_text(document_id, "document_id"))
        return plain(result) or None

    def document_xml_data_as_string(self, document_id: str) -> str | None:
        """Return the structured data of a processed document as XML text (same content as ``document_xml_data``)."""

        result = self.invoke("DocumentXMLDataAsString", documentID=require_text(document_id, "document_id"))
        return to_text(result)

    def _modified(self, operation: str, modified_since, sort_order, start_record: int, number_of_records: int, **parameters):
        result = self.invoke(
            operation,
            sortOrder=soap_value(sort_order),
            modifiedSince=as_datetime(modified_since),
            numberOfRecords=require_positive(number_of_records, "number_of_records"),
            startRecord=int(start_record),
            **parameters,
        )
        return [ArchiveDocument.from_plain(row) for row in first_rows(result, "Document")]

    def _documents(self, operation: str, document_filter: "DocumentFilter", start_record: int, number_of_records: int, **parameters):
        result = self.invoke(
            operation,
            sortOrder=soap_value(document_filter.sort_order),
            startDate=_date_or_none(document_filter.start_date),
            endDate=_date_or_none(document_filter.end_date),
            numberOfRecords=require_positive(number_of_records, "number_of_records"),
            startRecord=int(start_record),
            **parameters,
        )
        return [ArchiveDocument.from_plain(row) for row in first_rows(result, "Document")]

    @staticmethod
    def _iter(read_page: Callable[[int, int], list[ArchiveDocument]], page_size: int) -> Iterator[ArchiveDocument]:
        return iter_unique_pages(
            lambda start: read_page(start, page_size),
            first=0,
            page_size=page_size,
            next_position=lambda start, rows: start + len(rows),
        )

class _Archive:
    @property
    def _service(self) -> ArchiveService:
        return ArchiveService(self.client_credentials)


class DocumentFolderSet(_Archive, YukiRecordSet[DocumentFolder]):
    """Archive folders (one call per ``get``)."""

    def get(self) -> None:
        """``DocumentFolders``."""

        self._fill(self._service.document_folders())

    def get_counts(self, year: int) -> None:
        """``DocumentFolderCounts``: the folders with their document counts for a year."""

        self._fill(self._service.document_folder_counts(year))


class DocumentFolderTabSet(_Archive, YukiRecordSet[DocumentFolder]):
    """Tabs of one folder (``DocumentFolderTabs``, one call)."""

    def get(self, folder_id: int | str) -> None:
        self._fill(self._service.document_folder_tabs(folder_id))


class DocumentSet(_Archive, YukiRecordSet[ArchiveDocument]):
    """Archive documents. The ``get...`` methods read every page (one call per 100 documents)."""

    def get(
        self,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        *,
        sort_order: str = DocumentSortOrder.DOCUMENT_DATE_ASC,
    ) -> None:
        """``Documents``: every document, optionally of a period."""

        self._fill(self._service.iter_documents(start_date=start_date, end_date=end_date, sort_order=sort_order))

    def get_page(
        self,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        *,
        start_record: int = 0,
        number_of_records: int = 100,
        sort_order: str = DocumentSortOrder.DOCUMENT_DATE_ASC,
    ) -> None:
        """One page of ``Documents`` (one call)."""

        self._fill(
            self._service.documents(
                start_date=start_date,
                end_date=end_date,
                sort_order=sort_order,
                start_record=start_record,
                number_of_records=number_of_records,
            )
        )

    def get_in_folder(self, folder_id: int, start_date=None, end_date=None, *, sort_order: str = DocumentSortOrder.DOCUMENT_DATE_ASC) -> None:
        """``DocumentsInFolder``."""

        self._fill(self._service.iter_documents_in_folder(folder_id, start_date=start_date, end_date=end_date, sort_order=sort_order))

    def get_in_tab(self, tab_id: int, start_date=None, end_date=None, *, sort_order: str = DocumentSortOrder.DOCUMENT_DATE_ASC) -> None:
        """``DocumentsInTab``."""

        self._fill(self._service.iter_documents_in_tab(tab_id, start_date=start_date, end_date=end_date, sort_order=sort_order))

    def get_by_type(self, document_type: int, start_date=None, end_date=None, *, sort_order: str = DocumentSortOrder.DOCUMENT_DATE_ASC) -> None:
        """``DocumentsByType``."""

        self._fill(self._service.iter_documents_by_type(document_type, start_date=start_date, end_date=end_date, sort_order=sort_order))

    def get_modified_in_folder(self, folder_id: int, modified_since: date | datetime) -> None:
        """``ModifiedDocumentsInFolder``: changed since a moment, for a refresh after the bulk extract."""

        self._fill(self._service.iter_modified_documents_in_folder(folder_id, modified_since))

    def get_modified_by_type(self, document_type: int, modified_since: date | datetime) -> None:
        """``ModifiedDocumentsByType``."""

        self._fill(self._service.iter_modified_documents_by_type(document_type, modified_since))

    def get_bundle(self, document_id: str) -> None:
        """``DocumentBundle``: the documents bundled with one document (one call)."""

        self._fill(self._service.document_bundle(document_id))

    def search(
        self,
        search_text: str,
        *,
        search_option: str = DocumentSearchOption.ALL,
        folder_id: int = -1,
        tab_id: int = -1,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        start_record: int = 0,
        number_of_records: int = 100,
    ) -> None:
        """One page of ``SearchDocuments`` (one call)."""

        self._fill(
            self._service.search_documents(
                search_text,
                search_option=search_option,
                folder_id=folder_id,
                tab_id=tab_id,
                start_date=start_date,
                end_date=end_date,
                start_record=start_record,
                number_of_records=number_of_records,
            )
        )


class Document(_Archive, YukiRecord):
    """One archive document.

    ``read(id=...)`` fills the fields below (``FindDocument``, one call).
    ``file()``, ``bundle()``, ``download_url()``, ``xml_data()`` and ``ubl()``
    each cost one call and work right after ``read``, or with ``id=`` passed.
    """

    _value: ArchiveDocument | None = None

    # id is a property: it also works before read() when id= is passed.
    subject: str | None
    document_date: date | None
    amount: Decimal | None
    currency: str | None
    folder: str | None
    folder_id: int | None
    tab: str | None
    tab_id: int | None
    contact_name: str | None
    file_name: str | None
    reference: str | None
    type: str | None
    type_description: str | None
    contact_id: str | None
    vat_amount: Decimal | None
    content_type: str | None
    file_size: int | None
    created: datetime | None
    creator: str | None
    modified: datetime | None
    modifier: str | None
    fields: dict

    def __init__(self, client_credentials, administration_id: str | None = None, *, id: str | None = None):
        super().__init__(client_credentials, administration_id)
        self._id = id

    @property
    def id(self) -> str:
        if self._value is not None:
            return self._value.id
        if self._id:
            return self._id
        raise YukiError("Document is empty: call read(id=...) first or pass id=")

    def read(self, id: str) -> None:
        found = self._service.find_document(id)
        if found is None:
            raise YukiError(f"Document {id} was not found in the archive")
        self._id = id
        self._set(found)

    def file(self) -> ArchiveFile:
        """``DocumentFile``: ``file_name`` and ``data`` (bytes)."""

        return self._service.document_file(self.id)

    def binary_data(self) -> bytes:
        """``DocumentBinaryData``: the bytes without the file name."""

        return self._service.document_binary_data(self.id)

    def bundle(self) -> DocumentSet:
        """``DocumentBundle`` as a filled :class:`DocumentSet`."""

        documents = DocumentSet(self.client_credentials, self._administration_id)
        documents.get_bundle(self.id)
        return documents

    def download_url(self) -> str:
        """``DocumentDownloadUrl``."""

        return self._service.document_download_url(self.id)

    def xml_data(self) -> dict | None:
        """``DocumentXmlData``: the structured data Yuki read from the document."""

        return self._service.document_xml_data(self.id)

    def ubl(self) -> str | None:
        """``GetUBLDocument``: the UBL 2.1 XML of an invoice (needs the administration)."""

        return UblService(self.client_credentials).ubl_document(self.administration_id, self.id)
