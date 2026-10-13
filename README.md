# yuki-sdk

Unofficial Python client for the [Nmbrs Accounting](https://www.nmbrs.com/) (formerly Yuki) SOAP API. This project is not affiliated with Nmbrs or Visma.

## Install

```bash
pip install yuki-sdk
```

Python 3.10 or newer.

## Credentials

You only set two values yourself: the access key and the region. The SDK fills in the rest and writes it back to the credential store.

| Field | Set by | How |
|---|---|---|
| `api_key` | you | Yuki portal: Settings → Webservices → new access key, with read access to the webservices you use. |
| `region` | you | `be` (`api.yukiworks.be`) or `nl` (`api.yukiworks.nl`). |
| `domain_id` | SDK | `DomainSet.get()` lists the domains of the key; `credentials.set_domain_id(...)` stores one. |
| `admin_id` | SDK, optional | `AdministrationSet.get()` lists the administrations of the domain; `credentials.update_metadata(admin_id=...)` stores the default. Or pass `administration_id=` to each set or record. |
| `session_id`, `session_valid_until` | SDK | Created on the first call and renewed when they expire. Never set by hand. |

### 1. Store the key and the region

In a JSON file (keep it out of git; `local/` is gitignored):

```json
{
    "api_key": "...",
    "region": "be"
}
```

Or in HashiCorp Vault (KV v2): `api_key` in the secret data, `region` in the custom metadata.

### 2. Let the SDK fill in the domain and the administration

With the example script, from the repository root:

```
python -m examples.auth.set_domain
```

It reads `local/yuki_tokens.json` (or `YUKI_CREDENTIALS`, or Vault when `VAULT_TOKEN` is set), lists the domains and administrations of the key, and stores the domain, and the administration when there is only one. With more than one, run it again with the ids to store: `python -m examples.auth.set_domain <domain_id> [<administration_id>]`. About 5 calls.

Or in code:

```python
from yuki_sdk import AdministrationSet, ClientCredentialsJsonFile, DomainSet

credentials = ClientCredentialsJsonFile("local/yuki_tokens.json")

domains = DomainSet(credentials)
domains.get()  # needs only api_key and region
credentials.set_domain_id(domains[0].id)

administrations = AdministrationSet(credentials)
administrations.get()  # opens a session bound to the domain
credentials.update_metadata(admin_id=administrations[0].id)
```

The store now holds `domain_id`, `admin_id`, `session_id` and `session_valid_until`; every later run reuses them.

"Invalid access key" or "Domain has no active database" usually means the wrong `region`.

## Usage

Like odoo-sdk: create a set or record with the credentials, fill it with `get`, then read it. The administration is `admin_id` of the credentials; pass `administration_id=` to read another one.

```python
from datetime import date

from yuki_sdk import ContactSet, Document, Period, TransactionSet

transactions = TransactionSet(credentials)
transactions.get(date(2026, 1, 1), date(2026, 12, 31))  # every page
print(transactions.count)
for line in transactions:
    print(line.date, line.gl_account_code, line.amount, line.document and line.document.id)

period = Period(credentials)
period.get(2026)
print(period.start, period.end)

contacts = ContactSet(credentials)
contacts.get_customers()

document = Document(credentials)
document.read(id="document-id")
pdf = document.file().data
```

| Area | Sets and records |
|---|---|
| General ledger | `GLAccountSet`, `TransactionSet`, `TransactionDetailSet`, `TransactionDocument`, `Period`, `StartBalanceSet`, `ProjectSet`, `ProjectBalanceSet`, `PaymentMethodSet`, `ContactDefaultValueSet`, `RGSEntrySet` |
| Balances and open items | `GLAccountBalanceSet`, `GLAccountTransactionSet`, `NetRevenue`, `OutstandingItemSet` |
| Domains and contacts | `DomainSet`, `AdministrationSet`, `ContactSet`, `LanguageSet`, `Company` |
| Archive | `DocumentFolderSet`, `DocumentFolderTabSet`, `DocumentSet`, `Document` (`file()`, `bundle()`, `ubl()`, ...) |
| VAT | `VATCodeSet`, `VATReturnSet` |
| Back office | `Workflow`, `OutstandingQuestions` |
| UBL | `FoundInvoices`, `Document.ubl()` |

A set is iterable and has `count`, `[i]` and `to_json()`. Every `get` replaces the content. Each class says in its docstring which Yuki operation it calls and how often.

Import the sets from `yuki_sdk`. Each area is one module in `yuki_sdk.webservices`: the set you construct, and the SOAP client it calls (`AccountingInfoService`, ...). Every read has a set or record; the clients stay importable for the rare case that needs the raw service call. Session, SOAP and parsing stay in `service.py`, `soap.py` and `parsing.py`.

Every call counts against the domain's daily allowance, also faults and `Authenticate`; Yuki's limit raises `YukiRateLimitError`. `credentials.calls` counts the calls of this run; with `debug=True` every call is printed with its number. Set `credentials.response_hook` to keep each raw response.

## Examples

`examples/` has one folder per webservice (`accountinginfo`, `accounting`, `contact`, `archive`, `vat`, `integration`, `ubl`, `backoffice`) plus `auth` and `raw`. Each script is a short top-level script; run it from the repository root:

```
python -m examples.auth.set_domain              # once: fills domain_id and admin_id
python -m examples.accountinginfo.get_transactions
python -m examples.archive.download_document
```

Credentials come from `local/yuki_tokens.json` (gitignored) or Vault when `VAULT_TOKEN` is set. Each script sets its period and ids at the top. Each script lists the calls it makes in its docstring; files it writes go to `local/`.

## Tests

```
pytest                  # unit tests, no calls to Yuki
pytest -m integration   # live reads, about 40 calls
```

Unit tests are in `tests/unit/`, live tests in `tests/integration/<webservice>/`. The live tests only read, are skipped without credentials, and write every response to `local/yuki/<admin_id>/raw/<run>/`. Set `YUKI_TEST_YEAR` to pick the period.

## HashiCorp Vault

```python
from yuki_sdk import ClientCredentialsHvac

credentials = ClientCredentialsHvac(url="https://vault.example", token="...", mount_point="secret", path="yuki_api")
```

Same fields as the JSON file (see [Credentials](#credentials)): `api_key` and `session_id` in the secret data, the rest in the custom metadata. TLS verification is off by default; pass `verify=True` or a CA bundle path to turn it on.

Session handling, credential fields, and errors are described in [docs/guidelines.md](docs/guidelines.md).
