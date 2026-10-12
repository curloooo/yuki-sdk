"""Zeep transport for Yuki session calls.

Public helpers return plain strings and :class:`Domain` values. Zeep clients
stay inside this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
import threading

from zeep import Client, Settings
from zeep.exceptions import Fault, TransportError
from zeep.transports import Transport

from .parsing import get, to_text, unwrap_rows
from .exceptions import (
    YukiAuthError,
    YukiConfigError,
    YukiDomainError,
    YukiError,
    YukiRateLimitError,
    YukiSessionError,
    YukiSoapError,
)

SOAP_NAMESPACE = "http://www.theyukicompany.com/"

# Official docs: a session id is valid for 24 hours, or until the client
# closes the connection. Refresh one hour early so a stored session is not
# reused against the documented expiry. Callers still pass force=True when
# Yuki rejects a session before that.
SESSION_TTL = timedelta(hours=23)
SESSION_REFRESH_SKEW = timedelta(minutes=5)

HOSTS = {
    "nl": "https://api.yukiworks.nl",
    "be": "https://api.yukiworks.be",
}

# Archive.asmx imports the SOAP-encoding schema (for the StringArray of its
# HTTP bindings) without a schemaLocation, so zeep would download it from
# schemas.xmlsoap.org on every new client. That fails behind a restrictive
# proxy, and the SOAP calls never use the type. A minimal local copy is served instead.
SOAP_ENCODING_NAMESPACE = "http://schemas.xmlsoap.org/soap/encoding/"
SOAP_ENCODING_SCHEMA = b"""<?xml version="1.0" encoding="utf-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" targetNamespace="http://schemas.xmlsoap.org/soap/encoding/">
  <xs:attribute name="arrayType" type="xs:string"/>
  <xs:complexType name="Array">
    <xs:sequence>
      <xs:any minOccurs="0" maxOccurs="unbounded" processContents="lax"/>
    </xs:sequence>
    <xs:anyAttribute processContents="lax"/>
  </xs:complexType>
