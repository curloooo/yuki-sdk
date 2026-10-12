import pytest

from yuki_sdk import UblService, YukiError


def test_ubl_document_of_a_ledger_document(yuki_cred, administration_id, document_id):
    """Which id GetUBLDocument expects is not documented; this tries the archive document id."""

    try:
        ubl = UblService(yuki_cred).ubl_document(administration_id, document_id)
    except YukiError as error:
        pytest.xfail(f"GetUBLDocument does not take the archive document id: {error}")
    assert ubl is None or ubl.lstrip().startswith("<")
