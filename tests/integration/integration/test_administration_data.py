import pytest

from yuki_sdk import Company, YukiSoapError


def test_administration_data(yuki_cred, administration_id):
    company = Company(yuki_cred, administration_id)
    try:
        company.get()
    except YukiSoapError as error:
        # Seen with the curlo-test key (rights: all webservices): "A server-side error has occurred"
        # for a request that matches the WSDL. Cause unknown.
        pytest.xfail(f"GetAdministrationData fails on Yuki's side: {error}")

    assert company.company_name
