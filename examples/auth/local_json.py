import os

from dotenv import load_dotenv

from src import ClientCredentialsJsonFile

load_dotenv(".env")


def get_cred_json(client: str = "default") -> ClientCredentialsJsonFile:
    credentials_dir = os.environ.get("credentials_dir")
    if not credentials_dir:
        raise RuntimeError("Set credentials_dir in .env to the folder that holds the Yuki JSON files.")
    return ClientCredentialsJsonFile(
        file_path=os.path.join(credentials_dir, f"yuki_api_{client}.json")
    )
