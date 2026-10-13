"""Credential stores for a Yuki SOAP session.

Mirrors the Admin Consult pattern: an abstract credential object reads and
writes tokens in an external store, and ``authenticate()`` refreshes the
session when it is missing or expired.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import json
import os
import tempfile
import threading

import hvac

from .exceptions import YukiConfigError, YukiError
from .soap import (
    SESSION_REFRESH_SKEW,
    SESSION_TTL,
    Domain,
    authenticate_access_key,
    get_current_domain,
    host_for,
    list_domains,
    normalize_region,
    set_current_domain,
    wsdl_url,
)

_EXPIRED = datetime(1900, 1, 1, tzinfo=timezone.utc)


class ClientCredentials(ABC):
    """API key, region, selected domain, and the current SOAP session.

    ``session_id`` is safe to reuse until ``session_valid_until``. Yuki documents
    a session as valid for 24 hours. This client stores it for 23 hours and
    refreshes earlier than that. Pass ``force=True`` when a later call reports
    that Yuki has already ended the session.

    ``calls`` counts the SOAP calls made with this object (in memory, this run only).
    With ``debug`` every call is printed with its number.
    """

    def __init__(self, *, debug: bool = False):
        self.debug = debug
        # Optional callable(service, operation, parameters, result), called after every
        # successful read. Use it to keep the raw response next to the parsed values.
        self.response_hook = None
        self._auth_in_process = False
        self._refresh_lock = threading.Lock()
        self._count_lock = threading.Lock()
        self.calls = 0

        self._api_key = ""
        self._region = ""
        self._domain_id = ""
        self._admin_id = ""
        self._administration_name = ""
        self._session_id = ""
        self._session_valid_until = _EXPIRED

    @property
    def api_key(self) -> str:
        return self._api_key

    @property
    def region(self) -> str:
        return self._region

    @property
    def domain_id(self) -> str:
        return self._domain_id

    @property
    def admin_id(self) -> str:
        return self._admin_id

    @property
    def administration_name(self) -> str:
        return self._administration_name

    @property
    def session_id(self) -> str:
        return self._session_id

    @session_id.setter
    def session_id(self, value: str):
        self._session_id = str(value or "").strip()

    @property
    def session_valid_until(self) -> datetime:
        return self._session_valid_until

    @session_valid_until.setter
    def session_valid_until(self, value):
        self._session_valid_until = _parse_datetime(value)

    def count_call(self, operation: str) -> int:
        """Count one SOAP call made with these credentials and return its number."""

        with self._count_lock:
            self.calls += 1
            return self.calls

    @property
    def host(self) -> str:
        if not self._region:
            raise YukiConfigError("region is required")
        return host_for(self._region)

    def wsdl_url(self, service: str = "Sales") -> str:
        """Return the WSDL URL for a Yuki webservice on this credential's host."""

        return wsdl_url(self.host, service)

    def set_domain_id(self, domain_id: str) -> None:
        """Store the Yuki domain id.

        A session bound to another domain is cleared. The next ``authenticate()``
        opens a new session and calls ``SetCurrentDomain``.
        """

        self.update_metadata(domain_id=domain_id)

    def update_metadata(
        self,
        *,
        region: str | None = None,
        domain_id: str | None = None,
        admin_id: str | None = None,
        administration_name: str | None = None,
    ) -> None:
        """Update region, domain, or administration metadata and write it back.

        Pass only the fields that should change. ``domain_id`` and ``region``
        cannot be blank. Blank ``admin_id`` or ``administration_name`` clears
        that field. Changing region or domain id drops the stored session.
        """

        self._read_tokens()
        invalidate_session = False
        if region is not None:
            selected_region = normalize_region(region)
            invalidate_session = invalidate_session or selected_region != self._region
            self._region = selected_region
        if domain_id is not None:
            selected_domain = str(domain_id).strip()
            if not selected_domain:
                raise YukiConfigError(
                    "domain_id cannot be empty. Pass the domain UUID returned by discover_domains()."
                )
            invalidate_session = invalidate_session or selected_domain != self._domain_id
            self._domain_id = selected_domain
        if admin_id is not None:
            self._admin_id = str(admin_id).strip()
        if administration_name is not None:
            self._administration_name = str(administration_name).strip()
        if invalidate_session:
            self.session_id = ""
            self.session_valid_until = _EXPIRED
        self._write_tokens()

    def authenticate(self, force: bool = False) -> str:
        """Return a session id bound to ``domain_id``.

        A stored session that is still inside its lifetime is returned without
        calling Yuki. Otherwise this authenticates, selects the domain, and
        writes the new session back to the credential store.
        """

        self._read_tokens()
        self._require_authentication_metadata()
        if self._can_reuse_session(force):
            self._trace("reusing session")
            return self.session_id

        with self._refresh_lock:
            self._start_auth()
            persist = False
            try:
                self._require_authentication_metadata()
                if self._can_reuse_session(force):
                    self._trace("reusing session")
                    return self.session_id
                self._refresh_session()
                persist = True
            finally:
                if persist:
                    self._stop_auth()
                else:
                    self._auth_in_process = False
        return self.session_id

    def list_domains(self) -> list[Domain]:
        """Return the domains visible to the current session."""

        self.authenticate()
        return list_domains(self.wsdl_url(), self.session_id, debug=self.debug, on_call=self.count_call)

    def current_domain(self) -> Domain:
        """Return the domain bound to the current session."""

        self.authenticate()
        return get_current_domain(self.wsdl_url(), self.session_id, debug=self.debug, on_call=self.count_call)

    def _can_reuse_session(self, force: bool) -> bool:
        if force or not self.session_id:
            return False
        refresh_at = self.session_valid_until - SESSION_REFRESH_SKEW
        return datetime.now(timezone.utc) < refresh_at

    def _require_authentication_metadata(self) -> None:
        missing = [
            name
            for name in ("api_key", "region", "domain_id")
            if not str(getattr(self, name) or "").strip()
        ]
        if not missing:
            return
        raise YukiConfigError(
            "Cannot authenticate, missing "
            + ", ".join(missing)
            + ". Store the missing values first with set_domain_id() or update_metadata()."
        )

    def _refresh_session(self) -> None:
        self._require_authentication_metadata()

        endpoint = self.wsdl_url()
        session_id = authenticate_access_key(
            endpoint,
            self.api_key,
            region=self.region,
            debug=self.debug,
            on_call=self.count_call,
        )
        set_current_domain(
            endpoint,
            session_id,
            self.domain_id,
            debug=self.debug,
            on_call=self.count_call,
        )
        self.session_id = session_id
        self.session_valid_until = datetime.now(timezone.utc) + SESSION_TTL

    def _return_tokens_dict(self) -> dict:
        return {
            "api_key": self.api_key,
            "region": self.region,
            "domain_id": self.domain_id,
            "admin_id": self.admin_id,
            "administration_name": self.administration_name,
            "session_id": self.session_id,
            "session_valid_until": self.session_valid_until.isoformat(),
        }

    def _apply_token_fields(self, fields: dict) -> None:
        try:
            self._api_key = str(fields["api_key"])
            self._region = normalize_region(fields["region"])
            self._domain_id = str(fields.get("domain_id") or "").strip()
        except KeyError as exc:
            raise YukiConfigError(f"Credentials are missing required field '{exc.args[0]}'") from exc
        self._admin_id = str(fields.get("admin_id") or "")
        self._administration_name = str(fields.get("administration_name") or "")
        self.session_id = fields.get("session_id") or ""
        self.session_valid_until = fields.get("session_valid_until") or _EXPIRED

    def _trace(self, message: str) -> None:
        if self.debug:
            print(f"Yuki credentials: {message}")

    @abstractmethod
    def _read_tokens(self):
        raise NotImplementedError()

    @abstractmethod
    def _write_tokens(self):
        raise NotImplementedError()

    @abstractmethod
    def _lock_tokens_external_source(self):
        """Lock the external store, then re-read tokens.

        The JSON and HVAC backends have nothing to lock. A database backend
        should lock its row and then call ``super()``, which re-reads tokens.
        """

        self._read_tokens()

    @abstractmethod
    def _unlock_tokens_external_source(self):
        """Write the latest tokens and unlock the external store."""

        self._write_tokens()

    def _start_auth(self):
        """Mark a refresh as in progress and re-read the external store.

        ``authenticate()`` already holds ``_refresh_lock``, so two threads in
        this process cannot refresh at the same time.
        """

        self._auth_in_process = True
        self._lock_tokens_external_source()

    def _stop_auth(self):
        """Persist tokens and allow the next refresh."""

        try:
            self._unlock_tokens_external_source()
        finally:
            self._auth_in_process = False


