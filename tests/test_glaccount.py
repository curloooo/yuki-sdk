from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from lxml import etree
import pytest

from yuki_sdk.exceptions import YukiConfigError, YukiError, YukiSessionError
from yuki_sdk.glaccount import GLAccountScheme, parse_gl_accounts

ADMINISTRATION_ID = "e7c4b218-deba-437d-844d-d022e355d263"
CREDENTIALS_FILE = Path(__file__).resolve().parents[1] / "credentials" / "yuki_api_default.json"

SCHEME_XML = """
<GetGLAccountSchemeResult xmlns="http://www.theyukicompany.com/">
  <GlAccount>
    <code>100000</code>
    <type>2</type>
    <subtype>0</subtype>
    <isEnabled>true</isEnabled>
    <descripton>Geplaatst kapitaal</descripton>
    <isVATApplicable>false</isVATApplicable>
    <deductableVATPercentage>0.00</deductableVATPercentage>
    <professionalPercentage>1.00</professionalPercentage>
  </GlAccount>
  <GlAccount>
    <code>600000</code>
    <type>8</type>
    <subtype>1</subtype>
    <isEnabled>false</isEnabled>
    <descripton>Aankopen</descripton>
    <descriptionNL>Aankopen NL</descriptionNL>
    <descriptionFR>Achats</descriptionFR>
    <descriptionEN>Purchases</descriptionEN>
    <isVATApplicable>true</isVATApplicable>
    <deductableVATPercentage>21.00</deductableVATPercentage>
    <professionalPercentage>0.50</professionalPercentage>
  </GlAccount>
</GetGLAccountSchemeResult>
"""


def test_parse_gl_accounts_reads_yuki_field_names():
    accounts = parse_gl_accounts(etree.fromstring(SCHEME_XML))

    assert [account.code for account in accounts] == ["100000", "600000"]
    capital = accounts[0]
    assert capital.account_type == 2
    assert capital.subtype == 0
    assert capital.is_enabled is True
    assert capital.description == "Geplaatst kapitaal"
    assert capital.description_nl is None
    assert capital.is_vat_applicable is False
    assert capital.deductible_vat_percentage == Decimal("0.00")
    assert capital.professional_percentage == Decimal("1.00")

    purchases = accounts[1]
    assert purchases.is_enabled is False
    assert purchases.description_nl == "Aankopen NL"
    assert purchases.description_fr == "Achats"
    assert purchases.description_en == "Purchases"
    assert purchases.is_vat_applicable is True
    assert purchases.deductible_vat_percentage == Decimal("21.00")
    assert purchases.professional_percentage == Decimal("0.50")


def test_parse_gl_accounts_reads_zeep_objects():
    account = SimpleNamespace(
        code="100000",
        type=2,
        subtype=0,
        isEnabled=True,
        descripton="Geplaatst kapitaal",
        descriptionNL=None,
        descriptionFR=None,
        descriptionEN=None,
        isVATApplicable=False,
        deductableVATPercentage=Decimal("0.00"),
        professionalPercentage=Decimal("1.00"),
    )

    parsed = parse_gl_accounts([account])

    assert parsed[0].description == "Geplaatst kapitaal"
    assert parsed[0].account_type == 2


class _Credentials:
    def __init__(self):
        self.debug = False
        self.calls = []

    def authenticate(self, force=False):
        self.calls.append(("authenticate", force))
        return "session-1"

    def wsdl_url(self, service="Sales"):
        self.calls.append(("wsdl", service))
        return "https://api.yukiworks.be/ws/AccountingInfo.asmx?WSDL"


def test_scheme_requests_the_administration(monkeypatch):
    credentials = _Credentials()
    seen = {}

    def fake_invoke(wsdl_url_value, operation, *, debug=False, **parameters):
        seen["wsdl"] = wsdl_url_value
        seen["operation"] = operation
        seen["parameters"] = parameters
        return [
            SimpleNamespace(
                code="100000",
                type=2,
                subtype=0,
                isEnabled=True,
                descripton="Geplaatst kapitaal",
                descriptionNL=None,
                descriptionFR=None,
                descriptionEN=None,
                isVATApplicable=False,
                deductableVATPercentage=Decimal("0.00"),
                professionalPercentage=Decimal("1.00"),
            )
        ]

    monkeypatch.setattr("yuki_sdk.service.soap_invoke", fake_invoke)
    scheme = GLAccountScheme(credentials, ADMINISTRATION_ID)

    accounts = scheme.get()

    assert accounts[0].code == "100000"
    assert seen["operation"] == "GetGLAccountScheme"
    assert seen["wsdl"] == "https://api.yukiworks.be/ws/AccountingInfo.asmx?WSDL"
    assert seen["parameters"] == {
        "sessionID": "session-1",
        "administrationID": ADMINISTRATION_ID,
    }
    scheme.find("100000")
    assert credentials.calls.count(("authenticate", False)) == 1


def test_scheme_refreshes_a_rejected_session(monkeypatch):
    credentials = _Credentials()
    attempts = {"count": 0}

    def fake_invoke(wsdl_url_value, operation, *, debug=False, **parameters):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise YukiSessionError("Invalid session ID")
        return []

    monkeypatch.setattr("yuki_sdk.service.soap_invoke", fake_invoke)

    assert GLAccountScheme(credentials, ADMINISTRATION_ID).get() == []
    assert [call for call in credentials.calls if call[0] == "authenticate"] == [
        ("authenticate", False),
        ("authenticate", True),
    ]


def test_missing_administration_id_is_rejected():
    with pytest.raises(YukiConfigError, match="administration_id"):
        GLAccountScheme(_Credentials(), "")


def test_unknown_code_raises():
    scheme = GLAccountScheme(_Credentials(), ADMINISTRATION_ID)
    scheme._accounts = []

    with pytest.raises(YukiError, match="100000"):
        scheme.find("100000")


@pytest.mark.skipif(not CREDENTIALS_FILE.is_file(), reason="local Yuki credentials are not present")
def test_live_gl_account_scheme_for_administration():
    from yuki_sdk import ClientCredentialsJsonFile

    credentials = ClientCredentialsJsonFile(str(CREDENTIALS_FILE))
    scheme = GLAccountScheme(credentials, ADMINISTRATION_ID)

    accounts = scheme.get()

    assert accounts
    capital = scheme.find("100000")
    assert capital.description == "Geplaatst kapitaal"
    assert capital.account_type == 2
    assert capital.is_enabled is True
    assert capital.deductible_vat_percentage == Decimal("0.00")
    assert capital.professional_percentage == Decimal("1.00")
