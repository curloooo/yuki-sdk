# Guidelines

Notes for working on this SDK. The [Postman collection](https://documenter.getpostman.com/view/12207912/UVCBB51L) is the reference for the Yuki webservices.

## Authentication

An access key is created inside a Yuki administration. The key only reaches the domains it was granted. Yuki also supports domain keys and accountant portal keys. Each key authenticates with `Authenticate(accessKey)`.

A session id is valid for 24 hours, or until the client closes the connection. This SDK stores the session for 23 hours and refreshes it five minutes early. `authenticate()` calls Yuki again only when the stored session is missing, expired, or `force=True`.

| Region | Host |
| --- | --- |
| `nl` | `https://api.yukiworks.nl` |
| `be` | `https://api.yukiworks.be` |

Authentication uses only the configured host. A rejected key is not retried on the other region.

The session flow, against the Sales WSDL, is:

1. `Authenticate(accessKey)` returns a session id.
2. `Domains(sessionID)` lists the domains this key can see.
3. `SetCurrentDomain(sessionID, domainID)` binds the session.

`YukiService.invoke` calls `authenticate()` and retries once with `force=True` when Yuki rejects the session. Read methods for Contact, Accounting, and AccountingInfo go through that base class. Write operations are not wrapped.

`debug=True` prints SOAP operation names and the WSDL URL. It does not print the access key or parameter values.

## JSON credentials

```json
{
    "api_key": "...",
    "region": "be",
    "domain_id": "...",
    "admin_id": "",
    "administration_name": "Example B.V.",
    "session_id": "",
    "session_valid_until": "1900-01-01T00:00:00+00:00"
}
```

`authenticate()` writes `session_id` and `session_valid_until` after a successful refresh. `domain_id` is required before authentication. Set it with `set_domain_id()` or `update_metadata()`.

Local examples read `.env`. When `VAULT_TOKEN` is set, `examples.auth.auth.get_cred()` uses Vault (`VAULT_URL`, `VAULT_MOUNT`, `VAULT_PATH`). Otherwise it uses the JSON file in `credentials_dir`.

```
credentials_dir=C:\path\to\credential-files
API_KEY=...
YUKI_REGION=be
```

## HashiCorp Vault

KV v2:

- Secret data: `api_key`, `session_id`
- Custom metadata: `region`, `domain_id`, `admin_id`, `administration_name`, `session_valid_until`

Empty metadata values are omitted. Vault rejects blank custom metadata. Changing `region` or `domain_id` clears the stored session.

`ClientCredentialsHvac` disables TLS verification by default. Pass `verify=True` or a CA bundle path to enable it.

## General ledger field names

`GetGLAccountScheme` keeps two Yuki spellings in the SOAP payload: `descripton` and `deductableVATPercentage`. The Python attributes are `description` and `deductible_vat_percentage`.

## Errors

| Exception | When |
| --- | --- |
| `YukiConfigError` | Region is not `nl` or `be`, or `api_key` / `domain_id` is missing |
| `YukiAuthError` | Yuki rejects the access key for that region |
| `YukiSessionError` | Yuki rejects the session id |
| `YukiDomainError` | Yuki rejects the domain id |
| `YukiRateLimitError` | The domain daily call limit is exhausted |
| `YukiSoapError` | Any other SOAP fault |

Yuki allows 1,000 webservice calls per domain per day unless the accountant buys a higher allowance.
