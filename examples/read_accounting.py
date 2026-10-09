"""Read every Accounting webservice method and print a short summary."""

from datetime import date

from src import AccountingService

from examples.auth.auth import get_cred
from examples.sample_ids import ADMINISTRATION_ID, GL_ACCOUNT_CODE

START = date(date.today().year, 1, 1)
END = date.today()


def _show(label, rows) -> None:
    print(f"{label}: {len(rows)}")
    for row in rows[:3]:
        print(f"  {row}")


def main() -> None:
    service = AccountingService(get_cred())
    _show("GLAccountBalance", service.gl_account_balance(ADMINISTRATION_ID, END))
    _show("GLAccountBalanceFiscal", service.gl_account_balance_fiscal(ADMINISTRATION_ID, END))
    _show("GLAccountBalanceYearEnd", service.gl_account_balance_year_end(ADMINISTRATION_ID, END))
    _show(
        "GLAccountTransactions",
        service.gl_account_transactions(ADMINISTRATION_ID, GL_ACCOUNT_CODE, START, END),
    )
    _show(
        "GLAccountTransactionsAndContact",
        service.gl_account_transactions_and_contact(ADMINISTRATION_ID, GL_ACCOUNT_CODE, START, END),
    )
    _show(
        "GLAccountTransactionsFiscal",
        service.gl_account_transactions_fiscal(ADMINISTRATION_ID, GL_ACCOUNT_CODE, START, END),
    )
    print(f"NetRevenue: {service.net_revenue(ADMINISTRATION_ID, START, END)}")
    print(f"NetRevenueFiscal: {service.net_revenue_fiscal(ADMINISTRATION_ID, START, END)}")
    _show("OutstandingCreditorItems", service.outstanding_creditor_items(ADMINISTRATION_ID))
    _show(
        "OutstandingCreditorItemsByDate",
        service.outstanding_creditor_items_by_date(ADMINISTRATION_ID, START, END),
    )
    _show(
        "OutstandingCreditorItemsByDateOutstanding",
        service.outstanding_creditor_items_by_date_outstanding(ADMINISTRATION_ID, END),
    )
    _show(
        "OutstandingCreditorWithPaymentReference",
        service.outstanding_creditor_with_payment_reference(ADMINISTRATION_ID, START, END),
    )
    _show("OutstandingDebtorItems", service.outstanding_debtor_items(ADMINISTRATION_ID))
    _show(
        "OutstandingDebtorItemsByDate",
        service.outstanding_debtor_items_by_date(ADMINISTRATION_ID, START, END),
    )
    _show(
        "OutstandingDebtorItemsByDateOutstanding",
        service.outstanding_debtor_items_by_date_outstanding(ADMINISTRATION_ID, END),
    )
    _show(
        "OutstandingDebtorItemsWithLanguage",
        service.outstanding_debtor_items_with_language(ADMINISTRATION_ID),
    )
    _show(
        "OutstandingDebtorWithPaymentReference",
        service.outstanding_debtor_with_payment_reference(ADMINISTRATION_ID, START, END),
    )
    _show("CheckOutstandingItem", service.check_outstanding_item("1"))
    _show("CheckOutstandingItemAdmin", service.check_outstanding_item_admin(ADMINISTRATION_ID, "1"))


if __name__ == "__main__":
    main()
