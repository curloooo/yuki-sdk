"""Shared caller for every Yuki webservice.

Subclasses set ``service_name`` and add read methods. ``invoke`` authenticates,
sends ``sessionID``, and retries once when Yuki rejects the session.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from lxml import etree

from .clientcredentials import ClientCredentials
from .exceptions import YukiConfigError, YukiSessionError
from .soap import invoke as soap_invoke


class YukiService:
    """Base client for one ASMX webservice."""

    service_name: str

    def __init__(self, client_credentials: ClientCredentials):
        self.client_credentials = client_credentials

    def invoke(self, operation: str, **parameters):
        """Call ``operation`` on this service with the current session."""

        try:
            return self._invoke(operation, force=False, **parameters)
        except YukiSessionError:
            return self._invoke(operation, force=True, **parameters)

    def read_rows(self, operation: str, row_name: str, parser, **parameters) -> list:
        """Call ``operation`` and parse each ``row_name`` element."""

        result = self.invoke(operation, **parameters)
        return [parser(row) for row in row_elements(result, row_name)]

    def _invoke(self, operation: str, *, force: bool, **parameters):
        session_id = self.client_credentials.authenticate(force=force)
        payload = dict(parameters)
        payload["sessionID"] = session_id
        return soap_invoke(
            self.client_credentials.wsdl_url(self.service_name),
            operation,
            debug=self.client_credentials.debug,
            **payload,
        )


def soap_value(value) -> str:
    """Return the SOAP enum string. ``str(Enum)`` is the member name on Python 3.11+."""

    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def require_text(value: str, name: str) -> str:
    selected = str(value or "").strip()
    if not selected:
        raise YukiConfigError(f"{name} is required")
    return selected


def as_datetime(value: date | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    raise YukiConfigError("expected a date or datetime")


def row_elements(result, row_name: str) -> list:
    if result is None:
        return []
    nodes = result if isinstance(result, list) else [result]
    wanted = row_name.lower()
    rows = []
    for node in nodes:
        if not hasattr(node, "iter"):
            continue
        for element in node.iter():
            if local_name(element).lower() == wanted:
                rows.append(element)
    return rows


def local_name(element) -> str:
    return etree.QName(element).localname


def child(element, name: str):
    wanted = name.lower()
    for item in element:
        if local_name(item).lower() == wanted:
            return item
    return None


def text(element, name: str) -> str | None:
    item = child(element, name)
    if item is None or item.text is None:
        return None
    value = item.text.strip()
    return value or None


def attribute(element, name: str) -> str | None:
    if element is None:
        return None
    wanted = name.lower()
    for key, value in element.attrib.items():
        if etree.QName(key).localname.lower() == wanted and str(value).strip():
            return str(value).strip()
    return None


def decimal_text(element, name: str) -> Decimal | None:
    value = text(element, name)
    if value is None:
        return None
    return Decimal(value)


def bool_text(element, name: str) -> bool | None:
    value = text(element, name)
    if value is None:
        return None
    return value.strip().lower() in {"true", "1"}
