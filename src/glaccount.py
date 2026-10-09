"""General ledger accounts from the AccountingInfo webservice.

``GetGLAccountScheme`` returns the chart of accounts for one administration.
Two SOAP element names keep Yuki's spelling: ``descripton`` and
``deductableVATPercentage``. This module exposes them as ``description`` and
``deductible_vat_percentage``.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from lxml import etree

from .clientcredentials import ClientCredentials
from .exceptions import YukiConfigError, YukiError
from .service import YukiService, require_text


@dataclass(frozen=True)
class GLAccount:
    """One account in a Yuki general ledger scheme."""

    code: str
    account_type: int
    subtype: int
    is_enabled: bool
    description: str
    description_nl: str | None = None
    description_fr: str | None = None
    description_en: str | None = None
    is_vat_applicable: bool = False
    deductible_vat_percentage: Decimal = Decimal("0")
    professional_percentage: Decimal = Decimal("0")


class GLAccountScheme:
    """Chart of accounts for one administration.

    The administration id is the Yuki ``administrationID``, not the domain id.
    """

    def __init__(self, client_credentials: ClientCredentials, administration_id: str):
        self.client_credentials = client_credentials
        self.administration_id = str(administration_id or "").strip()
        if not self.administration_id:
            raise YukiConfigError("administration_id is required")
        self._accounts: list[GLAccount] | None = None

    def get(self, *, refresh: bool = False) -> list[GLAccount]:
        """Return the general ledger accounts for this administration."""

        if self._accounts is None or refresh:
            self._accounts = self._load()
        return list(self._accounts)

    def __len__(self) -> int:
        return len(self.get())

    def __iter__(self):
        return iter(self.get())

    def find(self, code: str) -> GLAccount:
        """Return the account with this code."""

        wanted = str(code or "").strip()
        matches = [account for account in self.get() if account.code == wanted]
        if len(matches) != 1:
            raise YukiError(
                f"Found {len(matches)} general ledger accounts with code '{wanted}'"
            )
        return matches[0]

    def _load(self) -> list[GLAccount]:
        return AccountingInfoService(self.client_credentials).gl_account_scheme(self.administration_id)


class AccountingInfoService(YukiService):
    """Read data from ``AccountingInfo.asmx``."""

    service_name = "AccountingInfo"

    def gl_account_scheme(self, administration_id: str) -> list[GLAccount]:
        result = self.invoke(
            "GetGLAccountScheme",
            administrationID=require_text(administration_id, "administration_id"),
        )
        return parse_gl_accounts(result)


def parse_gl_accounts(result) -> list[GLAccount]:
    """Turn a ``GetGLAccountScheme`` payload into :class:`GLAccount` values."""

    accounts: list[GLAccount] = []
    for item in _account_items(result):
        if item is None:
            continue
        code = _text(_read(item, "code"))
        if not code:
            continue
        accounts.append(
            GLAccount(
                code=code,
                account_type=_integer(_read(item, "type")),
                subtype=_integer(_read(item, "subtype")),
                is_enabled=_boolean(_read(item, "isEnabled")),
                description=_text(_read(item, "descripton", "description")),
                description_nl=_optional_text(_read(item, "descriptionNL")),
                description_fr=_optional_text(_read(item, "descriptionFR")),
                description_en=_optional_text(_read(item, "descriptionEN")),
                is_vat_applicable=_boolean(_read(item, "isVATApplicable")),
                deductible_vat_percentage=_decimal(_read(item, "deductableVATPercentage")),
                professional_percentage=_decimal(_read(item, "professionalPercentage")),
            )
        )
    return accounts


def _account_items(result):
    if result is None:
        return []
    if isinstance(result, list):
        return result
    nested = getattr(result, "GlAccount", None)
    if nested is not None:
        return nested if isinstance(nested, list) else [nested]
    if _is_element(result):
        return [element for element in result.iter() if _local_name(element).lower() == "glaccount"]
    return [result]


def _read(item, *names):
    if _is_element(item):
        for child in item:
            if _local_name(child) in names and child.text is not None:
                return child.text
        return None
    for name in names:
        if hasattr(item, name):
            return getattr(item, name)
    return None


def _is_element(item) -> bool:
    return isinstance(item, etree._Element)


def _local_name(element) -> str:
    return etree.QName(element).localname


def _text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _optional_text(value) -> str | None:
    text = _text(value)
    return text or None


def _integer(value) -> int:
    if value is None or value == "":
        return 0
    return int(value)


def _boolean(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1"}


def _decimal(value) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value).strip())