</xs:schema>
"""

_CLIENTS: dict[str, Client] = {}
_CLIENTS_LOCK = threading.Lock()


class YukiTransport(Transport):
    """zeep transport that serves the SOAP-encoding schema locally."""

    def load(self, url):
        if url.split("://", 1)[-1].rstrip("/") == SOAP_ENCODING_NAMESPACE.split("://", 1)[-1].rstrip("/"):
            return SOAP_ENCODING_SCHEMA
        return super().load(url)


@dataclass(frozen=True)
class Domain:
    """A Yuki domain visible to the current access key."""

    id: str
    name: str
    url: str | None = None
    status: str | None = None
    status_id: str | None = None


def normalize_region(region: str) -> str:
    """Return ``nl`` or ``be``.

    Raises:
        YukiConfigError: ``region`` is anything else. The other host is never tried.
    """

    normalized = str(region or "").strip().lower()
    if normalized not in HOSTS:
        raise YukiConfigError("region must be 'nl' or 'be'")
    return normalized


def host_for(region: str) -> str:
    """Return the API host for a region."""

    return HOSTS[normalize_region(region)]


def wsdl_url(host: str, service: str = "Sales") -> str:
    """Return ``{host}/ws/{service}.asmx?WSDL``."""

    service_name = str(service or "").strip()
    if not service_name.isascii() or not service_name.isalnum():
        raise YukiConfigError(
            "service must be an alphanumeric Yuki webservice name, for example 'Sales'"
        )
    return f"{host.rstrip('/')}/ws/{service_name}.asmx?WSDL"


def get_client(wsdl_url_value: str) -> Client:
    """Return a cached zeep client for a WSDL URL."""

    # Yuki publishes http:// addresses in the WSDL. Zeep upgrades them to HTTPS
    # and logs a warning on every client. That upgrade is expected.
    logging.getLogger("zeep.wsdl.bindings.http").setLevel(logging.ERROR)

    with _CLIENTS_LOCK:
        client = _CLIENTS.get(wsdl_url_value)
        if client is None:
            client = Client(
                wsdl_url_value,
                settings=Settings(strict=False, xml_huge_tree=True),
                transport=YukiTransport(timeout=30, operation_timeout=60),
            )
            _CLIENTS[wsdl_url_value] = client
        return client


def clear_client_cache() -> None:
    """Drop cached zeep clients. Intended for tests."""

    with _CLIENTS_LOCK:
        _CLIENTS.clear()


def invoke(
    wsdl_url_value: str,
    operation: str,
    *,
    debug: bool = False,
    **parameters,
):
    """Call one SOAP operation and return the zeep result.

    Parameter values are not logged. Session ids and access keys stay out of debug output.
    """

    _trace(debug, operation, wsdl_url_value)
    try:
        method = getattr(get_client(wsdl_url_value).service, operation)
    except AttributeError as exc:
        raise YukiConfigError(f"Yuki webservice has no operation '{operation}'") from exc
    try:
        return method(**parameters)
    except Fault as exc:
        _raise_for_fault(exc)
    except TransportError as exc:
        raise YukiError(f"Yuki SOAP transport error during {operation}: {exc}") from exc


def authenticate_access_key(
    wsdl_url_value: str,
    api_key: str,
    *,
    region: str | None = None,
    debug: bool = False,
) -> str:
    """Call ``Authenticate(accessKey)`` and return the session id."""

    access_key = str(api_key or "").strip()
    if not access_key:
        raise YukiConfigError("api_key is required")

    _trace(debug, "Authenticate", wsdl_url_value)
    try:
        result = get_client(wsdl_url_value).service.Authenticate(accessKey=access_key)
    except Fault as exc:
        _raise_for_fault(exc, region=region)
    except TransportError as exc:
        raise YukiError(f"Yuki SOAP transport error during Authenticate: {exc}") from exc

    session_id = str(result or "").strip()
    if not session_id:
        raise YukiAuthError("Authenticate returned an empty session id")
    return session_id


def list_domains(
    wsdl_url_value: str,
    session_id: str,
    *,
    debug: bool = False,
) -> list[Domain]:
    """Call ``Domains(sessionID)`` and return the domains for this key."""

    _require_session(session_id)
    _trace(debug, "Domains", wsdl_url_value)
    try:
        result = get_client(wsdl_url_value).service.Domains(sessionID=session_id)
    except Fault as exc:
        _raise_for_fault(exc)
    except TransportError as exc:
        raise YukiError(f"Yuki SOAP transport error during Domains: {exc}") from exc
    return parse_domains(result)


def set_current_domain(
    wsdl_url_value: str,
    session_id: str,
    domain_id: str,
    *,
    debug: bool = False,
) -> None:
    """Call ``SetCurrentDomain(sessionID, domainID)``."""

    _require_session(session_id)
    selected = str(domain_id or "").strip()
    if not selected:
        raise YukiConfigError(
            "domain_id is required. Call discover_domains() and store the chosen domain id."
        )

    _trace(debug, "SetCurrentDomain", wsdl_url_value)
    try:
        get_client(wsdl_url_value).service.SetCurrentDomain(
            sessionID=session_id,
            domainID=selected,
        )
    except Fault as exc:
        _raise_for_fault(exc)
    except TransportError as exc:
        raise YukiError(f"Yuki SOAP transport error during SetCurrentDomain: {exc}") from exc


def get_current_domain(
    wsdl_url_value: str,
    session_id: str,
    *,
    debug: bool = False,
) -> Domain:
    """Call ``GetCurrentDomain(sessionID)`` and return the active domain."""

    _require_session(session_id)
    _trace(debug, "GetCurrentDomain", wsdl_url_value)
    try:
        result = get_client(wsdl_url_value).service.GetCurrentDomain(sessionID=session_id)
    except Fault as exc:
        _raise_for_fault(exc)
    except TransportError as exc:
        raise YukiError(f"Yuki SOAP transport error during GetCurrentDomain: {exc}") from exc

    domains = parse_domains(result)
    if not domains:
        raise YukiSoapError("GetCurrentDomain returned no domain")
    return domains[0]


def discover_domains(
    api_key: str,
    region: str,
    *,
    debug: bool = False,
) -> list[Domain]:
    """Authenticate and return the domains visible to an access key.

    This does not select a domain and does not store the session. Use it while
    setting up credentials, then save the chosen ``domain_id``.
    """

    selected_region = normalize_region(region)
    endpoint = wsdl_url(host_for(selected_region), "Sales")
    session_id = authenticate_access_key(
        endpoint,
        api_key,
        region=selected_region,
        debug=debug,
    )
    return list_domains(endpoint, session_id, debug=debug)


def parse_domains(result) -> list[Domain]:
    """Turn a ``Domains`` or ``GetCurrentDomain`` payload into :class:`Domain` values."""

    domains: list[Domain] = []
    for row in unwrap_rows(result, "Domain"):
        domain_id = to_text(get(row, "ID"))
        if not domain_id:
            continue
        status = get(row, "Status")
        domains.append(
            Domain(
                id=domain_id,
                name=to_text(get(row, "Name")) or "",
                url=to_text(get(row, "URL")),
                status=to_text(status),
                status_id=to_text(get(status, "ID")),
            )
        )
    return domains


def _require_session(session_id: str) -> None:
    if not str(session_id or "").strip():
        raise YukiSessionError("session_id is required. Call authenticate() first.")


def _trace(debug: bool, operation: str, wsdl_url_value: str) -> None:
    if debug:
        print(f"Yuki SOAP: {operation} [{wsdl_url_value}]")


def _raise_for_fault(fault: Fault, *, region: str | None = None) -> None:
    message = str(getattr(fault, "message", None) or fault).strip()
    lowered = message.lower()
    if "invalid access key" in lowered or "no rights" in lowered or "api-key" in lowered:
        region_note = f" (region '{region}')" if region else ""
        raise YukiAuthError(f"{message}{region_note}. The other Yuki region was not tried.")
    if "invalid session" in lowered:
        raise YukiSessionError(message)
    # Checked before the generic "domain" test: a limit message can name the domain.
    if "daily limit" in lowered:
        raise YukiRateLimitError(message)
    if "no active database" in lowered:
        raise YukiDomainError(
            f"{message}. The administration does not exist on this host: check the region "
            "(an administration only exists on the API host of its own region)."
        )
    if "domain" in lowered:
        raise YukiDomainError(message)
    raise YukiSoapError(message)
