from yuki_sdk import VatService


def test_active_vat_codes(yuki_cred, administration_id, transactions):
    codes = VatService(yuki_cred).active_vat_codes(administration_id)

    assert codes
    assert all(code.type is not None for code in codes)


def test_vat_returns(yuki_cred, administration_id, year):
    for vat_return in VatService(yuki_cred).vat_returns(administration_id, year):
        assert vat_return.start_date and vat_return.end_date
