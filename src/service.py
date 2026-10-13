"""Shared caller for every Yuki webservice.

Subclasses set ``service_name`` and add read methods. ``invoke`` authenticates,
sends ``sessionID``, and retries once when Yuki rejects the session. Response parsing lives in
:mod:`yuki_sdk.parsing`.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Callable

from .clientcredentials import ClientCredentials
from .exceptions import YukiConfigError, YukiSessionError
from .parsing import unwrap_rows
from .soap import invoke as soap_invoke


class YukiService:
    """Base client for one ASMX webservice."""

    service_name: str
    # Most webservices name the session parameter ``sessionID``; a few use ``sessionId``.
    session_parameter: str = "sessionID"

    def __init__(self, client_credentials: ClientCredentials):
        self.client_credentials = client_credentials

    def invoke(self, operation: str, **parameters):
        """Call ``operation`` on this service with the current session.

        After a successful call the credentials' ``response_hook`` (if set) receives
        ``(service_name, operation, parameters, result)``. ``parameters`` never holds
        the session id.
        """

        try:
            result = self._invoke(operation, force=False, **parameters)
        except YukiSessionError:
            result = self._invoke(operation, force=True, **parameters)
        hook = getattr(self.client_credentials, "response_hook", None)
        if hook is not None:
            hook(self.service_name, operation, dict(parameters), result)
        return result

    def read_rows(self, operation: str, row_name: str, parser: Callable, **parameters) -> list:
        """Call ``operation`` and parse each ``row_name`` row with ``parser``."""

        result = self.invoke(operation, **parameters)
        return [parser(row) for row in unwrap_rows(result, row_name)]

    def _invoke(self, operation: str, *, force: bool, **parameters):
        session_id = self.client_credentials.authenticate(force=force)
        payload = dict(parameters)
        payload[self.session_parameter] = session_id
        return soap_invoke(
            self.client_credentials.wsdl_url(self.service_name),
            operation,
            debug=self.client_credentials.debug,
            on_call=getattr(self.client_credentials, "count_call", None),
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


def require_positive(value: int, name: str) -> int:
    number = int(value)
    if number <= 0:
        raise YukiConfigError(f"{name} must be positive")
    return number
