from decimal import Decimal

from lxml import etree
import pytest
from zeep import xsd

from yuki_sdk import AccountingInfoService, GLAccountSet
from yuki_sdk.exceptions import YukiConfigError, YukiError, YukiSessionError
from yuki_sdk.webservices.accountinginfo import parse_gl_accounts

ADMINISTRATION_ID = "administration-1"

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

GL_ACCOUNT_TYPE = xsd.ComplexType(
    [
        xsd.Element("code", xsd.String()),
        xsd.Element("type", xsd.Integer()),
        xsd.Element("subtype", xsd.Integer()),
        xsd.Element("isEnabled", xsd.Boolean()),
        xsd.Element("descripton", xsd.String()),
        xsd.Element("descriptionNL", xsd.String()),
        xsd.Element("descriptionFR", xsd.String()),
        xsd.Element("descriptionEN", xsd.String()),
        xsd.Element("isVATApplicable", xsd.Boolean()),
        xsd.Element("deductableVATPercentage", xsd.Decimal()),
        xsd.Element("professionalPercentage", xsd.Decimal()),
    ]
)


def _zeep_account(**values):
    """A GlAccount as zeep builds it from the WSDL type."""

    return GL_ACCOUNT_TYPE(**values)


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
    account = _zeep_account(
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
            _zeep_account(
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
    accounts = AccountingInfoService(credentials).gl_account_scheme(ADMINISTRATION_ID)

    assert accounts[0].code == "100000"
    assert seen["operation"] == "GetGLAccountScheme"
    assert seen["wsdl"] == "https://api.yukiworks.be/ws/AccountingInfo.asmx?WSDL"
    assert seen["parameters"] == {
        "sessionID": "session-1",
        "administrationID": ADMINISTRATION_ID,
    }
    filled = GLAccountSet(credentials, ADMINISTRATION_ID)
    filled._fill(accounts)
    assert filled.find("100000").code == "100000"
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

    assert AccountingInfoService(credentials).gl_account_scheme(ADMINISTRATION_ID) == []
    assert [call for call in credentials.calls if call[0] == "authenticate"] == [
        ("authenticate", False),
        ("authenticate", True),
    ]


def test_missing_administration_id_is_rejected():
    with pytest.raises(YukiConfigError, match="administration_id"):
        AccountingInfoService(_Credentials()).gl_account_scheme("")


def test_unknown_code_raises():
    accounts = GLAccountSet(_Credentials(), ADMINISTRATION_ID)
    accounts._fill([])

    with pytest.raises(YukiError, match="100000"):
        accounts.find("100000")
