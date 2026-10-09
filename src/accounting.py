"""Read methods for the Accounting webservice.

``ProcessJournal`` is a write and is not wrapped.
Documentation: https://documenter.getpostman.com/view/12207912/UVCBB51L
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from .service import (
    YukiService,
    as_datetime,
    attribute,
    child,
    decimal_text,
    require_text,
    soap_value,
    text,
)


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
    def from_element(cls, element) -> "GLAccountBalance":
        return cls(
            code=attribute(element, "Code") or "",
            balance_type=attribute(element, "BalanceType"),
            description=text(element, "Description"),
            amount=decimal_text(element, "Amount"),
        )


@dataclass(frozen=True)
class GLAccountTransaction:
    id: str
    date: str | None = None
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
    def from_element(cls, element) -> "GLAccountTransaction":
        project = child(element, "Project")
        return cls(
            id=attribute(element, "ID") or "",
            date=text(element, "Date"),
            description=text(element, "Description"),
            amount=decimal_text(element, "Amount"),
            contact=text(element, "Contact"),
            contact_id=text(element, "ContactID"),
            project_code=attribute(project, "Code"),
            gl_account_code=text(element, "GLAccountCode"),
            sales_item=text(element, "SalesItem"),
            file_name=text(element, "FileName"),
            transaction_type=text(element, "TransactionType"),
        )


@dataclass(frozen=True)
class OutstandingItem:
    id: str
    date: str | None = None
    description: str | None = None
    contact: str | None = None
    contact_id: str | None = None
    open_amount: Decimal | None = None
    original_amount: Decimal | None = None
    item_type: str | None = None
    item_type_id: str | None = None
    reference: str | None = None
    due_date: str | None = None
    document_id: str | None = None
    payment_method: str | None = None
    contact_code: str | None = None
    coc_number: str | None = None
    vat_number: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    postcode: str | None = None
    city: str | None = None
    country: str | None = None

    @classmethod
    def from_element(cls, element) -> "OutstandingItem":
        type_element = child(element, "Type")
        return cls(
            id=attribute(element, "ID") or "",
            date=text(element, "Date"),
            description=text(element, "Description"),
            contact=text(element, "Contact"),
            contact_id=text(element, "ContactID"),
            open_amount=decimal_text(element, "OpenAmount"),
            original_amount=decimal_text(element, "OriginalAmount"),
            item_type=text(element, "Type"),
            item_type_id=attribute(type_element, "ID"),
            reference=text(element, "Reference"),
            due_date=text(element, "DueDate"),
            document_id=text(element, "DocumentID"),
            payment_method=text(element, "PaymentMethod"),
            contact_code=text(element, "ContactCode"),
            coc_number=text(element, "CoCNumber"),
            vat_number=text(element, "VATNumber"),
            address_line_1=text(element, "AddressLine_1"),
            address_line_2=text(element, "AddressLine_2"),
            postcode=text(element, "Postcode"),
            city=text(element, "City"),
            country=text(element, "Country"),
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
            OutstandingItem.from_element,
            Reference=require_text(reference, "reference"),
        )

    def check_outstanding_item_admin(self, administration_id: str, reference: str) -> list[OutstandingItem]:
        return self.read_rows(
            "CheckOutstandingItemAdmin",
            "Item",
            OutstandingItem.from_element,
            administrationID=require_text(administration_id, "administration_id"),
            Reference=require_text(reference, "reference"),
        )

    def _balances(self, operation: str, administration_id: str, transaction_date: date | datetime) -> list[GLAccountBalance]:
        return self.read_rows(
            operation,
            "GLAccount",
            GLAccountBalance.from_element,
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
            GLAccountTransaction.from_element,
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
            OutstandingItem.from_element,
            administrationID=require_text(administration_id, "administration_id"),
            includeBankTransactions=include_bank_transactions,
            sortOrder=soap_value(sort_order),
            **extra,
        )
