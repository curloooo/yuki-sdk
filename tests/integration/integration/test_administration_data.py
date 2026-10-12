import pytest

from yuki_sdk import IntegrationService, YukiSoapError


def test_administration_data(yuki_cred, administration_id):
    try:
        company = IntegrationService(yuki_cred).administration_data(administration_id)
    except YukiSoapError as error:
        # Seen with the curlo-test key (rights: all webservices): "A server-side error has occurred"
        # for a request that matches the WSDL. Cause unknown.
        pytest.xfail(f"GetAdministrationData fails on Yuki's side: {error}")

    assert company.company_name
