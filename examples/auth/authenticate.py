"""Authenticate with the JSON or Vault credentials selected by ``.env``."""

from .auth import get_cred


def main() -> None:
    credentials = get_cred()
    session_id = credentials.authenticate()
    print(f"region={credentials.region} session_ready={bool(session_id)}")
    for domain in credentials.list_domains():
        print(f"{domain.id}  {domain.name}  {domain.url or ''}")
    current = credentials.current_domain()
    print(f"current_domain={current.id}  {current.name}")


if __name__ == "__main__":
    main()
