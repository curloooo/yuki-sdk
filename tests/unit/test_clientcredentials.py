from datetime import datetime, timedelta, timezone
import json

import pytest

from yuki_sdk import ClientCredentialsHvac, ClientCredentialsJsonFile
from yuki_sdk.exceptions import YukiAuthError, YukiConfigError
from yuki_sdk.soap import SESSION_TTL


def _write_credentials(path, **overrides):
    payload = {
        "api_key": "access-key",
        "region": "be",
        "domain_id": "domain-1",
        "admin_id": "admin-1",
        "administration_name": "Example B.V.",
        "session_id": "",
        "session_valid_until": "1900-01-01T00:00:00+00:00",
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload), encoding="utf-8")


class _Soap:
    def __init__(self):
        self.calls = []

    def authenticate_access_key(self, wsdl_url_value, api_key, *, region=None, debug=False, on_call=None):
        self.calls.append(("Authenticate", wsdl_url_value, api_key, region))
        if api_key == "bad-key":
            raise YukiAuthError(f"Invalid access key (region '{region}'). The other Yuki region was not tried.")
        return "session-1"

    def set_current_domain(self, wsdl_url_value, session_id, domain_id, *, debug=False, on_call=None):
        self.calls.append(("SetCurrentDomain", wsdl_url_value, session_id, domain_id))

    def list_domains(self, wsdl_url_value, session_id, *, debug=False, on_call=None):
        self.calls.append(("Domains", wsdl_url_value, session_id))
        return []

    def get_current_domain(self, wsdl_url_value, session_id, *, debug=False, on_call=None):
        self.calls.append(("GetCurrentDomain", wsdl_url_value, session_id))
        from yuki_sdk import Domain

        return Domain(id="domain-1", name="Example")


@pytest.fixture
def soap(monkeypatch):
    client = _Soap()
    monkeypatch.setattr("yuki_sdk.clientcredentials.authenticate_access_key", client.authenticate_access_key)
    monkeypatch.setattr("yuki_sdk.clientcredentials.set_current_domain", client.set_current_domain)
    monkeypatch.setattr("yuki_sdk.clientcredentials.list_domains", client.list_domains)
    monkeypatch.setattr("yuki_sdk.clientcredentials.get_current_domain", client.get_current_domain)
    return client


def test_json_authenticate_persists_session_and_binds_domain(tmp_path, soap):
    path = tmp_path / "yuki_api_default.json"
    _write_credentials(path)

    credentials = ClientCredentialsJsonFile(path)
    session_id = credentials.authenticate()

    assert session_id == "session-1"
    assert soap.calls[0][0] == "Authenticate"
    assert soap.calls[0][1] == "https://api.yukiworks.be/ws/Sales.asmx?WSDL"
    assert soap.calls[1] == (
        "SetCurrentDomain",
        "https://api.yukiworks.be/ws/Sales.asmx?WSDL",
        "session-1",
        "domain-1",
    )

    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["session_id"] == "session-1"
    assert stored["administration_name"] == "Example B.V."
    assert stored["admin_id"] == "admin-1"
    valid_until = datetime.fromisoformat(stored["session_valid_until"])
    assert valid_until > datetime.now(timezone.utc) + SESSION_TTL - timedelta(minutes=1)


def test_valid_session_is_reused_without_calling_yuki(tmp_path, soap):
    path = tmp_path / "yuki_api_default.json"
    valid_until = datetime.now(timezone.utc) + timedelta(hours=2)
    _write_credentials(path, session_id="existing-session", session_valid_until=valid_until.isoformat())

    credentials = ClientCredentialsJsonFile(path)
    assert credentials.authenticate() == "existing-session"
    assert soap.calls == []

    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["session_id"] == "existing-session"


def test_force_refreshes_a_live_session(tmp_path, soap):
    path = tmp_path / "yuki_api_default.json"
    valid_until = datetime.now(timezone.utc) + timedelta(hours=2)
    _write_credentials(path, session_id="existing-session", session_valid_until=valid_until.isoformat())

    credentials = ClientCredentialsJsonFile(path)
    assert credentials.authenticate(force=True) == "session-1"
    assert [call[0] for call in soap.calls] == ["Authenticate", "SetCurrentDomain"]


def test_dutch_and_belgian_hosts(tmp_path, soap):
    dutch = tmp_path / "nl.json"
    belgian = tmp_path / "be.json"
    _write_credentials(dutch, region="nl")
    _write_credentials(belgian, region="BE")

    assert ClientCredentialsJsonFile(dutch).wsdl_url() == "https://api.yukiworks.nl/ws/Sales.asmx?WSDL"
    assert ClientCredentialsJsonFile(belgian).wsdl_url("Archive") == "https://api.yukiworks.be/ws/Archive.asmx?WSDL"
    ClientCredentialsJsonFile(dutch).authenticate()
    assert soap.calls[-2][1] == "https://api.yukiworks.nl/ws/Sales.asmx?WSDL"


