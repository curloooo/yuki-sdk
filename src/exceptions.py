"""Errors raised by the Yuki SDK.

These types are the public error surface. Zeep faults are translated before
they leave the SOAP helper.
"""


class YukiError(Exception):
    """Base error for the Yuki SDK."""


class YukiConfigError(YukiError):
    """Local credentials are missing or invalid."""


class YukiAuthError(YukiError):
    """The access key was rejected for the configured region."""


class YukiSessionError(YukiError):
    """The SOAP session is missing or was rejected by Yuki."""


class YukiDomainError(YukiError):
    """Yuki rejected the domain id."""


class YukiRateLimitError(YukiError):
    """The domain has used its daily webservice allowance."""


class YukiSoapError(YukiError):
    """Yuki returned a SOAP fault that is not an auth, session, or domain error."""
