"""Read methods for the Contact webservice.

Write operations such as ``UpdateContact`` are not wrapped.
Documentation: https://documenter.getpostman.com/view/12207912/UVCBB51L
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .service import YukiService, attribute, bool_text, require_text, row_elements, soap_value, text


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
    """A contact returned by SearchContacts or GetSuppliersAndCustomers."""

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
    email_work: str | None = None
    website: str | None = None
    vat_number: str | None = None
    coc_number: str | None = None
    income_tax_number: str | None = None
    created: str | None = None
    modified: str | None = None
    main_contact_person: str | None = None
    is_supplier: bool | None = None
    is_customer: bool | None = None
    iban: str | None = None
    bic: str | None = None
    tags: str | None = None
    backoffice_status: str | None = None

    @classmethod
    def from_element(cls, element) -> "Contact":
        first_name = text(element, "FirstName")
        middle_name = text(element, "MiddleName")
        last_name = text(element, "LastName")
        name = text(element, "Name") or " ".join(
            part for part in (first_name, middle_name, last_name) if part
        ) or None
        return cls(
            id=attribute(element, "ID") or "",
            type=text(element, "Type"),
            hid=text(element, "HID"),
            code=text(element, "Code"),
            name=name,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            address_line_1=text(element, "AddressLine_1"),
            address_line_2=text(element, "AddressLine_2"),
            postcode=text(element, "Postcode"),
            city=text(element, "City"),
            mail_address_line_1=text(element, "MailAddressLine_1"),
            mail_address_line_2=text(element, "MailAddressLine_2"),
            mail_postcode=text(element, "MailPostcode"),
            mail_city=text(element, "MailCity"),
            country=text(element, "Country"),
            phone_home=text(element, "PhoneHome"),
            email_work=text(element, "EMailWork"),
            website=text(element, "Website"),
            vat_number=text(element, "VATNumber"),
            coc_number=text(element, "CoCNumber"),
            income_tax_number=text(element, "IncomeTaxNumber"),
            created=text(element, "Created"),
            modified=text(element, "Modified"),
            main_contact_person=text(element, "MainContactPerson"),
            is_supplier=bool_text(element, "IsSupplier"),
            is_customer=bool_text(element, "IsCustomer"),
            iban=text(element, "IBAN"),
            bic=text(element, "BIC"),
            tags=text(element, "Tags"),
            backoffice_status=text(element, "BackofficeStatus"),
        )


@dataclass(frozen=True)
class Administration:
    """An administration visible to the current session."""

    id: str
    name: str | None = None
    address_line: str | None = None
    postcode: str | None = None
    city: str | None = None
    country: str | None = None
    coc_number: str | None = None
    vat_number: str | None = None
    start_date: str | None = None
    domain_id: str | None = None
    active: bool | None = None
    internal_customer_code: str | None = None

    @classmethod
    def from_element(cls, element) -> "Administration":
        return cls(
            id=attribute(element, "ID") or "",
            name=text(element, "Name"),
            address_line=text(element, "AddressLine"),
            postcode=text(element, "Postcode"),
            city=text(element, "City"),
            country=text(element, "Country"),
            coc_number=text(element, "CoCNumber"),
            vat_number=text(element, "VATNumber"),
            start_date=text(element, "StartDate"),
            domain_id=text(element, "DomainID"),
            active=bool_text(element, "Active"),
            internal_customer_code=text(element, "InternalCustomerCode"),
        )


@dataclass(frozen=True)
class SupportedLanguage:
    code: str
    description: str | None = None
    native_description: str | None = None

    @classmethod
    def from_element(cls, element) -> "SupportedLanguage":
        return cls(
            code=attribute(element, "Code") or "",
            description=text(element, "Description"),
            native_description=text(element, "NativeDescription"),
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

    def administrations(self) -> list[Administration]:
        return self.read_rows("Administrations", "Administration", Administration.from_element)

    def administrations_with_internal_customer_code(self) -> list[Administration]:
        return self.read_rows(
            "AdministrationsWithInternalCustomerCode",
            "Administration",
            Administration.from_element,
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
        rows = row_elements(result, "Company") or row_elements(result, "Administration")
        return [Administration.from_element(row) for row in rows]

    def language(self) -> str:
        """Return the language of the current session, for example ``nl-be``."""

        return str(self.invoke("Language") or "").strip()

    def supported_languages(self) -> list[SupportedLanguage]:
        return self.read_rows("SupportedLanguages", "Language", SupportedLanguage.from_element)

    def _contacts(self, operation: str, search_value: str, *, search_option, sort_order, active, page_number, modified_after, domain_id, **extra) -> list[Contact]:
        selected_domain = require_text(domain_id or self.client_credentials.domain_id, "domain_id")
        return self.read_rows(
            operation,
            "Contact",
            Contact.from_element,
            domainID=selected_domain,
            searchOption=soap_value(search_option),
            searchValue=search_value or "",
            sortOrder=soap_value(sort_order),
            modifiedAfter=modified_after,
            active=soap_value(active),
            pageNumber=page_number,
            **extra,
        )
