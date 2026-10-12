import os
import urllib3
from dotenv import load_dotenv

from yuki_sdk import ClientCredentialsHvac

load_dotenv(".env")


def get_cred_hvac(url: str | None = None) -> ClientCredentialsHvac:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    return ClientCredentialsHvac(
        url=url or os.getenv("VAULT_URL") or "http://localhost:8200",
        token=os.getenv("VAULT_TOKEN") or "",
        mount_point=os.getenv("VAULT_MOUNT") or "",
        path=os.getenv("VAULT_PATH") or "yuki_api",
    )