class ClientCredentialsJsonFile(ClientCredentials):
    """Credentials stored in a local JSON file.

    The file is read on authenticate and rewritten with ``session_id`` and
    ``session_valid_until`` after a refresh. There is no cross-process lock
    on the file.

    Expected shape::

        {
            "api_key": "...",
            "region": "nl",
            "domain_id": "...",
            "admin_id": "",
            "administration_name": "Example B.V.",
            "session_id": "",
            "session_valid_until": "1900-01-01T00:00:00+00:00"
        }
    """

    def __init__(self, file_path: str, *, debug: bool = False):
        self._file_path = file_path
        super().__init__(debug=debug)
        self._read_tokens()

    @property
    def file_path(self) -> str:
        return self._file_path

    def _read_tokens(self):
        if not os.path.isfile(self.file_path):
            raise YukiConfigError(f"Credentials file not found: {self.file_path}")
        with open(self.file_path, mode="r", encoding="utf-8") as credentials_file:
            credentials = json.load(credentials_file)
        if not isinstance(credentials, dict):
            raise YukiConfigError(f"Credentials file must contain a JSON object: {self.file_path}")
        self._apply_token_fields(credentials)

    def _write_tokens(self):
        directory = os.path.dirname(os.path.abspath(self.file_path)) or "."
        os.makedirs(directory, exist_ok=True)
        descriptor, temporary_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(descriptor, mode="w", encoding="utf-8") as credential_file:
                json.dump(self._return_tokens_dict(), credential_file, indent=4)
                credential_file.write("\n")
            os.replace(temporary_path, self.file_path)
        except Exception:
            if os.path.exists(temporary_path):
                os.remove(temporary_path)
            raise

    def _lock_tokens_external_source(self):
        # No cross-process lock for a local JSON file.
        super()._lock_tokens_external_source()

    def _unlock_tokens_external_source(self):
        # No cross-process lock for a local JSON file.
        super()._unlock_tokens_external_source()


