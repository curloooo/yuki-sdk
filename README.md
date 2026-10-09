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
from yuki_sdk import ClientCredentialsJsonFile

credentials = ClientCredentialsJsonFile(r"C:\path\to\yuki_api_default.json")
credentials.authenticate()
for domain in credentials.list_domains():
    print(domain.id, domain.name)
```

## Usage

```python
from datetime import date

from yuki_sdk import AccountingService, ContactService, GLAccountScheme

accounts = GLAccountScheme(credentials, "administration-id").get()
contacts = ContactService(credentials).search("Numerix")
balances = AccountingService(credentials).gl_account_balance("administration-id", date.today())
```

Scripts in `examples/` cover domains, contacts, accounting, and a transaction CSV export.

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
