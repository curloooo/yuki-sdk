"""Read methods for the Accounting webservice.

``ProcessJournal`` is a write and is not wrapped. Every read here is untyped
(``<any>``) in the WSDL; the layouts follow Yuki's support articles.
Documentation: https://documenter.getpostman.com/view/12207912/UVCBB51L
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from ..parsing import get, plain, single, to_date, to_decimal, to_text
from ..service import YukiService, as_datetime, require_text, soap_value
from ..exceptions import YukiConfigError
from ..record import YukiRecord, YukiRecordSet


class OutstandingItemsSortOrder(str, Enum):
    CONTACT_ASC = "ContactAsc"
    CONTACT_DESC = "ContactDesc"
    AMOUNT_ASC = "AmountAsc"
    AMOUNT_DESC = "AmountDesc"
    DATE_ASC = "DateAsc"
    DATE_DESC = "DateDesc"


@dataclass(frozen=True)
class GLAccountBalance:
    code: str
    balance_type: str | None
    description: str | None
    amount: Decimal | None

    @classmethod
    def from_plain(cls, data) -> "GLAccountBalance":
        data = plain(data) or {}
        return cls(
            code=to_text(get(data, "Code")) or "",
            balance_type=to_text(get(data, "BalanceType")),
            description=to_text(get(data, "Description")),
            amount=to_decimal(get(data, "Amount")),
        )


@dataclass(frozen=True)
class GLAccountTransaction:
    id: str
    date: date | None = None
    description: str | None = None
    amount: Decimal | None = None
    contact: str | None = None
    contact_id: str | None = None
    project_code: str | None = None
    gl_account_code: str | None = None
    sales_item: str | None = None
    file_name: str | None = None
    transaction_type: str | None = None

    @classmethod
    def from_plain(cls, data) -> "GLAccountTransaction":
        data = plain(data) or {}
        return cls(
            id=to_text(get(data, "ID")) or "",
            date=to_date(get(data, "Date")),
            description=to_text(get(data, "Description")),
            amount=to_decimal(get(data, "Amount")),
            contact=to_text(get(data, "Contact")),
            contact_id=to_text(get(data, "ContactID")),
            project_code=to_text(get(get(data, "Project"), "Code")),
            gl_account_code=to_text(get(data, "GLAccountCode")),
            sales_item=to_text(get(data, "SalesItem")),
            file_name=to_text(get(data, "FileName")),
            transaction_type=to_text(get(data, "TransactionType")),
        )


@dataclass(frozen=True)
class OutstandingItem:
    id: str
    date: date | None = None
    description: str | None = None
    contact: str | None = None
    contact_id: str | None = None
    open_amount: Decimal | None = None
    original_amount: Decimal | None = None
    item_type: str | None = None
    item_type_id: str | None = None
    reference: str | None = None
    due_date: date | None = None
    document_id: str | None = None
    payment_method: str | None = None
    payment_reference: str | None = None
    language: str | None = None
    contact_code: str | None = None
    coc_number: str | None = None
    vat_number: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    postcode: str | None = None
    city: str | None = None
    mail_address_line_1: str | None = None
    mail_address_line_2: str | None = None
    mail_postcode: str | None = None
    mail_city: str | None = None
    country: str | None = None

    @classmethod
    def from_plain(cls, data) -> "OutstandingItem":
        data = plain(data) or {}
        item_type = get(data, "Type")
        return cls(
            id=to_text(get(data, "ID")) or "",
            date=to_date(get(data, "Date")),
            description=to_text(get(data, "Description")),
            contact=to_text(get(data, "Contact")),
            contact_id=to_text(single(get(data, "ContactID"))),
            open_amount=to_decimal(get(data, "OpenAmount")),
            original_amount=to_decimal(get(data, "OriginalAmount")),
            item_type=to_text(item_type),
            item_type_id=to_text(get(item_type, "ID")),
            reference=to_text(get(data, "Reference")),
            due_date=to_date(get(data, "DueDate")),
            document_id=to_text(get(data, "DocumentID")),
            payment_method=to_text(get(data, "PaymentMethod")),
            payment_reference=to_text(get(data, "PaymentReference")),
            language=to_text(get(data, "Language", "LayoutLanguage")),
            contact_code=to_text(get(data, "ContactCode")),
            coc_number=to_text(get(data, "CoCNumber")),
            vat_number=to_text(get(data, "VATNumber")),
            address_line_1=to_text(get(data, "AddressLine_1")),
            address_line_2=to_text(get(data, "AddressLine_2")),
            postcode=to_text(get(data, "Postcode")),
            city=to_text(get(data, "City")),
            mail_address_line_1=to_text(get(data, "MailAddressLine_1")),
            mail_address_line_2=to_text(get(data, "MailAddressLine_2")),
            mail_postcode=to_text(get(data, "MailPostcode")),
            mail_city=to_text(get(data, "MailCity")),
            country=to_text(get(data, "Country")),
        )


class AccountingService(YukiService):
    """Read data from ``Accounting.asmx``."""

    service_name = "Accounting"

    def gl_account_balance(self, administration_id: str, transaction_date: date | datetime) -> list[GLAccountBalance]:
        return self._balances("GLAccountBalance", administration_id, transaction_date)

    def gl_account_balance_fiscal(self, administration_id: str, transaction_date: date | datetime) -> list[GLAccountBalance]:
        return self._balances("GLAccountBalanceFiscal", administration_id, transaction_date)

    def gl_account_balance_year_end(self, administration_id: str, transaction_date: date | datetime) -> list[GLAccountBalance]:
        return self._balances("GLAccountBalanceYearEnd", administration_id, transaction_date)

    def gl_account_transactions(
        self,
        administration_id: str,
        gl_account_code: str,
        start_date: date | datetime,
        end_date: date | datetime,
    ) -> list[GLAccountTransaction]:
        return self._transactions("GLAccountTransactions", administration_id, gl_account_code, start_date, end_date)

    def gl_account_transactions_and_contact(
        self,
        administration_id: str,
        gl_account_code: str,
        start_date: date | datetime,
        end_date: date | datetime,
    ) -> list[GLAccountTransaction]:
        return self._transactions(
            "GLAccountTransactionsAndContact",
            administration_id,
            gl_account_code,
            start_date,
            end_date,
        )

    def gl_account_transactions_fiscal(
        self,
        administration_id: str,
        gl_account_code: str,
        start_date: date | datetime,
        end_date: date | datetime,
    ) -> list[GLAccountTransaction]:
        return self._transactions(
            "GLAccountTransactionsFiscal",
            administration_id,
            gl_account_code,
            start_date,
            end_date,
        )

    def net_revenue(
        self,
        administration_id: str,
        start_date: date | datetime,
        end_date: date | datetime,
    ) -> Decimal:
        return self._revenue("NetRevenue", administration_id, start_date, end_date)

    def net_revenue_fiscal(
        self,
        administration_id: str,
        start_date: date | datetime,
        end_date: date | datetime,
    ) -> Decimal:
        return self._revenue("NetRevenueFiscal", administration_id, start_date, end_date)

    def outstanding_creditor_items(
        self,
        administration_id: str,
        *,
        include_bank_transactions: bool = False,
        sort_order: str = OutstandingItemsSortOrder.DATE_DESC,
    ) -> list[OutstandingItem]:
        return self._outstanding(
            "OutstandingCreditorItems",
            administration_id,
            include_bank_transactions=include_bank_transactions,
            sort_order=sort_order,
        )

    def outstanding_creditor_items_by_date(
        self,
        administration_id: str,
        start_date: date | datetime,
        end_date: date | datetime,
        *,
        include_bank_transactions: bool = False,
        sort_order: str = OutstandingItemsSortOrder.DATE_DESC,
    ) -> list[OutstandingItem]:
        return self._outstanding(
            "OutstandingCreditorItemsByDate",
            administration_id,
            include_bank_transactions=include_bank_transactions,
            sort_order=sort_order,
            startDate=as_datetime(start_date),
            endDate=as_datetime(end_date),
        )

    def outstanding_creditor_items_by_date_outstanding(
        self,
        administration_id: str,
        date_outstanding: date | datetime,
        *,
        include_bank_transactions: bool = False,
        sort_order: str = OutstandingItemsSortOrder.DATE_DESC,
    ) -> list[OutstandingItem]:
        return self._outstanding(
            "OutstandingCreditorItemsByDateOutstanding",
            administration_id,
            include_bank_transactions=include_bank_transactions,
            sort_order=sort_order,
            dateOutstanding=as_datetime(date_outstanding),
        )

    def outstanding_creditor_with_payment_reference(
        self,
        administration_id: str,
        start_date: date | datetime,
        end_date: date | datetime,
        *,
        include_bank_transactions: bool = False,
        sort_order: str = OutstandingItemsSortOrder.DATE_DESC,
    ) -> list[OutstandingItem]:
        return self._outstanding(
            "OutstandingCreditorWithPaymentReference",
            administration_id,
            include_bank_transactions=include_bank_transactions,
            sort_order=sort_order,
            startDate=as_datetime(start_date),
            endDate=as_datetime(end_date),
        )

    def outstanding_debtor_items(
        self,
        administration_id: str,
        *,
        include_bank_transactions: bool = False,
        sort_order: str = OutstandingItemsSortOrder.DATE_DESC,
    ) -> list[OutstandingItem]:
        return self._outstanding(
            "OutstandingDebtorItems",
            administration_id,
            include_bank_transactions=include_bank_transactions,
            sort_order=sort_order,
        )

    def outstanding_debtor_items_by_date(
        self,
        administration_id: str,
        start_date: date | datetime,
        end_date: date | datetime,
        *,
        include_bank_transactions: bool = False,
        sort_order: str = OutstandingItemsSortOrder.DATE_DESC,
    ) -> list[OutstandingItem]:
        return self._outstanding(
            "OutstandingDebtorItemsByDate",
            administration_id,
            include_bank_transactions=include_bank_transactions,
            sort_order=sort_order,
            startDate=as_datetime(start_date),
            endDate=as_datetime(end_date),
        )

    def outstanding_debtor_items_by_date_outstanding(
        self,
        administration_id: str,
        date_outstanding: date | datetime,
        *,
        include_bank_transactions: bool = False,
        sort_order: str = OutstandingItemsSortOrder.DATE_DESC,
    ) -> list[OutstandingItem]:
        return self._outstanding(
            "OutstandingDebtorItemsByDateOutstanding",
            administration_id,
            include_bank_transactions=include_bank_transactions,
            sort_order=sort_order,
            dateOutstanding=as_datetime(date_outstanding),
        )

    def outstanding_debtor_items_with_language(
        self,
        administration_id: str,
        *,
        include_bank_transactions: bool = False,
        sort_order: str = OutstandingItemsSortOrder.DATE_DESC,
    ) -> list[OutstandingItem]:
        return self._outstanding(
            "OutstandingDebtorItemsWithLanguage",
            administration_id,
            include_bank_transactions=include_bank_transactions,
            sort_order=sort_order,
        )

    def outstanding_debtor_with_payment_reference(
        self,
        administration_id: str,
        start_date: date | datetime,
        end_date: date | datetime,
        *,
        include_bank_transactions: bool = False,
        sort_order: str = OutstandingItemsSortOrder.DATE_DESC,
    ) -> list[OutstandingItem]:
        return self._outstanding(
            "OutstandingDebtorWithPaymentReference",
            administration_id,
            include_bank_transactions=include_bank_transactions,
            sort_order=sort_order,
            startDate=as_datetime(start_date),
            endDate=as_datetime(end_date),
        )

    def check_outstanding_item(self, reference: str) -> list[OutstandingItem]:
        return self.read_rows(
            "CheckOutstandingItem",
            "Item",
            OutstandingItem.from_plain,
            Reference=require_text(reference, "reference"),
        )

    def check_outstanding_item_admin(self, administration_id: str, reference: str) -> list[OutstandingItem]:
        return self.read_rows(
            "CheckOutstandingItemAdmin",
            "Item",
            OutstandingItem.from_plain,
            administrationID=require_text(administration_id, "administration_id"),
            Reference=require_text(reference, "reference"),
        )

    def _balances(self, operation: str, administration_id: str, transaction_date: date | datetime) -> list[GLAccountBalance]:
        return self.read_rows(
            operation,
            "GLAccount",
            GLAccountBalance.from_plain,
            administrationID=require_text(administration_id, "administration_id"),
            transactionDate=as_datetime(transaction_date),
        )

    def _transactions(
        self,
        operation: str,
        administration_id: str,
        gl_account_code: str,
        start_date: date | datetime,
        end_date: date | datetime,
    ) -> list[GLAccountTransaction]:
        return self.read_rows(
            operation,
            "GLAccountTransaction",
            GLAccountTransaction.from_plain,
            administrationID=require_text(administration_id, "administration_id"),
            GLAccountCode=require_text(gl_account_code, "gl_account_code"),
            StartDate=as_datetime(start_date),
            EndDate=as_datetime(end_date),
        )

    def _revenue(self, operation: str, administration_id: str, start_date: date | datetime, end_date: date | datetime) -> Decimal:
        result = self.invoke(
            operation,
            administrationID=require_text(administration_id, "administration_id"),
            StartDate=as_datetime(start_date),
            EndDate=as_datetime(end_date),
        )
        if result is None or result == "":
            return Decimal("0")
        return Decimal(str(result))

    def _outstanding(
        self,
        operation: str,
        administration_id: str,
        *,
        include_bank_transactions: bool,
        sort_order: str,
        **extra,
    ) -> list[OutstandingItem]:
        return self.read_rows(
            operation,
            "Item",
            OutstandingItem.from_plain,
            administrationID=require_text(administration_id, "administration_id"),
            includeBankTransactions=include_bank_transactions,
            sortOrder=soap_value(sort_order),
            **extra,
        )

class _Accounting:
    @property
    def _service(self) -> AccountingService:
        return AccountingService(self.client_credentials)


class GLAccountBalanceSet(_Accounting, YukiRecordSet[GLAccountBalance]):
    """Balance per account on a date (one call)."""

    def get(self, transaction_date: date | datetime, *, fiscal: bool = False) -> None:
        """``GLAccountBalance``, or ``GLAccountBalanceFiscal`` with ``fiscal=True``."""

        read = self._service.gl_account_balance_fiscal if fiscal else self._service.gl_account_balance
        self._fill(read(self.administration_id, transaction_date))

    def get_year_end(self, transaction_date: date | datetime) -> None:
        """``GLAccountBalanceYearEnd``."""

        self._fill(self._service.gl_account_balance_year_end(self.administration_id, transaction_date))


class GLAccountTransactionSet(_Accounting, YukiRecordSet[GLAccountTransaction]):
    """Lines of one account (one call)."""

    def get(
        self,
        gl_account_code: str,
        start_date: date | datetime,
        end_date: date | datetime,
        *,
        fiscal: bool = False,
        with_contact: bool = False,
    ) -> None:
        """``GLAccountTransactions``; ``fiscal=True`` for the fiscal variant, ``with_contact=True`` for the one with contact."""

        if fiscal and with_contact:
            raise YukiConfigError("Yuki has no fiscal variant with contact")
        if fiscal:
            read = self._service.gl_account_transactions_fiscal
        elif with_contact:
            read = self._service.gl_account_transactions_and_contact
        else:
            read = self._service.gl_account_transactions
        self._fill(read(self.administration_id, gl_account_code, start_date, end_date))


class NetRevenue(_Accounting, YukiRecord):
    """Net revenue of a period (``NetRevenue`` or ``NetRevenueFiscal``, one call). Field: ``amount``."""

    def get(self, start_date: date | datetime, end_date: date | datetime, *, fiscal: bool = False) -> None:
        read = self._service.net_revenue_fiscal if fiscal else self._service.net_revenue
        self._set(read(self.administration_id, start_date, end_date))

    @property
    def amount(self) -> Decimal | None:
        return self._value


class OutstandingItemSet(_Accounting, YukiRecordSet[OutstandingItem]):
    """Open items of customers or suppliers (one call per ``get``).

    ``get_debtors`` / ``get_creditors`` choose the operation from the arguments:
    nothing → open now; ``start_date`` + ``end_date`` → by date;
    ``outstanding_on`` → open on that date.
    """

    def get_debtors(
        self,
        *,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        outstanding_on: date | datetime | None = None,
        include_bank_transactions: bool = False,
        sort_order: str = OutstandingItemsSortOrder.DATE_DESC,
    ) -> None:
        service = self._service
        self._fill(
            self._read(
                service.outstanding_debtor_items,
                service.outstanding_debtor_items_by_date,
                service.outstanding_debtor_items_by_date_outstanding,
                start_date,
                end_date,
                outstanding_on,
                include_bank_transactions=include_bank_transactions,
                sort_order=sort_order,
            )
        )

    def get_creditors(
        self,
        *,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        outstanding_on: date | datetime | None = None,
        include_bank_transactions: bool = False,
        sort_order: str = OutstandingItemsSortOrder.DATE_DESC,
    ) -> None:
        service = self._service
        self._fill(
            self._read(
                service.outstanding_creditor_items,
                service.outstanding_creditor_items_by_date,
                service.outstanding_creditor_items_by_date_outstanding,
                start_date,
                end_date,
                outstanding_on,
                include_bank_transactions=include_bank_transactions,
                sort_order=sort_order,
            )
        )

    def get_debtors_with_language(self, *, include_bank_transactions: bool = False, sort_order: str = OutstandingItemsSortOrder.DATE_DESC) -> None:
        """``OutstandingDebtorItemsWithLanguage``: open customer items with the customer's language and address."""

        self._fill(
            self._service.outstanding_debtor_items_with_language(
                self.administration_id, include_bank_transactions=include_bank_transactions, sort_order=sort_order
            )
        )

    def get_debtors_with_payment_reference(self, start_date: date | datetime, end_date: date | datetime, **options) -> None:
        """``OutstandingDebtorWithPaymentReference``."""

        self._fill(self._service.outstanding_debtor_with_payment_reference(self.administration_id, start_date, end_date, **options))

    def get_creditors_with_payment_reference(self, start_date: date | datetime, end_date: date | datetime, **options) -> None:
        """``OutstandingCreditorWithPaymentReference``."""

        self._fill(self._service.outstanding_creditor_with_payment_reference(self.administration_id, start_date, end_date, **options))

    def check(self, reference: str) -> None:
        """``CheckOutstandingItemAdmin``: the open items with this reference."""

        self._fill(self._service.check_outstanding_item_admin(self.administration_id, reference))

    def _read(self, now, by_date, by_date_outstanding, start_date, end_date, outstanding_on, **options):
        if outstanding_on is not None:
            if start_date is not None or end_date is not None:
                raise YukiConfigError("Pass outstanding_on, or start_date and end_date, not both")
            return by_date_outstanding(self.administration_id, outstanding_on, **options)
        if start_date is not None or end_date is not None:
            if start_date is None or end_date is None:
                raise YukiConfigError("Pass both start_date and end_date")
            return by_date(self.administration_id, start_date, end_date, **options)
        return now(self.administration_id, **options)
