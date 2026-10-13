"""Read methods for the Contact webservice.

Write operations such as ``UpdateContact`` are not wrapped.
Documentation: https://documenter.getpostman.com/view/12207912/UVCBB51L
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Iterator

from ..parsing import first_rows, get, iter_unique_pages, plain, to_bool, to_date, to_datetime, to_text
from ..service import YukiService, require_text, soap_value
from ..record import YukiRecordSet
from ..soap import Domain, discover_domains

# Yuki returns at most this many contacts per page.
CONTACT_PAGE_SIZE = 100

# ``modifiedAfter`` is a required element. An early date returns every contact.
EVERYTHING_SINCE = datetime(1900, 1, 1)


class ContactSearchOption(str, Enum):
    ALL = "All"
    NAME = "Name"
    CITY = "City"
    POSTCODE = "Postcode"
    TAG = "Tag"
    EMAIL = "Email"
    WEBSITE = "Website"
    PHONE = "Phone"
    CODE = "Code"
    COC_NUMBER = "CoCNumber"
    VAT_NUMBER = "VATNumber"
    BANK_ACCOUNT = "BankAccount"
    ID = "ID"
    CONTACT_TYPE = "ContactType"
    HID = "HID"


class ContactSortOrder(str, Enum):
    NAME = "Name"
    LAST_NAME = "LastName"
    CREATED_ASC = "CreatedAsc"
    CREATED_DESC = "CreatedDesc"
    MODIFIED_ASC = "ModifiedAsc"
    MODIFIED_DESC = "ModifiedDesc"
    HID = "HID"


class ContactActive(str, Enum):
    BOTH = "Both"
    ACTIVE = "Active"
    INACTIVE = "Inactive"


class ContactTypeFilter(str, Enum):
    CUSTOMER = "Customer"
    SUPPLIER = "Supplier"
    BOTH = "Both"
    NONE = "None"


@dataclass(frozen=True)
class Contact:
    """A contact returned by SearchContacts or GetSuppliersAndCustomers.

    The response layout is not documented; ``fields`` keeps every field Yuki
    returned, including the ones not mapped to an attribute here.
    """

    id: str
    type: str | None = None
    hid: str | None = None
    code: str | None = None
    name: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    postcode: str | None = None
    city: str | None = None
    mail_address_line_1: str | None = None
    mail_address_line_2: str | None = None
    mail_postcode: str | None = None
    mail_city: str | None = None
    country: str | None = None
    phone_home: str | None = None
    phone_work: str | None = None
    mobile_home: str | None = None
    mobile_work: str | None = None
    email_home: str | None = None
    email_work: str | None = None
    website: str | None = None
    vat_number: str | None = None
    coc_number: str | None = None
    income_tax_number: str | None = None
    created: datetime | None = None
    modified: datetime | None = None
    main_contact_person: str | None = None
    is_supplier: bool | None = None
    is_customer: bool | None = None
    iban: str | None = None
    bic: str | None = None
    tags: str | None = None
    backoffice_status: str | None = None
    fields: dict = field(default_factory=dict, compare=False, repr=False)

    @classmethod
    def from_plain(cls, data) -> "Contact":
        data = plain(data) or {}
        first_name = to_text(get(data, "FirstName"))
        middle_name = to_text(get(data, "MiddleName"))
        last_name = to_text(get(data, "LastName"))
        name = to_text(get(data, "Name", "FullName")) or " ".join(
            part for part in (first_name, middle_name, last_name) if part
        ) or None
        return cls(
            id=to_text(get(data, "ID")) or "",
            type=to_text(get(data, "Type")),
            hid=to_text(get(data, "HID")),
            code=to_text(get(data, "Code")),
            name=name,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            address_line_1=to_text(get(data, "AddressLine_1")),
            address_line_2=to_text(get(data, "AddressLine_2")),
            postcode=to_text(get(data, "Postcode")),
            city=to_text(get(data, "City")),
            mail_address_line_1=to_text(get(data, "MailAddressLine_1")),
            mail_address_line_2=to_text(get(data, "MailAddressLine_2")),
            mail_postcode=to_text(get(data, "MailPostcode")),
            mail_city=to_text(get(data, "MailCity")),
            country=to_text(get(data, "Country")),
            phone_home=to_text(get(data, "PhoneHome")),
            phone_work=to_text(get(data, "PhoneWork")),
            mobile_home=to_text(get(data, "MobileHome")),
            mobile_work=to_text(get(data, "MobileWork")),
            email_home=to_text(get(data, "EmailHome")),
            email_work=to_text(get(data, "EmailWork")),
            website=to_text(get(data, "Website")),
            vat_number=to_text(get(data, "VATNumber")),
            coc_number=to_text(get(data, "CoCNumber")),
            income_tax_number=to_text(get(data, "IncomeTaxNumber")),
            created=to_datetime(get(data, "Created")),
            modified=to_datetime(get(data, "Modified")),
            main_contact_person=to_text(get(data, "MainContactPerson")),
            is_supplier=to_bool(get(data, "IsSupplier")),
            is_customer=to_bool(get(data, "IsCustomer")),
            iban=to_text(get(data, "IBAN")),
            bic=to_text(get(data, "BIC")),
            tags=to_text(get(data, "Tags")),
            backoffice_status=to_text(get(data, "BackofficeStatus")),
            fields=data if isinstance(data, dict) else {},
        )


@dataclass(frozen=True)
class Administration:
    """An administration visible to the current session."""

    id: str
    name: str | None = None
    address_line: str | None = None
    address_line_2: str | None = None
    postcode: str | None = None
    city: str | None = None
    country: str | None = None
    coc_number: str | None = None
    vat_number: str | None = None
    start_date: date | None = None
    domain_id: str | None = None
    active: bool | None = None
    internal_customer_code: str | None = None

    @classmethod
    def from_plain(cls, data) -> "Administration":
        data = plain(data) or {}
        return cls(
            id=to_text(get(data, "ID")) or "",
            name=to_text(get(data, "Name")),
            address_line=to_text(get(data, "AddressLine")),
            address_line_2=to_text(get(data, "AddressLine_2")),
            postcode=to_text(get(data, "Postcode")),
            city=to_text(get(data, "City")),
            country=to_text(get(data, "Country")),
            coc_number=to_text(get(data, "CoCNumber")),
            vat_number=to_text(get(data, "VATNumber")),
            start_date=to_date(get(data, "StartDate")),
            domain_id=to_text(get(data, "DomainID")),
            active=to_bool(get(data, "Active")),
            internal_customer_code=to_text(get(data, "InternalCustomerCode")),
        )


@dataclass(frozen=True)
class SupportedLanguage:
    code: str
    description: str | None = None
    native_description: str | None = None

    @classmethod
    def from_plain(cls, data) -> "SupportedLanguage":
        data = plain(data) or {}
        return cls(
            code=to_text(get(data, "Code")) or "",
            description=to_text(get(data, "Description")),
            native_description=to_text(get(data, "NativeDescription")),
        )


class ContactService(YukiService):
    """Read data from ``Contact.asmx``."""

    service_name = "Contact"

    def search(
        self,
        search_value: str = "",
        *,
        search_option: str = ContactSearchOption.NAME,
        sort_order: str = ContactSortOrder.NAME,
        active: str = ContactActive.BOTH,
        page_number: int = 1,
        modified_after: datetime | None = None,
        domain_id: str | None = None,
    ) -> list[Contact]:
        """Search contacts. Yuki returns at most 100 rows per page."""

        return self._contacts(
            "SearchContacts",
            search_value,
            search_option=search_option,
            sort_order=sort_order,
            active=active,
            page_number=page_number,
            modified_after=modified_after,
            domain_id=domain_id,
        )

    def suppliers_and_customers(
        self,
        search_value: str = "",
        *,
        contact_type: str = ContactTypeFilter.BOTH,
        search_option: str = ContactSearchOption.NAME,
        sort_order: str = ContactSortOrder.NAME,
        active: str = ContactActive.ACTIVE,
        page_number: int = 1,
        modified_after: datetime | None = None,
        domain_id: str | None = None,
    ) -> list[Contact]:
        """Search suppliers and customers. Yuki returns at most 100 rows per page."""

        return self._contacts(
            "GetSuppliersAndCustomers",
            search_value,
            search_option=search_option,
            sort_order=sort_order,
            active=active,
            page_number=page_number,
            modified_after=modified_after,
            domain_id=domain_id,
            contactType=soap_value(contact_type),
        )

    def iter_suppliers_and_customers(
        self,
        contact_type: str = ContactTypeFilter.BOTH,
        *,
        active: str = ContactActive.BOTH,
        search_option: str = ContactSearchOption.ALL,
        search_value: str = "",
        sort_order: str = ContactSortOrder.HID,
        modified_after: datetime | None = None,
        domain_id: str | None = None,
        max_pages: int | None = None,
    ) -> Iterator[Contact]:
        """Yield every supplier and/or customer, one call per page of 100.

        Stops on an empty page, a short page, or a page without new ids. Each
        contact id is yielded once. ``contact_type`` cannot be empty: Yuki rejects
        the whole request.
        """

        yield from self._iter_pages(
            lambda page: self.suppliers_and_customers(
                search_value,
                contact_type=contact_type,
                search_option=search_option,
                sort_order=sort_order,
                active=active,
                page_number=page,
                modified_after=modified_after,
                domain_id=domain_id,
            ),
            max_pages,
        )

    def iter_contacts(
        self,
        *,
        active: str = ContactActive.BOTH,
        search_option: str = ContactSearchOption.ALL,
        search_value: str = "",
        sort_order: str = ContactSortOrder.HID,
        modified_after: datetime | None = None,
        domain_id: str | None = None,
        max_pages: int | None = None,
    ) -> Iterator[Contact]:
        """Yield every contact of the domain (``SearchContacts``), one call per page of 100."""

        yield from self._iter_pages(
            lambda page: self.search(
                search_value,
                search_option=search_option,
                sort_order=sort_order,
                active=active,
                page_number=page,
                modified_after=modified_after,
                domain_id=domain_id,
            ),
            max_pages,
        )

    @staticmethod
    def _iter_pages(read_page, max_pages: int | None) -> Iterator[Contact]:
        # Sorted on HID by default, so pages stay stable while they are read.
        return iter_unique_pages(
            read_page,
            first=1,
            page_size=CONTACT_PAGE_SIZE,
            next_position=lambda page_number, rows: page_number + 1,
            max_pages=max_pages,
        )

    def administrations(self) -> list[Administration]:
        return self.read_rows("Administrations", "Administration", Administration.from_plain)

    def administrations_with_internal_customer_code(self) -> list[Administration]:
        return self.read_rows(
            "AdministrationsWithInternalCustomerCode",
            "Administration",
            Administration.from_plain,
        )

    def administration_id(self, administration_name: str) -> str:
        """Return the administration id for an administration name."""

        result = self.invoke(
            "AdministrationID",
            administrationName=require_text(administration_name, "administration_name"),
        )
        return str(result or "").strip()

    def companies(self) -> list[Administration]:
        result = self.invoke("Companies")
        return [Administration.from_plain(row) for row in first_rows(result, "Company", "Administration")]

    def language(self) -> str:
        """Return the language of the current session, for example ``nl-be``."""

        return str(self.invoke("Language") or "").strip()

    def supported_languages(self) -> list[SupportedLanguage]:
        return self.read_rows("SupportedLanguages", "Language", SupportedLanguage.from_plain)

    def _contacts(self, operation: str, search_value: str, *, search_option, sort_order, active, page_number, modified_after, domain_id, **extra) -> list[Contact]:
        selected_domain = require_text(domain_id or self.client_credentials.domain_id, "domain_id")
        return self.read_rows(
            operation,
            "Contact",
            Contact.from_plain,
            domainID=selected_domain,
            searchOption=soap_value(search_option),
            searchValue=search_value or "",
            sortOrder=soap_value(sort_order),
            modifiedAfter=modified_after or EVERYTHING_SINCE,
            active=soap_value(active),
            pageNumber=page_number,
            **extra,
        )

class _Contact:
    @property
    def _service(self) -> ContactService:
        return ContactService(self.client_credentials)


class DomainSet(YukiRecordSet[Domain]):
    """Domains of the access key.

    ``get`` needs only ``api_key`` and ``region`` (``Authenticate`` + ``Domains``, two calls):
    use it to find the ``domain_id`` to store. ``get_current`` holds the domain the stored
    session is bound to (``GetCurrentDomain``).
    """

    def get(self) -> None:
        """``Domains``."""

        credentials = self.client_credentials
        self._fill(
            discover_domains(
                credentials.api_key,
                credentials.region,
                debug=credentials.debug,
                on_call=getattr(credentials, "count_call", None),
            )
        )

    def get_current(self) -> None:
        """``GetCurrentDomain``: the domain of the stored session (authenticates when needed)."""

        self._fill([self.client_credentials.current_domain()])


class AdministrationSet(_Contact, YukiRecordSet[Administration]):
    """Administrations of the domain (one call per ``get``)."""

    def get(self) -> None:
        """``Administrations``."""

        self._fill(self._service.administrations())

    def get_with_internal_customer_code(self) -> None:
        """``AdministrationsWithInternalCustomerCode``."""

        self._fill(self._service.administrations_with_internal_customer_code())

    def get_companies(self) -> None:
        """``Companies``."""

        self._fill(self._service.companies())


class ContactSet(_Contact, YukiRecordSet[Contact]):
    """Contacts of the domain. Contacts belong to the domain, not to one administration.

    ``get`` reads every contact, also the administration itself and Yuki's own
    contacts; ``get_customers`` / ``get_suppliers`` only those with that role.
    Both read every page (one call per 100 contacts).
    """

    def get(self, *, active: str = ContactActive.BOTH, modified_after: datetime | None = None, max_pages: int | None = None) -> None:
        """``SearchContacts`` over all pages."""

        self._fill(self._service.iter_contacts(active=active, modified_after=modified_after, max_pages=max_pages))

    def get_customers(self, *, active: str = ContactActive.BOTH, modified_after: datetime | None = None, max_pages: int | None = None) -> None:
        """``GetSuppliersAndCustomers`` for customers, over all pages."""

        self._fill(
            self._service.iter_suppliers_and_customers(
                ContactTypeFilter.CUSTOMER, active=active, modified_after=modified_after, max_pages=max_pages
            )
        )

    def get_suppliers(self, *, active: str = ContactActive.BOTH, modified_after: datetime | None = None, max_pages: int | None = None) -> None:
        """``GetSuppliersAndCustomers`` for suppliers, over all pages."""

        self._fill(
            self._service.iter_suppliers_and_customers(
                ContactTypeFilter.SUPPLIER, active=active, modified_after=modified_after, max_pages=max_pages
            )
        )

    def search(
        self,
        search_value: str = "",
        *,
        search_option: str = ContactSearchOption.NAME,
        sort_order: str = ContactSortOrder.NAME,
        active: str = ContactActive.BOTH,
        modified_after: datetime | None = None,
        page_number: int = 1,
    ) -> None:
        """One page of ``SearchContacts`` (one call)."""

        self._fill(
            self._service.search(
                search_value,
                search_option=search_option,
                sort_order=sort_order,
                active=active,
                modified_after=modified_after,
                page_number=page_number,
            )
        )

    def read(self, ids: list[str]) -> None:
        """The contacts with these Yuki ids (one call per id)."""

        found = []
        for contact_id in ids:
            found.extend(
                contact
                for contact in self._service.search(contact_id, search_option=ContactSearchOption.ID)
                if contact.id == contact_id
            )
        self._fill(found)


class LanguageSet(_Contact, YukiRecordSet[SupportedLanguage]):
    """Languages Yuki supports (``SupportedLanguages``, one call)."""

    def get(self) -> None:
        self._fill(self._service.supported_languages())
