"""Read methods for the Vat webservice (``Vat.asmx``).

The access key needs the Vat service ticked in Yuki.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from ..parsing import get, plain, to_date, to_datetime, to_decimal, to_int, to_text, unwrap_rows
from ..service import YukiService, as_datetime, require_text
from ..record import YukiRecordSet

# ``modifiedAfter`` is a required dateTime; an early date returns every return.
EVERYTHING_SINCE = datetime(1900, 1, 1)


@dataclass(frozen=True)
class VATCode:
    """One active VAT code. ``type`` is the number found on transactions as ``vat.codeType``."""

    type: int | None
    description: str | None = None
    type_description: str | None = None
    percentage: Decimal | None = None
    country: str | None = None
    start_date: date | None = None
    end_date: date | None = None

    @classmethod
    def from_plain(cls, data) -> "VATCode":
        data = plain(data) or {}
        return cls(
            type=to_int(get(data, "type")),
            description=to_text(get(data, "description")),
            type_description=to_text(get(data, "typeDescription")),
            percentage=to_decimal(get(data, "percentage")),
            country=to_text(get(data, "country")),
            start_date=to_date(get(data, "startDate")),
            end_date=to_date(get(data, "endDate")),
        )


@dataclass(frozen=True)
class VATReturnInfo:
    """A filed or open VAT return: period and status only, no grid amounts."""

    document_id: str | None
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None
    send_date: datetime | None = None
    acknowledge_date: datetime | None = None
    modified: datetime | None = None

    @classmethod
    def from_plain(cls, data) -> "VATReturnInfo":
        data = plain(data) or {}
        return cls(
            document_id=to_text(get(data, "documentID")),
            start_date=to_date(get(data, "startDate")),
            end_date=to_date(get(data, "endDate")),
            status=to_text(get(data, "status")),
            send_date=to_datetime(get(data, "sendDate")),
            acknowledge_date=to_datetime(get(data, "acknowledgeDate")),
            modified=to_datetime(get(data, "modified")),
        )


class VatService(YukiService):
    """Read data from ``Vat.asmx``."""

    service_name = "Vat"

    def active_vat_codes(self, administration_id: str) -> list[VATCode]:
        result = self.invoke(
            "ActiveVATCodesList",
            administrationID=require_text(administration_id, "administration_id"),
        )
        return [VATCode.from_plain(row) for row in unwrap_rows(result, "VATCode")]

    def vat_returns(
        self,
        administration_id: str,
        year: int,
        *,
        modified_after: date | datetime | None = None,
    ) -> list[VATReturnInfo]:
        result = self.invoke(
            "VATReturnList",
            administrationID=require_text(administration_id, "administration_id"),
            year=int(year),
            modifiedAfter=as_datetime(modified_after) if modified_after is not None else EVERYTHING_SINCE,
        )
        return [VATReturnInfo.from_plain(row) for row in unwrap_rows(result, "VATReturnInfo")]

class VATCodeSet(YukiRecordSet[VATCode]):
    """VAT codes active in the administration (``ActiveVATCodesList``, one call).

    A VAT type is not unique: type 11 (input tax) exists at 6, 12 and 21 %.
    """

    def get(self) -> None:
        self._fill(VatService(self.client_credentials).active_vat_codes(self.administration_id))


class VATReturnSet(YukiRecordSet[VATReturnInfo]):
    """Filed VAT returns of a year (``VATReturnList``, one call)."""

    def get(self, year: int, *, modified_after: date | datetime | None = None) -> None:
        self._fill(VatService(self.client_credentials).vat_returns(self.administration_id, year, modified_after=modified_after))