def test_missing_domain_id_does_not_call_yuki(tmp_path, soap):
    path = tmp_path / "yuki_api_default.json"
    _write_credentials(path, domain_id="")

    with pytest.raises(YukiConfigError, match="set_domain_id"):
        ClientCredentialsJsonFile(path).authenticate()

    assert soap.calls == []


def test_bad_key_is_not_followed_by_the_other_region(tmp_path, soap):
    path = tmp_path / "yuki_api_default.json"
    _write_credentials(path, api_key="bad-key", region="nl")

    with pytest.raises(YukiAuthError, match="region 'nl'"):
        ClientCredentialsJsonFile(path).authenticate()

    assert len(soap.calls) == 1
    assert soap.calls[0][1].startswith("https://api.yukiworks.nl/")


def test_unknown_region_is_rejected(tmp_path):
    path = tmp_path / "yuki_api_default.json"
    _write_credentials(path, region="fr")

    with pytest.raises(YukiConfigError, match="nl"):
        ClientCredentialsJsonFile(path).authenticate()


def test_list_domains_uses_the_stored_session(tmp_path, soap):
    path = tmp_path / "yuki_api_default.json"
    valid_until = datetime.now(timezone.utc) + timedelta(hours=2)
    _write_credentials(path, session_id="existing-session", session_valid_until=valid_until.isoformat())

    ClientCredentialsJsonFile(path).list_domains()

    assert soap.calls == [("Domains", "https://api.yukiworks.be/ws/Sales.asmx?WSDL", "existing-session")]


class _Vault:
    def __init__(self):
        self.secret = {
            "api_key": "access-key",
            "session_id": "",
        }
        self.metadata = {
            "region": "nl",
            "domain_id": "domain-1",
            "admin_id": "admin-9",
            "administration_name": "Vault B.V.",
            "session_valid_until": "1900-01-01T00:00:00+00:00",
        }
        self.secrets = self
        self.kv = self
        self.v2 = self

    def read_secret_version(self, mount_point, path):
        assert mount_point == "secret"
        assert path == "yuki_api"
        return {
            "data": {
                "data": dict(self.secret),
                "metadata": {"custom_metadata": dict(self.metadata)},
            }
        }

    def create_or_update_secret(self, mount_point, path, secret):
        assert mount_point == "secret"
        assert path == "yuki_api"
        self.secret = dict(secret)

    def update_metadata(self, mount_point, path, custom_metadata):
        self.metadata = dict(custom_metadata)


def test_hvac_reads_and_writes_the_same_fields_as_json(monkeypatch, soap):
    vault = _Vault()
    monkeypatch.setattr("yuki_sdk.clientcredentials.hvac.Client", lambda **kwargs: vault)

    credentials = ClientCredentialsHvac(
        url="http://vault.local",
        token="token",
        mount_point="secret",
        path="yuki_api",
    )
    assert credentials.authenticate() == "session-1"

    assert vault.secret == {"api_key": "access-key", "session_id": "session-1"}
    assert vault.metadata["region"] == "nl"
    assert vault.metadata["domain_id"] == "domain-1"
    assert vault.metadata["admin_id"] == "admin-9"
    assert vault.metadata["administration_name"] == "Vault B.V."
    assert vault.metadata["session_valid_until"]

    reloaded = ClientCredentialsHvac(
        url="http://vault.local",
        token="token",
        mount_point="secret",
        path="yuki_api",
    )
    assert reloaded.authenticate() == "session-1"
    assert [call[0] for call in soap.calls] == ["Authenticate", "SetCurrentDomain"]


def test_missing_vault_domain_id_is_a_config_error_and_does_not_write(monkeypatch):
    vault = _Vault()
    vault.metadata = {
        "region": "be",
        "session_valid_until": "1900-01-01T00:00:00+00:00",
    }
    vault.writes = []
    original_secret = vault.create_or_update_secret
    original_metadata = vault.update_metadata

    def record_secret(*args, **kwargs):
        vault.writes.append("secret")
        return original_secret(*args, **kwargs)

    def record_metadata(*args, **kwargs):
        vault.writes.append("metadata")
        return original_metadata(*args, **kwargs)

    vault.create_or_update_secret = record_secret
    vault.update_metadata = record_metadata
    monkeypatch.setattr("yuki_sdk.clientcredentials.hvac.Client", lambda **kwargs: vault)

    credentials = ClientCredentialsHvac(
        url="http://vault.local",
        token="token",
        mount_point="secret",
        path="yuki_api",
    )

    with pytest.raises(YukiConfigError, match="set_domain_id"):
        credentials.authenticate()

    assert vault.writes == []


