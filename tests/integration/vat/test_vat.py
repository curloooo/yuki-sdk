from yuki_sdk import VATCodeSet, VATReturnSet


def test_active_vat_codes(yuki_cred, administration_id, transactions):
    codes = VATCodeSet(yuki_cred, administration_id)
    codes.get()

    assert codes
    assert all(code.type is not None for code in codes)


def test_vat_returns(yuki_cred, administration_id, year):
    returns = VATReturnSet(yuki_cred, administration_id)
    returns.get(year)

    for vat_return in returns:
        assert vat_return.start_date and vat_return.end_date
