import os

from dotenv import load_dotenv

from yuki_sdk import ClientCredentials

from .hashicorp_vault import get_cred_hvac
from .local_json import get_cred_json

load_dotenv(".env")


def get_cred() -> ClientCredentials:
    """Return Vault credentials when ``VAULT_TOKEN`` is set, otherwise the local JSON file."""

    if os.getenv("VAULT_TOKEN"):
        return get_cred_hvac(url=os.getenv("VAULT_URL"))
    return get_cred_json()
