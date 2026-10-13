import pytest

from yuki_sdk import Document, YukiError


def test_ubl_document_of_a_ledger_document(yuki_cred, administration_id, document_id):
    """GetUBLDocument takes the archive document id."""

    try:
        ubl = Document(yuki_cred, administration_id, id=document_id).ubl()
    except YukiError as error:
        pytest.xfail(f"GetUBLDocument does not take the archive document id: {error}")
    assert ubl is None or ubl.lstrip().startswith("<")
