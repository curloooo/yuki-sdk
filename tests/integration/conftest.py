"""Live fixtures for the integration tests.

These tests call Yuki and count against the daily call limit (about 50 calls for
the whole suite), so ``pytest`` leaves them out. Run them with::

    pytest -m integration

Credentials come from ``YUKI_CREDENTIALS`` (``.env``) or ``local/yuki_tokens.json``
with ``domain_id`` and ``admin_id`` filled in (``python -m examples.auth.set_domain``).
Every successful response is written to ``local/yuki/<admin_id>/raw/<run>/`` so its
shape can be checked and turned into a unit-test fixture without calling again.
The tests only read; none of them writes to Yuki.
"""

import json
import os
from datetime import date, datetime
from itertools import count
from pathlib import Path

import pytest
from dotenv import load_dotenv

from yuki_sdk import AccountingInfoService, ArchiveService, ClientCredentialsJsonFile, to_jsonable

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

YEAR = int(os.getenv("YUKI_TEST_YEAR") or date.today().year)


@pytest.fixture(scope="session")
def yuki_cred() -> ClientCredentialsJsonFile:
    path = Path(os.getenv("YUKI_CREDENTIALS") or ROOT / "local" / "yuki_tokens.json")
    if not path.is_file():
        pytest.skip(f"Yuki credentials not found at {path}")
    credentials = ClientCredentialsJsonFile(str(path))
    if not credentials.admin_id:
        pytest.skip("admin_id is empty: run python -m examples.auth.set_domain first")

    output = ROOT / "local" / "yuki" / credentials.admin_id / "raw" / datetime.now().strftime("%Y%m%d-%H%M%S")
    output.mkdir(parents=True, exist_ok=True)
    numbers = count(1)

    def keep_raw(service, operation, parameters, result):
        payload = {"service": service, "operation": operation, "parameters": to_jsonable(parameters), "result": to_jsonable(result)}
        path = output / f"{next(numbers):03d}_{service}_{operation}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    credentials.response_hook = keep_raw
    return credentials


@pytest.fixture(scope="session")
def administration_id(yuki_cred) -> str:
    return yuki_cred.admin_id


@pytest.fixture(scope="session")
def year() -> int:
    return YEAR


@pytest.fixture(scope="session")
def period() -> tuple[date, date]:
    return date(YEAR, 1, 1), date(YEAR, 12, 31)


@pytest.fixture(scope="session")
def transactions(yuki_cred, administration_id, period):
    """The first 100 general ledger lines of the period, shared by the tests (one call)."""

    start, end = period
    rows = AccountingInfoService(yuki_cred).transactions(administration_id, start, end, number_of_records=100)
    if not rows:
        pytest.skip(f"no transactions in {start}..{end}; set YUKI_TEST_YEAR")
    return rows


@pytest.fixture(scope="session")
def document_id(transactions) -> str:
    found = next((row.document.id for row in transactions if row.document and row.document.id), None)
    if found is None:
        pytest.skip("no transaction with a document on the first page")
    return found


@pytest.fixture(scope="session")
def folders(yuki_cred):
    """Archive folders, shared by the tests (one call)."""

    return ArchiveService(yuki_cred).document_folders()
