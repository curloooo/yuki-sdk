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

Local examples read `.env`. When `VAULT_TOKEN` is set, `examples.auth.auth.get_cred()` uses Vault (`VAULT_URL`, `VAULT_MOUNT`, `VAULT_PATH`). Otherwise it uses the JSON file `YUKI_CREDENTIALS`, or `local/yuki_tokens.json`.

```
YUKI_CREDENTIALS=local/yuki_tokens.json
```

## HashiCorp Vault

KV v2:

- Secret data: `api_key`, `session_id`
- Custom metadata: `region`, `domain_id`, `admin_id`, `administration_name`, `session_valid_until`

Empty metadata values are omitted. Vault rejects blank custom metadata. Changing `region` or `domain_id` clears the stored session.

`ClientCredentialsHvac` disables TLS verification by default. Pass `verify=True` or a CA bundle path to enable it.

## Services

| Module | Webservice | Reads |
| --- | --- | --- |
| `webservices/accountinginfo.py` | `AccountingInfo.asmx` | `GetGLAccountScheme`, `GetTransactions` (paged), `GetTransactionDetails`, `GetPeriodDateTable`, `GetFinancialYearModifiedDate`, `GetStartBalanceByGlAccount`, `GetTransactionDocument`, `GetContactDefaultValues`, `GetCustomPaymentMethods`, `GetProjectsAndID`, `GetProjectBalance`, `GetRGSScheme` |
| `webservices/accounting.py` | `Accounting.asmx` | balances, GL account transactions, all `Outstanding*` lists, `CheckOutstandingItem*` |
| `webservices/contact.py` | `Contact.asmx` | `SearchContacts`, `GetSuppliersAndCustomers` (paged), administrations, languages |
| `webservices/vat.py` | `Vat.asmx` | `ActiveVATCodesList`, `VATReturnList` |
| `webservices/archive.py` | `Archive.asmx` | folders, tabs, document listings (paged, also "modified since"), `FindDocument`, `DocumentBundle`, `DocumentBinaryData`, `DocumentFile`, `DocumentDownloadUrl`, `DocumentXMLData`, `DocumentXMLDataAsString` |
| `webservices/integration.py` | `Integration.asmx` | `GetAdministrationData` (company phone, e-mail, IBAN, logo); uses `sessionId` / `administrationId` |
| `webservices/ubl.py` | `UBL.asmx` | `GetUBLDocument` (UBL XML of an invoice), `FindInvoices` (raw; `argXML` undocumented, but the server rejects a null, so an omitted document is sent as an empty element) |
| `webservices/backoffice.py` | `Backoffice.asmx` | `GetWorkflow`, `GetOutstandingQuestions` (documents and questions still open) |

Not wrapped, on purpose: `Tasks.asmx` (payment approval tasks), `Domains.asmx` (domain and user management), `FiscalTable.asmx` (Dutch sole-proprietor totals), `Sales.GetSalesItems`, and the archive's `DocumentImage*`, `PaymentMethods`, `CostCategories`, `Currencies`, `Menu`, `Projects`.

Writes (`ProcessJournal`, `ProcessSalesInvoices`, `UpdateContact`, uploads) are not wrapped.

## WSDL contract test

`tests/unit/fixtures/wsdl_contract.json` holds the request elements, response types and enums of every operation the SDK calls, taken from the live WSDLs (identical on the NL and BE hosts). `tests/unit/test_wsdl_contract.py` calls every public read and checks each request against it: operation name, parameter names, required parameters, value types and enum values. It also checks that every typed response field reaches the parsed value, and that the untyped layouts documented in Yuki's support articles are read completely. A new public read must be added to `READS` in that test, or the test fails.

To refresh the fixture, extract the same data from `https://api.yukiworks.be/ws/<Service>.asmx?WSDL`.

## Parsing

Typed operations come back from zeep as objects, untyped (`<any>`) operations as lxml elements, sometimes wrapped in a zeep object. `parsing.plain()` turns all of them into dicts and lists. Every dataclass has a `from_plain()` that reads that shape, so the same parser works on a zeep result, an lxml element, or a stored JSON snapshot. Yuki's empty date `0001-01-01` is read as `None`.

`parsing.get()` looks a field up exactly first, then case-insensitively: Yuki's casing differs between operations (`EmailWork` / `EMailWork`, `hID` / `HID`) and is not documented for the untyped responses.

Rows whose layout Yuki does not document (contacts, archive listings, folders, `DocumentFile`) keep every field in `fields`.

## Paging

| Read | Page size | Paging |
| --- | --- | --- |
| `GetTransactions` | `numberOfRecords` (default 100) | `startRecord` |
| `GetSuppliersAndCustomers`, `SearchContacts` | 100, fixed | `pageNumber`, 1-based |
| Archive listings | `numberOfRecords` | `startRecord` |

Whether `startRecord` counts from 0 or 1 is not documented. Every `iter_*` method (`iter_transactions`, `iter_suppliers_and_customers`, `iter_contacts`, `iter_documents*`) goes through `parsing.iter_unique_pages`: it moves on by the page length and drops ids it already returned, so an overlap of one row is harmless and no row is skipped. It stops on an empty page, a short page, or a page without new ids.

The contact iterators sort on `HID` by default, so the order stays stable between pages. The single-page methods keep their own defaults (`search`: active and inactive; `suppliers_and_customers`: active only).

`GetTransactions` takes `dataGroups`, a comma-separated list of the optional groups of a `Transaction`. Yuki does not document the accepted values; `DEFAULT_DATA_GROUPS` uses the element names from the WSDL.

`modifiedAfter` is a required element on the contact reads and `VATReturnList`; the SDK sends 1900-01-01 when no date is given. Archive date filters use `0001-01-01`, which Yuki documents as "no date selection".

## Attachments

`DocumentBinaryData` returns the bytes without a name; `DocumentFile` and `GetTransactionDocument` include the file name. `DocumentBundle` returns the documents bundled with a main document, for example the extra PDFs of a UBL invoice. Each is one call per document.

## Raw responses

`credentials.response_hook`, when set, is called after every successful read with `(service, operation, parameters, result)`. `parameters` never contains the session id. `to_jsonable(result)` turns the raw result into something `json.dump` accepts.

## General ledger field names

`GetGLAccountScheme` keeps two Yuki spellings in the SOAP payload: `descripton` and `deductableVATPercentage`. The Python attributes are `description` and `deductible_vat_percentage`.

## Errors

| Exception | When |
| --- | --- |
| `YukiConfigError` | Region is not `nl` or `be`, or `api_key` / `domain_id` is missing |
| `YukiAuthError` | Yuki rejects the access key for that region |
| `YukiSessionError` | Yuki rejects the session id |
| `YukiDomainError` | Yuki rejects the domain id, or `Domain has no active database` (administration called on the other region's host) |
| `YukiRateLimitError` | The domain daily call limit is exhausted |
| `YukiSoapError` | Any other SOAP fault |

Yuki allows 1,000 webservice calls per domain per day unless the accountant buys a higher allowance.
