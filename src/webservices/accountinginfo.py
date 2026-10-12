"""Read methods for the AccountingInfo webservice.

Every operation here is typed in the WSDL, so zeep returns objects. The parsers
read them through :func:`yuki_sdk.parsing.plain`, which also accepts lxml
elements and plain dicts (tests, stored snapshots).

``GetGLAccountScheme`` keeps two Yuki spellings in the payload: ``descripton``
and ``deductableVATPercentage``. The Python attributes are ``description`` and
``deductible_vat_percentage``.

``GetTransactions`` is the bulk source for journal lines. It is paged with
``numberOfRecords`` / ``startRecord``. Whether ``startRecord`` counts from 0 or
1 is not documented, so :meth:`AccountingInfoService.iter_transactions` moves
on by the page length and drops ids it has already returned: an overlap of one
record is harmless, a gap is impossible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum, IntEnum
from typing import Iterator

from ..parsing import (
    get,
    iter_unique_pages,
    plain,
    to_amount,
    to_bool,
    to_bytes,
    to_date,
    to_datetime,
    to_decimal,
    to_int,
    to_text,
    unwrap_rows,
)
from ..service import YukiService, as_datetime, require_positive, require_text, soap_value
from ..exceptions import YukiError
from ..record import YukiRecord, YukiRecordSet

# Element names of the optional groups of a ``Transaction``. Yuki does not
# document the accepted ``dataGroups`` values; these are the names in the WSDL.
DEFAULT_DATA_GROUPS = "contact,document,documentProcessed,documentMatched,foreignCurrency,vat,project"
DEFAULT_PAGE_SIZE = 100


class ProjectSearchOption(str, Enum):
    ALL = "All"
    COMPANY = "Company"
    CODE = "Code"
    DESCRIPTION = "Description"


class FinancialMode(IntEnum):
    """``financialMode`` of AccountingInfo reads."""

    COMMERCIAL = 0
    FISCAL = 1


@dataclass(frozen=True)
class TransactionContact:
    id: str | None = None
    hid: int | None = None
    full_name: str | None = None
    zip_code: str | None = None
    country: str | None = None
    contact_code: str | None = None
    coc_number: str | None = None
    vat_number: str | None = None

    @classmethod
    def from_plain(cls, data) -> "TransactionContact | None":
        # Lines without a contact (a year-end correction, say) carry an empty
        # contact with HID 0 instead of none.
        if not isinstance(data, dict) or not (to_text(get(data, "id", "ID")) or to_text(get(data, "fullName"))):
            return None
        return cls(
            id=to_text(get(data, "id", "ID")),
            hid=to_int(get(data, "HID")),
            full_name=to_text(get(data, "fullName")),
            zip_code=to_text(get(data, "zipCode")),
            country=to_text(get(data, "country")),
            contact_code=to_text(get(data, "contactCode")),
            coc_number=to_text(get(data, "CoCNumber")),
            vat_number=to_text(get(data, "VATNumber")),
        )


@dataclass(frozen=True)
class TransactionDocumentInfo:
    id: str | None = None
    hid: int | None = None
    reference: str | None = None
    type: str | None = None
    type_description: str | None = None
    folder_id: int | None = None
    folder: str | None = None
    folder_tab_id: int | None = None
    folder_tab: str | None = None
    created: datetime | None = None
    modified: datetime | None = None
    upload_method: str | None = None

    @classmethod
    def from_plain(cls, data) -> "TransactionDocumentInfo | None":
        if not isinstance(data, dict) or not any(value is not None for value in data.values()):
            return None
        return cls(
            id=to_text(get(data, "id", "ID")),
            hid=to_int(get(data, "HID")),
            reference=to_text(get(data, "reference")),
            type=to_text(get(data, "type")),
            type_description=to_text(get(data, "typeDescription")),
            folder_id=to_int(get(data, "folderId")),
            folder=to_text(get(data, "folder")),
            folder_tab_id=to_int(get(data, "folderTabId")),
            folder_tab=to_text(get(data, "folderTab")),
            created=to_datetime(get(data, "created")),
            modified=to_datetime(get(data, "modified")),
            upload_method=to_text(get(data, "uploadMethod")),
        )


@dataclass(frozen=True)
class Transaction:
    """One general-ledger line from ``GetTransactions``.

    ``amount`` is signed in the administration currency (positive = debit).
    The optional groups are ``None`` when Yuki did not return them.
    """

    id: str
    hid: str | None = None
    date: date | None = None
    description: str | None = None
    amount: Decimal | None = None
    gl_account_code: str | None = None
    contact: TransactionContact | None = None
    document: TransactionDocumentInfo | None = None
    processed_date: datetime | None = None
    processed_by: str | None = None
    matched_date: datetime | None = None
    matched_by: str | None = None
    currency: str | None = None
    amount_currency: Decimal | None = None
    currency_rate: Decimal | None = None
    vat_code_type: int | None = None
    vat_description: str | None = None
    vat_percentage: Decimal | None = None
    project_code: str | None = None
    project_description: str | None = None

    @property
    def is_matched(self) -> bool:
        return self.matched_date is not None

    @classmethod
    def from_plain(cls, data) -> "Transaction":
        data = plain(data) or {}
        processed = get(data, "documentProcessed") or {}
        matched = get(data, "documentMatched") or {}
        currency = get(data, "foreignCurrency") or {}
        vat = get(data, "vat") or {}
        project = get(data, "project") or {}
        return cls(
            id=to_text(get(data, "id")) or "",
            hid=to_text(get(data, "hID")),
            date=to_date(get(data, "transactionDate")),
            description=to_text(get(data, "description")),
            amount=to_decimal(get(data, "amount")),
            gl_account_code=to_text(get(data, "glAccountCode")),
            contact=TransactionContact.from_plain(get(data, "contact")),
            document=TransactionDocumentInfo.from_plain(get(data, "document")),
            processed_date=to_datetime(get(processed, "processedDate")),
            processed_by=to_text(get(processed, "processedBy")),
            matched_date=to_datetime(get(matched, "matchDate")),
            matched_by=to_text(get(matched, "matchedBy")),
            currency=to_text(get(currency, "currency")),
            amount_currency=to_decimal(get(currency, "amountFC")),
            currency_rate=to_decimal(get(currency, "rate")),
            vat_code_type=to_int(get(vat, "codeType")),
            vat_description=to_text(get(vat, "codeDescription")),
            vat_percentage=to_decimal(get(vat, "codePercentage")),
            project_code=to_text(get(project, "code")),
            project_description=to_text(get(project, "description")),
        )


@dataclass(frozen=True)
class TransactionInfo:
    """One line from ``GetTransactionDetails`` (flat, not paged)."""

    id: str
    hid: str | None = None
    date: date | None = None
    description: str | None = None
    amount: Decimal | None = None
    amount_currency: Decimal | None = None
    currency_rate: Decimal | None = None
    currency: str | None = None
    tax_code_description: str | None = None
    full_name: str | None = None
    coc_number: str | None = None
    vat_number: str | None = None
    contact_hid: int | None = None
    contact_code: str | None = None
    contact_country: str | None = None
    contact_zipcode: str | None = None
    contact_id: str | None = None
    project: str | None = None
    project_code: str | None = None
    gl_account_code: str | None = None
    document_id: str | None = None
    document_reference: str | None = None
    document_type: str | None = None
    document_folder: str | None = None
    document_folder_tab: str | None = None
    period_id: str | None = None
    company: str | None = None
    mutation_user: str | None = None

    @classmethod
    def from_plain(cls, data) -> "TransactionInfo":
        data = plain(data) or {}
        return cls(
            id=to_text(get(data, "id")) or "",
            hid=to_text(get(data, "hID")),
            date=to_date(get(data, "transactionDate")),
            description=to_text(get(data, "description")),
            amount=to_decimal(get(data, "transactionAmount")),
            amount_currency=to_decimal(get(data, "transactionAmountForeignCurrency")),
            currency_rate=to_decimal(get(data, "currencyRate")),
            currency=to_text(get(data, "currency")),
            tax_code_description=to_text(get(data, "taxCodeDescription")),
            full_name=to_text(get(data, "fullName")),
            coc_number=to_text(get(data, "CoCNumber")),
            vat_number=to_text(get(data, "VATNumber")),
            contact_hid=to_int(get(data, "contactHID")),
            contact_code=to_text(get(data, "contactCode")),
            contact_country=to_text(get(data, "contactCountry")),
            contact_zipcode=to_text(get(data, "contactZipcode")),
            contact_id=to_text(get(data, "contactID")),
            project=to_text(get(data, "project")),
            project_code=to_text(get(data, "projectCode")),
            gl_account_code=to_text(get(data, "glAccountCode")),
            document_id=to_text(get(data, "documentID")),
            document_reference=to_text(get(data, "documentReference")),
            document_type=to_text(get(data, "documentType")),
            document_folder=to_text(get(data, "documentFolder")),
            document_folder_tab=to_text(get(data, "documentFolderTab")),
            period_id=to_text(get(data, "periodId")),
            company=to_text(get(data, "company")),
            mutation_user=to_text(get(data, "mutationUser")),
        )


@dataclass(frozen=True)
class AdministrationPeriod:
    """``GetPeriodDateTable``: the start of a financial year."""

    name: str | None = None
    period: date | None = None
    whole_period: str | None = None
    iso8601_period: bool | None = None

    @classmethod
    def from_plain(cls, data) -> "AdministrationPeriod":
        data = plain(data) or {}
        return cls(
            name=to_text(get(data, "name")),
            period=to_date(get(data, "period")),
            whole_period=to_text(get(data, "wholePeriod")),
            iso8601_period=to_bool(get(data, "ISO8601Period")),
        )


@dataclass(frozen=True)
class AccountStartBalance:
    """``GetStartBalanceByGlAccount``: opening balance of one account."""

    gl_account_code: str
    start_balance: Decimal | None = None
    description: str | None = None
    # The WSDL types the balance as text; kept as sent in case its notation surprises.
    start_balance_text: str | None = None

    @classmethod
    def from_plain(cls, data) -> "AccountStartBalance":
        data = plain(data) or {}
        return cls(
            gl_account_code=to_text(get(data, "accountID")) or "",
            start_balance=to_amount(get(data, "startBalance")),
            description=to_text(get(data, "accountDescription")),
            start_balance_text=to_text(get(data, "startBalance")),
        )


@dataclass(frozen=True)
class TransactionDocumentFile:
    """``GetTransactionDocument``: the archived file behind a transaction."""

    file_name: str | None
    data: bytes | None

    @classmethod
    def from_plain(cls, data) -> "TransactionDocumentFile":
        data = plain(data) or {}
        return cls(file_name=to_text(get(data, "fileName")), data=to_bytes(get(data, "filedata")))


@dataclass(frozen=True)
class DefaultValue:
    """One rule of ``GetContactDefaultValues``: when the input matches, use the output."""

    document_type: str | None = None
    contact_name: str | None = None
    priority: int | None = None
    amount: str | None = None
    currency: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    text: str | None = None
    gl_account: str | None = None
    vat_code: str | None = None
    payment_method: str | None = None
    payment_term: str | None = None
    created: datetime | None = None

    @classmethod
    def from_plain(cls, data) -> "DefaultValue":
        data = plain(data) or {}
        inputs = get(data, "InputFields") or {}
        outputs = get(data, "OutputFields") or {}
        return cls(
            document_type=to_text(get(inputs, "DocumentType")),
            contact_name=to_text(get(inputs, "ContactName")),
            priority=to_int(get(inputs, "Priority")),
            amount=to_text(get(inputs, "Amount")),
            currency=to_text(get(inputs, "Currency")),
            start_date=to_text(get(inputs, "StartDate")),
            end_date=to_text(get(inputs, "EndDate")),
            text=to_text(get(inputs, "Text")),
            gl_account=to_text(get(outputs, "GLAccount")),
            vat_code=to_text(get(outputs, "VATCode")),
            payment_method=to_text(get(outputs, "PaymentMethod")),
            payment_term=to_text(get(outputs, "PaymentTerm")),
            created=to_datetime(get(data, "Created")),
        )


@dataclass(frozen=True)
class ContactDefaultValues:
    contact_id: str
    contact_name: str | None = None
    default_bank_account: str | None = None
    default_values: tuple[DefaultValue, ...] = field(default_factory=tuple)

    @classmethod
    def from_plain(cls, data) -> "ContactDefaultValues":
        data = plain(data) or {}
        return cls(
            contact_id=to_text(get(data, "ContactId")) or "",
            contact_name=to_text(get(data, "ContactName")),
            default_bank_account=to_text(get(data, "DefaultBankAccount")),
            default_values=tuple(
                DefaultValue.from_plain(row) for row in unwrap_rows(get(data, "DefaultValues"), "DefaultValue")
            ),
        )


@dataclass(frozen=True)
class PaymentMethod:
    id: int | None
    description: str | None = None

    @classmethod
    def from_plain(cls, data) -> "PaymentMethod":
        data = plain(data) or {}
        return cls(id=to_int(get(data, "ID")), description=to_text(get(data, "Description")))


@dataclass(frozen=True)
class Project:
    """A Yuki project (the ``project`` group on a transaction refers to its code)."""

    id: str | None
    code: str | None = None
    hid: int | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    company: str | None = None
    contact: str | None = None
    contact_id: str | None = None
    tags: str | None = None
    budget_sales: Decimal | None = None
    budget_purchase: Decimal | None = None

    @classmethod
    def from_plain(cls, data) -> "Project":
        data = plain(data) or {}
        return cls(
            id=to_text(get(data, "id")),
            code=to_text(get(data, "code")),
            hid=to_int(get(data, "HID")),
            description=to_text(get(data, "description")),
            start_date=to_date(get(data, "startDate")),
            end_date=to_date(get(data, "endDate")),
            company=to_text(get(data, "company")),
            contact=to_text(get(data, "contact")),
            contact_id=to_text(get(data, "contactID")),
            tags=to_text(get(data, "tags")),
            budget_sales=to_decimal(get(data, "budgetSales")),
            budget_purchase=to_decimal(get(data, "budgetPurchase")),
        )


@dataclass(frozen=True)
class ProjectBalance:
    gl_account_code: str | None
    project: str | None = None
    project_code: str | None = None
    amount: Decimal | None = None

    @classmethod
    def from_plain(cls, data) -> "ProjectBalance":
        data = plain(data) or {}
        return cls(
            gl_account_code=to_text(get(data, "glAccountCode")),
            project=to_text(get(data, "project")),
            project_code=to_text(get(data, "projectCode")),
            amount=to_decimal(get(data, "amount")),
        )


@dataclass(frozen=True)
class RGSEntry:
    """A Yuki account with its Dutch RGS reference code (NL administrations)."""

    yuki_code: str | None
    yuki_is_enabled: str | None = None  # text in the WSDL
    yuki_description: str | None = None
    rgs_reference_code: str | None = None
    rgs_description: str | None = None
    rgs_flip_code: str | None = None

    @classmethod
    def from_plain(cls, data) -> "RGSEntry":
        data = plain(data) or {}
        return cls(
            yuki_code=to_text(get(data, "YukiCode")),
            yuki_is_enabled=to_text(get(data, "YukiIsEnabled")),
            yuki_description=to_text(get(data, "YukiDescription")),
            rgs_reference_code=to_text(get(data, "RgsReferenceCode")),
            rgs_description=to_text(get(data, "RgsDescription")),
            rgs_flip_code=to_text(get(data, "RgsFlipCode")),
        )


@dataclass(frozen=True)
class GLAccount:
    """One account in a Yuki general ledger scheme."""

    code: str
    account_type: int
    subtype: int
    is_enabled: bool
    description: str
    description_nl: str | None = None
    description_fr: str | None = None
    description_en: str | None = None
    is_vat_applicable: bool = False
    deductible_vat_percentage: Decimal = Decimal("0")
    professional_percentage: Decimal = Decimal("0")


def parse_gl_accounts(result) -> list[GLAccount]:
    """Turn a ``GetGLAccountScheme`` payload into :class:`GLAccount` values.

    Accepts the zeep result (a list of ``GlAccount`` or the array wrapper), an
    lxml element, or plain dicts.
    """

    accounts: list[GLAccount] = []
    for item in unwrap_rows(result, "GlAccount"):
        code = to_text(get(item, "code"))
        if not code:
            continue
        accounts.append(
            GLAccount(
                code=code,
                account_type=to_int(get(item, "type")) or 0,
                subtype=to_int(get(item, "subtype")) or 0,
                is_enabled=bool(to_bool(get(item, "isEnabled"))),
                description=to_text(get(item, "descripton", "description")) or "",
                description_nl=to_text(get(item, "descriptionNL")),
                description_fr=to_text(get(item, "descriptionFR")),
                description_en=to_text(get(item, "descriptionEN")),
                is_vat_applicable=bool(to_bool(get(item, "isVATApplicable"))),
                deductible_vat_percentage=to_decimal(get(item, "deductableVATPercentage")) or Decimal("0"),
                professional_percentage=to_decimal(get(item, "professionalPercentage")) or Decimal("0"),
            )
        )
    return accounts


class AccountingInfoService(YukiService):
    """Read data from ``AccountingInfo.asmx``."""

    service_name = "AccountingInfo"

    def gl_account_scheme(self, administration_id: str) -> list[GLAccount]:
        result = self.invoke(
            "GetGLAccountScheme",
            administrationID=require_text(administration_id, "administration_id"),
        )
        return parse_gl_accounts(result)

    def transactions(
        self,
        administration_id: str,
        start_date: date | datetime,
        end_date: date | datetime,
        *,
        gl_account_code: str = "",
        financial_mode: int = FinancialMode.FISCAL,
        data_groups: str = DEFAULT_DATA_GROUPS,
        number_of_records: int = DEFAULT_PAGE_SIZE,
        start_record: int = 0,
        search_values: list[tuple[str, str]] | None = None,
    ) -> list[Transaction]:
        """Return one page of ``GetTransactions`` (one call).

        An empty ``gl_account_code`` asks for every account. ``search_values`` is a
        list of ``(SearchOption, SearchValue)``, for example
        ``[("AmountGreaterThanEqual", "100")]``.
        """

        parameters = dict(
            administrationID=require_text(administration_id, "administration_id"),
            glAccountCode=str(gl_account_code or ""),
            startDate=as_datetime(start_date),
            endDate=as_datetime(end_date),
            financialMode=int(financial_mode),
            dataGroups=data_groups or "",
            numberOfRecords=require_positive(number_of_records, "number_of_records"),
            startRecord=int(start_record),
        )
        if search_values:
            parameters["searchValues"] = {
                "TransactionSearch": [
                    {"SearchOption": option, "SearchValue": str(value)} for option, value in search_values
                ]
            }
        result = self.invoke("GetTransactions", **parameters)
        return [Transaction.from_plain(row) for row in unwrap_rows(result, "Transaction")]

    def iter_transactions(
        self,
        administration_id: str,
        start_date: date | datetime,
        end_date: date | datetime,
        *,
        gl_account_code: str = "",
        financial_mode: int = FinancialMode.FISCAL,
        data_groups: str = DEFAULT_DATA_GROUPS,
        page_size: int = DEFAULT_PAGE_SIZE,
        first_record: int = 0,
        max_pages: int | None = None,
    ) -> Iterator[Transaction]:
        """Yield every transaction in the range, one call per page.

        Stops on an empty page, a short page, a page without new ids, or after
        ``max_pages``. Each id is yielded once.
        """

        return iter_unique_pages(
            lambda start_record: self.transactions(
                administration_id,
                start_date,
                end_date,
                gl_account_code=gl_account_code,
                financial_mode=financial_mode,
                data_groups=data_groups,
                number_of_records=page_size,
                start_record=start_record,
            ),
            first=first_record,
            page_size=page_size,
            next_position=lambda start_record, rows: start_record + len(rows),
            max_pages=max_pages,
        )

    def transaction_details(
        self,
        administration_id: str,
        start_date: date | datetime,
        end_date: date | datetime,
        *,
        gl_account_code: str = "",
        financial_mode: int = FinancialMode.FISCAL,
    ) -> list[TransactionInfo]:
        """Return ``GetTransactionDetails`` for a range (one call, not paged)."""

        result = self.invoke(
            "GetTransactionDetails",
            administrationID=require_text(administration_id, "administration_id"),
            GLAccountCode=str(gl_account_code or ""),
            StartDate=as_datetime(start_date),
            EndDate=as_datetime(end_date),
            financialMode=int(financial_mode),
        )
        return [TransactionInfo.from_plain(row) for row in unwrap_rows(result, "TransactionInfo")]

    def period_date_table(self, administration_id: str, year: int) -> AdministrationPeriod:
        """Return the start of financial year ``year`` (one call per year)."""

        result = self.invoke(
            "GetPeriodDateTable",
            administrationID=require_text(administration_id, "administration_id"),
            yearID=int(year),
        )
        return AdministrationPeriod.from_plain(result)

    def financial_year_modified_date(self, administration_id: str, year: int) -> datetime | None:
        """Return when transactions of financial year ``year`` last changed."""

        result = self.invoke(
            "GetFinancialYearModifiedDate",
            administrationID=require_text(administration_id, "administration_id"),
            yearID=int(year),
        )
        return to_datetime(plain(result))

    def start_balance_by_gl_account(
        self,
        administration_id: str,
        year: int,
        *,
        financial_mode: int = FinancialMode.FISCAL,
    ) -> list[AccountStartBalance]:
        """Return the opening balance per account for financial year ``year``."""

        result = self.invoke(
            "GetStartBalanceByGlAccount",
            administrationID=require_text(administration_id, "administration_id"),
            bookyear=int(year),
            financialMode=int(financial_mode),
        )
        return [AccountStartBalance.from_plain(row) for row in unwrap_rows(result, "AccountStartBalance")]

    def transaction_document(self, administration_id: str, transaction_id: str) -> TransactionDocumentFile:
        """Return the archived file of a transaction (one call per document)."""

        result = self.invoke(
            "GetTransactionDocument",
            administrationID=require_text(administration_id, "administration_id"),
            transactionID=require_text(transaction_id, "transaction_id"),
        )
        return TransactionDocumentFile.from_plain(result)

    def contact_default_values(self, administration_id: str, contact_id: str) -> list[ContactDefaultValues]:
        """Return the booking defaults of a contact, including the payment term (one call per contact)."""

        result = self.invoke(
            "GetContactDefaultValues",
            administrationID=require_text(administration_id, "administration_id"),
            contactID=require_text(contact_id, "contact_id"),
        )
        return [ContactDefaultValues.from_plain(row) for row in unwrap_rows(result, "ContactDefaultValues")]

    def custom_payment_methods(self, administration_id: str) -> list[PaymentMethod]:
        result = self.invoke(
            "GetCustomPaymentMethods",
            administrationID=require_text(administration_id, "administration_id"),
        )
        return [PaymentMethod.from_plain(row) for row in unwrap_rows(result, "PaymentMethod")]

    def projects(
        self,
        administration_id: str,
        *,
        search_option: str = ProjectSearchOption.ALL,
        search_value: str = "",
    ) -> list[Project]:
        """Return the projects of an administration, with their ids (``GetProjectsAndID``)."""

        result = self.invoke(
            "GetProjectsAndID",
            administrationID=require_text(administration_id, "administration_id"),
            searchOption=soap_value(search_option),
            searchValue=search_value or "",
        )
        return [Project.from_plain(row) for row in unwrap_rows(result, "Project")]

    def project_balance(
        self,
        administration_id: str,
        start_date: date | datetime,
        end_date: date | datetime,
        *,
        gl_account_code: str = "",
        project_code: str = "",
    ) -> list[ProjectBalance]:
        """Return the balance per project and account in a range (a check on the analytic split)."""

        result = self.invoke(
            "GetProjectBalance",
            administrationID=require_text(administration_id, "administration_id"),
            GLAccountCode=str(gl_account_code or ""),
            projectCode=str(project_code or ""),
            StartDate=as_datetime(start_date),
            EndDate=as_datetime(end_date),
        )
        return [ProjectBalance.from_plain(row) for row in unwrap_rows(result, "ProjectBalance")]

    def rgs_scheme(self, administration_id: str, *, rgs_version: str = "") -> list[RGSEntry]:
        """Return the accounts with their RGS code. RGS is the Dutch reference scheme."""

        result = self.invoke(
            "GetRGSScheme",
            administrationID=require_text(administration_id, "administration_id"),
            rgsVersion=rgs_version or "",
        )
        return [RGSEntry.from_plain(row) for row in unwrap_rows(result, "RGSEntry")]

class _AccountingInfo:
    @property
    def _service(self) -> AccountingInfoService:
        return AccountingInfoService(self.client_credentials)


class GLAccountSet(_AccountingInfo, YukiRecordSet[GLAccount]):
    """The chart of accounts (``GetGLAccountScheme``, one call)."""

    def get(self) -> None:
        self._fill(self._service.gl_account_scheme(self.administration_id))

    def find(self, code: str) -> GLAccount:
        """The account with ``code`` from the filled set (no call)."""

        for account in self:
            if account.code == str(code):
                return account
        raise YukiError(f"General ledger account {code} is not in the scheme")


class TransactionSet(_AccountingInfo, YukiRecordSet[Transaction]):
    """General ledger lines (``GetTransactions``, one call per page)."""

    def get(
        self,
        start_date: date | datetime,
        end_date: date | datetime,
        *,
        gl_account_code: str = "",
        financial_mode: int = FinancialMode.FISCAL,
        data_groups: str = DEFAULT_DATA_GROUPS,
        page_size: int = 100,
        max_pages: int | None = None,
    ) -> None:
        """Every line of the period (all pages, or ``max_pages``)."""

        self._fill(
            self._service.iter_transactions(
                self.administration_id,
                start_date,
                end_date,
                gl_account_code=gl_account_code,
                financial_mode=financial_mode,
                data_groups=data_groups,
                page_size=page_size,
                max_pages=max_pages,
            )
        )

    def get_page(
        self,
        start_date: date | datetime,
        end_date: date | datetime,
        *,
        start_record: int = 0,
        number_of_records: int = 100,
        gl_account_code: str = "",
        financial_mode: int = FinancialMode.FISCAL,
        data_groups: str = DEFAULT_DATA_GROUPS,
    ) -> None:
        """One page of lines (one call)."""

        self._fill(
            self._service.transactions(
                self.administration_id,
                start_date,
                end_date,
                gl_account_code=gl_account_code,
                financial_mode=financial_mode,
                data_groups=data_groups,
                number_of_records=number_of_records,
                start_record=start_record,
            )
        )


class TransactionDetailSet(_AccountingInfo, YukiRecordSet[TransactionInfo]):
    """Lines with period, company and booking user (``GetTransactionDetails``, one call)."""

    def get(
        self,
        start_date: date | datetime,
        end_date: date | datetime,
        *,
        gl_account_code: str = "",
        financial_mode: int = FinancialMode.FISCAL,
    ) -> None:
        self._fill(
            self._service.transaction_details(
                self.administration_id, start_date, end_date, gl_account_code=gl_account_code, financial_mode=financial_mode
            )
        )


class TransactionDocument(_AccountingInfo, YukiRecord):
    """The file behind one general ledger line (``GetTransactionDocument``, one call)."""

    _value: TransactionDocumentFile | None = None

    file_name: str | None
    data: bytes | None

    def get(self, transaction_id: str) -> None:
        self._set(self._service.transaction_document(self.administration_id, transaction_id))


class Period(_AccountingInfo, YukiRecord):
    """A financial year (``GetPeriodDateTable``, one call per year).

    ``start`` and ``end`` are read from ``whole_period``.
    """

    _value: AdministrationPeriod | None = None
    _year: int | None = None

    name: str | None
    period: date | None
    whole_period: str | None
    iso8601_period: bool | None

    @property
    def year(self) -> int | None:
        return self._year

    def get(self, year: int) -> None:
        self._year = int(year)
        self._set(self._service.period_date_table(self.administration_id, self._year))

    @property
    def start(self) -> date | None:
        return self._bound(0) or self.period

    @property
    def end(self) -> date | None:
        return self._bound(1)

    def modified(self) -> datetime | None:
        """When transactions of this year last changed (``GetFinancialYearModifiedDate``, one call)."""

        if self.year is None:
            raise YukiError("Period is empty: call get(year) first")
        return self._service.financial_year_modified_date(self.administration_id, self.year)

    def _bound(self, index: int) -> date | None:
        from ..parsing import to_date

        parts = str(self.whole_period or "").split()
        return to_date(parts[index]) if len(parts) == 2 else None


class StartBalanceSet(_AccountingInfo, YukiRecordSet[AccountStartBalance]):
    """Opening balance per account (``GetStartBalanceByGlAccount``, one call)."""

    def get(self, year: int, *, financial_mode: int = FinancialMode.FISCAL) -> None:
        self._fill(self._service.start_balance_by_gl_account(self.administration_id, year, financial_mode=financial_mode))


class ContactDefaultValueSet(_AccountingInfo, YukiRecordSet[ContactDefaultValues]):
    """Booking defaults of one contact (``GetContactDefaultValues``, one call)."""

    def get(self, contact_id: str) -> None:
        self._fill(self._service.contact_default_values(self.administration_id, contact_id))


class PaymentMethodSet(_AccountingInfo, YukiRecordSet[PaymentMethod]):
    """Custom payment methods (``GetCustomPaymentMethods``, one call)."""

    def get(self) -> None:
        self._fill(self._service.custom_payment_methods(self.administration_id))


class ProjectSet(_AccountingInfo, YukiRecordSet[Project]):
    """Projects, the analytic dimension (``GetProjectsAndID``, one call)."""

    def get(self, *, search_option: str = ProjectSearchOption.ALL, search_value: str = "") -> None:
        self._fill(self._service.projects(self.administration_id, search_option=search_option, search_value=search_value))


class ProjectBalanceSet(_AccountingInfo, YukiRecordSet[ProjectBalance]):
    """Balance per account and project (``GetProjectBalance``, one call)."""

    def get(self, start_date: date | datetime, end_date: date | datetime, *, gl_account_code: str = "", project_code: str = "") -> None:
        self._fill(
            self._service.project_balance(
                self.administration_id, start_date, end_date, gl_account_code=gl_account_code, project_code=project_code
            )
        )


class RGSEntrySet(_AccountingInfo, YukiRecordSet[RGSEntry]):
    """The account mapping on the reference scheme (``GetRGSScheme``, one call)."""

    def get(self, *, rgs_version: str = "") -> None:
        self._fill(self._service.rgs_scheme(self.administration_id, rgs_version=rgs_version))
