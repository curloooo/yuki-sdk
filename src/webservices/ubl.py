"""Read methods for the UBL export webservice (``UBL.asmx``).

``GetUBLDocument`` returns the UBL XML of an invoice: due date, payment
reference, lines with VAT category, buyer and seller. The id it expects is not
documented; the transaction's document id is the first candidate.

``FindInvoices`` takes an ``argXML`` search document whose layout Yuki does
not document. The WSDL marks it optional, but Yuki rejects a missing value
(``Value cannot be null for parameter "argXML"``). An omitted document is
therefore sent as an empty element. The method returns the raw result.
"""

from __future__ import annotations

from enum import Enum

from lxml import etree

from ..parsing import plain, to_text
from ..service import YukiService, require_text, soap_value


class InvoiceMode(str, Enum):
    SALES_TO_BE_SEND = "Sales_ToBeSend"
    SALES_UNPAID = "Sales_Unpaid"
    SALES_TO_COLLECT = "Sales_ToCollect"
    SALES_IN_TRANSIT = "Sales_InTransit"
    SALES_ALL_INVOICES = "Sales_AllInvoices"
    SALES_REVERTED = "Sales_Reverted"
    SALES_IN_PROCESS = "Sales_InProcess"
    SALES_COLLECTION_IN_PROCESS = "Sales_CollectionInProcess"
    SALES_COLLECTION_ALL_INVOICES = "Sales_CollectionAllInvoices"
    SALES_COLLECTION_UNPAID = "Sales_CollectionUnpaid"
    SALES_REVENUE_LIST = "Sales_RevenueList"
    SALES_CREDIT_INVOICES = "Sales_CreditInvoices"
    PURCHASE_TO_BE_PAID = "Purchase_ToBePaid"
    PURCHASE_ALL = "Purchase_All"
    PURCHASE_IN_PROCESS = "Purchase_InProcess"
    PURCHASE_IN_TRANSFER = "Purchase_InTransfer"
    PURCHASE_CREDIT_INVOICES = "Purchase_CreditInvoices"


def _arg_xml(document: str | etree._Element | None):
    """Return the zeep value for ``argXML``.

    ``None`` is an empty document: zeep renders a list as the child elements,
    so an empty list is the element ``<argXML/>``.
    """

    if document is None:
        return []
    if isinstance(document, str):
        return etree.fromstring(document)
    return document


class UblService(YukiService):
    """Read data from ``UBL.asmx``."""

    service_name = "UBL"

    def ubl_document(self, administration_id: str, invoice_id: str) -> str | None:
        """Return the UBL XML of one invoice as text (one call per invoice)."""

        result = self.invoke(
            "GetUBLDocument",
            administrationID=require_text(administration_id, "administration_id"),
            invoiceID=require_text(invoice_id, "invoice_id"),
        )
        return to_text(result)

    def find_invoices(self, administration_id: str, invoice_mode: str, arg_xml: str | etree._Element | None = None):
        """Search invoices in a list of the Yuki UI (``invoice_mode``) and return the raw result as plain data.

        ``arg_xml`` is the search document. When it is omitted, an empty
        ``argXML`` element is sent: Yuki faults on a null parameter.
        """

        return plain(
            self.invoke(
                "FindInvoices",
                administrationID=require_text(administration_id, "administration_id"),
                invoiceMode=soap_value(invoice_mode),
                argXML=_arg_xml(arg_xml),
            )
        )
