# yuki-sdk

Unofficial Python client for the [Nmbrs Accounting](https://www.nmbrs.com/) (formerly Yuki) SOAP API. This project is not affiliated with Nmbrs or Visma.

## Install

```bash
pip install yuki-sdk
```

Python 3.10 or newer.

## Credentials

Create an access key in Yuki, then store it in a JSON file:

```json
{
    "api_key": "...",
    "region": "be",
    "domain_id": "..."
}
```

`region` is `nl` or `be`. Keep this file out of git.

```python
from yuki_sdk import ClientCredentialsJsonFile, DomainSet

credentials = ClientCredentialsJsonFile(r"C:\path\to\yuki_api_default.json")
domains = DomainSet(credentials)
domains.get()  # needs only api_key and region
for domain in domains:
    print(domain.id, domain.name)
```

`python -m examples.auth.set_domain` lists the domains and administrations of the key and stores the domain.

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

Every call counts against the domain's daily allowance, also faults and `Authenticate`; Yuki's limit raises `YukiRateLimitError`. Set `credentials.response_hook` to keep each raw response.

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

credentials = ClientCredentialsHvac(
    url="https://vault.example",
    token="...",
    mount_point="secret",
    path="yuki_api",
)
credentials.authenticate()
```

TLS verification is off by default. Pass `verify=True` or a CA bundle path to turn it on.

Session handling, credential fields, and errors are described in [docs/guidelines.md](docs/guidelines.md).