def test_set_domain_id_stores_metadata_and_drops_the_old_session(monkeypatch):
    vault = _Vault()
    vault.secret["session_id"] = "old-session"
    vault.metadata["session_valid_until"] = "2099-01-01T00:00:00+00:00"
    monkeypatch.setattr("yuki_sdk.clientcredentials.hvac.Client", lambda **kwargs: vault)

    credentials = ClientCredentialsHvac(
        url="http://vault.local",
        token="token",
        mount_point="secret",
        path="yuki_api",
    )
    credentials.set_domain_id("domain-2")

    assert credentials.domain_id == "domain-2"
    assert credentials.session_id == ""
    assert vault.secret["session_id"] == ""
    assert vault.metadata["domain_id"] == "domain-2"
    assert vault.metadata["region"] == "nl"
    assert vault.metadata["administration_name"] == "Vault B.V."


def test_update_metadata_omits_blank_optional_fields(monkeypatch):
    vault = _Vault()
    monkeypatch.setattr("yuki_sdk.clientcredentials.hvac.Client", lambda **kwargs: vault)

    credentials = ClientCredentialsHvac(
        url="http://vault.local",
        token="token",
        mount_point="secret",
        path="yuki_api",
    )
    credentials.update_metadata(admin_id="", administration_name="Renamed B.V.")

    assert credentials.administration_name == "Renamed B.V."
    assert "admin_id" not in vault.metadata
    assert vault.metadata["administration_name"] == "Renamed B.V."
    assert vault.metadata["domain_id"] == "domain-1"


def test_json_set_domain_id_is_written(tmp_path):
    path = tmp_path / "yuki_api_default.json"
    _write_credentials(path, domain_id="", session_id="old-session")

    credentials = ClientCredentialsJsonFile(path)
    credentials.set_domain_id("domain-9")

    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["domain_id"] == "domain-9"
    assert stored["session_id"] == ""


def test_calls_are_counted_per_run_and_printed_in_debug(tmp_path, capsys):
    from yuki_sdk.soap import _trace

    path = tmp_path / "yuki.json"
    _write_credentials(path)
    credentials = ClientCredentialsJsonFile(str(path), debug=True)

    _trace(True, "Authenticate", "https://api.yukiworks.be/ws/Sales.asmx?WSDL", credentials.count_call)
    _trace(True, "GetTransactions", "https://api.yukiworks.be/ws/AccountingInfo.asmx?WSDL", credentials.count_call)

    assert credentials.calls == 2
    printed = capsys.readouterr().out.splitlines()
    assert printed[-1].endswith("(call 2 in this run)") and "GetTransactions" in printed[-1]
    # Nothing is written to the store.
    assert "calls" not in json.loads(path.read_text(encoding="utf-8"))


def test_domain_set_needs_only_key_and_region(tmp_path, monkeypatch):
    from yuki_sdk import DomainSet
    from yuki_sdk.soap import Domain
    import yuki_sdk.webservices.contact as contact

    path = tmp_path / "yuki.json"
    _write_credentials(path, domain_id="")
    credentials = ClientCredentialsJsonFile(str(path))
    seen = []

    def fake_discover(api_key, region, *, debug=False, on_call=None):
        seen.append((api_key, region, on_call))
        return [Domain(id="domain-1", name="Example")]

    monkeypatch.setattr(contact, "discover_domains", fake_discover)

    domains = DomainSet(credentials)
    domains.get()

    assert [(d.id, d.name) for d in domains] == [("domain-1", "Example")]
    assert seen == [("access-key", "be", credentials.count_call)]


def test_domain_set_current_domain(tmp_path, monkeypatch):
    from yuki_sdk import DomainSet
    from yuki_sdk.soap import Domain

    path = tmp_path / "yuki.json"
    _write_credentials(path)
    credentials = ClientCredentialsJsonFile(str(path))
    monkeypatch.setattr(type(credentials), "current_domain", lambda self: Domain(id="domain-1", name="Example"))

    current = DomainSet(credentials)
    current.get_current()

    assert [(d.id, d.name) for d in current] == [("domain-1", "Example")]


def test_found_invoices_keeps_the_raw_result(tmp_path, monkeypatch):
    from yuki_sdk import FoundInvoices, InvoiceMode, UblService

    path = tmp_path / "yuki.json"
    _write_credentials(path)
    credentials = ClientCredentialsJsonFile(str(path))
    calls = []

    def fake_find(service, administration_id, invoice_mode, arg_xml=None):
        calls.append((administration_id, invoice_mode, arg_xml))
        return {"Invoice": [{"ID": "1"}]}

    monkeypatch.setattr(UblService, "find_invoices", fake_find)

    invoices = FoundInvoices(credentials)
    invoices.get(InvoiceMode.SALES_ALL_INVOICES)

    assert invoices.data == {"Invoice": [{"ID": "1"}]}
    assert calls == [("admin-1", InvoiceMode.SALES_ALL_INVOICES, None)]

