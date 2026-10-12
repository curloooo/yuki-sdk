from datetime import date, datetime
from decimal import Decimal
import json

from lxml import etree
import pytest
from zeep.exceptions import Fault

from yuki_sdk import AccountingInfoService, to_jsonable
from yuki_sdk.exceptions import YukiDomainError, YukiRateLimitError
from yuki_sdk.soap import _raise_for_fault


def test_fault_mapping_region_and_limit():
    with pytest.raises(YukiDomainError, match="region"):
        _raise_for_fault(Fault("Domain has no active database"))
    # A limit message that names the domain is still a rate limit.
    with pytest.raises(YukiRateLimitError):
        _raise_for_fault(Fault("The daily limit of webservice calls for this domain has been reached"))
    with pytest.raises(YukiDomainError):
        _raise_for_fault(Fault("Invalid domain ID"))


class _Credentials:
    debug = False
    domain_id = "domain-1"

    def __init__(self):
        self.hooked = []
        self.response_hook = lambda *args: self.hooked.append(args)

    def authenticate(self, force=False):
        return "session-1"

    def wsdl_url(self, service="Sales"):
        return f"https://api.yukiworks.be/ws/{service}.asmx?WSDL"


def test_response_hook_receives_the_raw_result_without_session(monkeypatch):
    def fake_invoke(wsdl_url_value, operation, *, debug=False, **parameters):
        return [{"id": "tx-1", "amount": Decimal("1")}]

    monkeypatch.setattr("yuki_sdk.service.soap_invoke", fake_invoke)
    credentials = _Credentials()

    AccountingInfoService(credentials).transactions("admin-1", date(2026, 1, 1), date(2026, 1, 31))

    service_name, operation, parameters, result = credentials.hooked[0]
    assert (service_name, operation) == ("AccountingInfo", "GetTransactions")
    assert "sessionID" not in parameters
    assert parameters["administrationID"] == "admin-1"
    assert result == [{"id": "tx-1", "amount": Decimal("1")}]


def test_to_jsonable_handles_every_shape():
    value = {
        "amount": Decimal("1.50"),
        "date": datetime(2026, 10, 12, 8, 0),
        "file": b"abc",
        "rows": [etree.fromstring("<Row ID='1'/>")],
    }

    result = json.loads(json.dumps(to_jsonable(value)))

    assert result["amount"] == "1.50"
    assert result["date"] == "2026-10-12T08:00:00"
    assert result["file"] == {"_base64": "YWJj"}
    assert result["rows"][0]["_xml"] == '<Row ID="1"/>'


def test_transport_serves_the_soap_encoding_schema_locally():
    from yuki_sdk.soap import SOAP_ENCODING_SCHEMA, YukiTransport

    transport = YukiTransport()

    assert transport.load("http://schemas.xmlsoap.org/soap/encoding/") == SOAP_ENCODING_SCHEMA
    assert transport.load("https://schemas.xmlsoap.org/soap/encoding") == SOAP_ENCODING_SCHEMA
