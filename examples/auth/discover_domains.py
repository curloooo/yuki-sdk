"""List the domains visible to the access key in ``.env``.

Requires ``API_KEY``. ``YUKI_REGION`` defaults to ``nl`` and must be ``nl`` or ``be``.
"""

import os

from dotenv import load_dotenv

from src import discover_domains


def main() -> None:
    load_dotenv(".env")
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise RuntimeError("Set API_KEY in .env")
    region = os.getenv("YUKI_REGION", "nl")
    for domain in discover_domains(api_key, region):
        print(f"{domain.id}  {domain.name}  {domain.url or ''}  {domain.status or ''}")


if __name__ == "__main__":
    main()
