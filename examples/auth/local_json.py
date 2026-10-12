import os

from dotenv import load_dotenv

from yuki_sdk import ClientCredentialsJsonFile

load_dotenv(".env")

DEFAULT_FILE = os.path.join("local", "yuki_tokens.json")


def get_cred_json(file_path: str | None = None) -> ClientCredentialsJsonFile:
    """Return the JSON-file credentials.

    The file is ``YUKI_CREDENTIALS`` from ``.env`` or ``local/yuki_tokens.json``
    (gitignored). Only ``api_key`` and ``region`` have to be filled in by hand;
    run ``python -m examples.auth.set_domain`` once to fill ``domain_id`` and
    ``admin_id``.
    """

    return ClientCredentialsJsonFile(file_path=file_path or os.getenv("YUKI_CREDENTIALS") or DEFAULT_FILE)
