from lxml import etree
import pytest
from zeep.exceptions import Fault

from yuki_sdk.exceptions import YukiAuthError, YukiDomainError, YukiSessionError
from yuki_sdk.soap import (
    authenticate_access_key,
    discover_domains,
    host_for,
    parse_domains,
    wsdl_url,
)

DOMAINS_XML = """
<DomainsResult xmlns="http://www.theyukicompany.com/">
  <Domains xmlns="">
    <Domain ID="7c0445a0-99fe-44ec-8f71-2747747955cd">
      <Name>curlo-test</Name>
      <URL>curlo-test.yukiworks.be</URL>
      <Status ID="0">Active</Status>
    </Domain>
  </Domains>
</DomainsResult>
"""


class _Service:
    def __init__(self, behaviour):
        self.behaviour = behaviour
        self.calls = []

    def Authenticate(self, accessKey):
        self.calls.append(("Authenticate", accessKey))
        if self.behaviour == "bad-key":
            raise Fault("Invalid access key")
        return "session-1"

    def Domains(self, sessionID):
        self.calls.append(("Domains", sessionID))
        if self.behaviour == "bad-session":
            raise Fault("Invalid session ID")
        return etree.fromstring(DOMAINS_XML)

    def SetCurrentDomain(self, sessionID, domainID):
        self.calls.append(("SetCurrentDomain", sessionID, domainID))
        if domainID == "missing":
            raise Fault("Invalid domain ID")
        return None


class _Client:
    def __init__(self, behaviour="ok"):
        self.service = _Service(behaviour)


def test_parse_domains_reads_id_name_url_and_status():
    domains = parse_domains(etree.fromstring(DOMAINS_XML))

    assert len(domains) == 1
    assert domains[0].id == "7c0445a0-99fe-44ec-8f71-2747747955cd"
    assert domains[0].name == "curlo-test"
    assert domains[0].url == "curlo-test.yukiworks.be"
    assert domains[0].status == "Active"
    assert domains[0].status_id == "0"


def test_hosts_follow_the_explicit_region():
    assert host_for("NL") == "https://api.yukiworks.nl"
    assert host_for("be") == "https://api.yukiworks.be"
    assert wsdl_url(host_for("nl"), "Sales") == "https://api.yukiworks.nl/ws/Sales.asmx?WSDL"
    assert wsdl_url(host_for("be"), "Accounting") == "https://api.yukiworks.be/ws/Accounting.asmx?WSDL"


def test_authenticate_access_key_returns_session_id(monkeypatch):
    client = _Client()
    monkeypatch.setattr("yuki_sdk.soap.get_client", lambda wsdl: client)

    session_id = authenticate_access_key(
        "https://api.yukiworks.be/ws/Sales.asmx?WSDL",
        "access-key",
        region="be",
    )

    assert session_id == "session-1"
    assert client.service.calls == [("Authenticate", "access-key")]


def test_invalid_access_key_stays_on_the_requested_region(monkeypatch):
    client = _Client("bad-key")
    requested = []
    monkeypatch.setattr(
        "yuki_sdk.soap.get_client",
        lambda wsdl: requested.append(wsdl) or client,
    )

    with pytest.raises(YukiAuthError, match="region 'be'"):
        authenticate_access_key(
            "https://api.yukiworks.be/ws/Sales.asmx?WSDL",
            "access-key",
            region="be",
        )

    assert requested == ["https://api.yukiworks.be/ws/Sales.asmx?WSDL"]


def test_invalid_session_and_domain_faults_are_typed(monkeypatch):
    monkeypatch.setattr("yuki_sdk.soap.get_client", lambda wsdl: _Client("bad-session"))
    with pytest.raises(YukiSessionError):
        from yuki_sdk.soap import list_domains

        list_domains("https://api.yukiworks.nl/ws/Sales.asmx?WSDL", "session-1")

    monkeypatch.setattr("yuki_sdk.soap.get_client", lambda wsdl: _Client())
    from yuki_sdk.soap import set_current_domain

    with pytest.raises(YukiDomainError):
        set_current_domain(
            "https://api.yukiworks.nl/ws/Sales.asmx?WSDL",
            "session-1",
            "missing",
        )


def test_discover_domains_uses_only_the_requested_host(monkeypatch):
    client = _Client()
    requested = []
    monkeypatch.setattr(
        "yuki_sdk.soap.get_client",
        lambda wsdl: requested.append(wsdl) or client,
    )

    domains = discover_domains("access-key", "be")

    assert [domain.name for domain in domains] == ["curlo-test"]
    assert requested
    assert set(requested) == {"https://api.yukiworks.be/ws/Sales.asmx?WSDL"}
    assert [call[0] for call in client.service.calls] == ["Authenticate", "Domains"]
