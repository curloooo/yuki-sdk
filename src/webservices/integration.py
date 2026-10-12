"""Read methods for the Integration webservice (``Integration.asmx``).

This service names its parameters ``sessionId`` and ``administrationId``
(lower-case ``d``), unlike the other services.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..parsing import get, plain, to_bytes, to_text
from ..service import YukiService, require_text
from ..record import YukiRecord


@dataclass(frozen=True)
class AdministrationData:
    """Company details of an administration, beyond what ``Administrations`` returns."""

    company_name: str | None = None
    description: str | None = None
    main_contact_name: str | None = None
    main_contact_email: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    postcode: str | None = None
    city: str | None = None
    country: str | None = None
    email_outgoing_invoices: str | None = None
    phone_work: str | None = None
    mobile_work: str | None = None
    fax_work: str | None = None
    iban: str | None = None
    bank_account_name: str | None = None
    coc_number: str | None = None
    vat_number: str | None = None
    company_logo: bytes | None = field(default=None, repr=False)
    navigation_logo: bytes | None = field(default=None, repr=False)

    @classmethod
    def from_plain(cls, data) -> "AdministrationData":
        data = plain(data) or {}
        return cls(
            company_name=to_text(get(data, "CompanyName")),
            description=to_text(get(data, "Description")),
            main_contact_name=to_text(get(data, "MainContactName")),
            main_contact_email=to_text(get(data, "MainContactEmail")),
            address_line_1=to_text(get(data, "AddressLine_1")),
            address_line_2=to_text(get(data, "AddressLine_2")),
            postcode=to_text(get(data, "Postcode")),
            city=to_text(get(data, "City")),
            country=to_text(get(data, "Country")),
            email_outgoing_invoices=to_text(get(data, "EmailOutgoingInvoices")),
            phone_work=to_text(get(data, "PhoneWork")),
            mobile_work=to_text(get(data, "MobileWork")),
            fax_work=to_text(get(data, "FaxWork")),
            iban=to_text(get(data, "IBAN")),
            bank_account_name=to_text(get(data, "BankAccountName")),
            coc_number=to_text(get(data, "CoCNumber")),
            vat_number=to_text(get(data, "VATNumber")),
            company_logo=_logo(get(data, "CompanyLogoB64")),
            navigation_logo=_logo(get(data, "NavigationLogoB64")),
        )


def _logo(value) -> bytes | None:
    # Declared as <any> in the WSDL; the content is base64 text.
    try:
        return to_bytes(value)
    except ValueError:
        return None


class IntegrationService(YukiService):
    """Read data from ``Integration.asmx``."""

    service_name = "Integration"
    session_parameter = "sessionId"

    def administration_data(self, administration_id: str) -> AdministrationData:
        result = self.invoke(
            "GetAdministrationData",
            administrationId=require_text(administration_id, "administration_id"),
        )
        return AdministrationData.from_plain(result)


class Company(YukiRecord):
    """Company data of the administration (``GetAdministrationData``, one call)."""

    _value: AdministrationData | None = None

    company_name: str | None
    description: str | None
    main_contact_name: str | None
    main_contact_email: str | None
    address_line_1: str | None
    address_line_2: str | None
    postcode: str | None
    city: str | None
    country: str | None
    email_outgoing_invoices: str | None
    phone_work: str | None
    mobile_work: str | None
    fax_work: str | None
    iban: str | None
    bank_account_name: str | None
    coc_number: str | None
    vat_number: str | None
    company_logo: bytes | None
    navigation_logo: bytes | None

    def get(self) -> None:
        self._set(IntegrationService(self.client_credentials).administration_data(self.administration_id))