class ClientCredentialsHvac(ClientCredentials):
    """Credentials stored in HashiCorp Vault KV v2.

    Secret data: ``api_key``, ``session_id``.
    Custom metadata: ``region``, ``domain_id``, ``admin_id``,
    ``administration_name``, ``session_valid_until``.

    TLS verification is disabled, matching the Admin Consult HVAC credential
    client. Pass ``verify`` to change that.
    """

    def __init__(
        self,
        url: str,
        token: str,
        mount_point: str = "",
        path: str = "yuki_api",
        *,
        verify: bool | str = False,
        debug: bool = False,
    ):
        self.client = hvac.Client(url=url, token=token, verify=verify)
        self.mount_point = mount_point
        self.path = path
        super().__init__(debug=debug)
        self._read_tokens()

    def _read_tokens(self):
        try:
            read_response = self.client.secrets.kv.v2.read_secret_version(
                mount_point=self.mount_point,
                path=self.path,
            )
        except hvac.exceptions.InvalidPath as exc:
            raise YukiConfigError(
                f"Vault secret not found at mount '{self.mount_point}' path '{self.path}'"
            ) from exc

        data = read_response.get("data", {}).get("data") or {}
        metadata = (read_response.get("data", {}).get("metadata") or {}).get("custom_metadata") or {}
        self._apply_token_fields(
            {
                "api_key": data.get("api_key", ""),
                "session_id": data.get("session_id", ""),
                "region": metadata.get("region", ""),
                "domain_id": metadata.get("domain_id", ""),
                "admin_id": metadata.get("admin_id", ""),
                "administration_name": metadata.get("administration_name", ""),
                "session_valid_until": metadata.get("session_valid_until", ""),
            }
        )

    def _write_tokens(self):
        metadata = _vault_metadata(
            {
                "region": self.region,
                "domain_id": self.domain_id,
                "admin_id": self.admin_id,
                "administration_name": self.administration_name,
                "session_valid_until": self.session_valid_until.isoformat(),
            }
        )
        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                mount_point=self.mount_point,
                path=self.path,
                secret={
                    "api_key": self.api_key,
                    "session_id": self.session_id,
                },
            )
            self.client.secrets.kv.v2.update_metadata(
                mount_point=self.mount_point,
                path=self.path,
                custom_metadata=metadata,
            )
        except hvac.exceptions.InvalidRequest as exc:
            raise YukiConfigError(
                "Vault rejected the credential metadata at "
                f"mount '{self.mount_point}' path '{self.path}'. "
                "region and domain_id must be non-empty. "
                f"Vault said: {exc}"
            ) from exc

    def _lock_tokens_external_source(self):
        # Vault KV v2 has no row lock. Re-read so a concurrent writer is observed.
        super()._lock_tokens_external_source()

    def _unlock_tokens_external_source(self):
        super()._unlock_tokens_external_source()


def _vault_metadata(fields: dict) -> dict:
    """Drop blank values. Vault custom metadata rejects empty strings."""

    metadata = {}
    for key, value in fields.items():
        text = str(value or "").strip()
        if text:
            metadata[key] = text
    return metadata


def _parse_datetime(value) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif value is None or value == "":
        return _EXPIRED
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return _EXPIRED
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise YukiError(
                "session_valid_until must be an ISO-8601 datetime"
            ) from exc
    else:
        raise YukiError(
            "session_valid_until must be a datetime or an ISO-8601 string, "
            f"got {type(value).__name__}"
        )

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
