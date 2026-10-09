"""List the domains visible to the stored access key.

Uses the Vault or JSON credentials from ``.env``. This does not require
``domain_id``. Copy one of the printed ids into ``set_domain_id()``.
"""

from src import discover_domains

from examples.auth.auth import get_cred


def main() -> None:
    credentials = get_cred()
    domains = discover_domains(credentials.api_key, credentials.region)
    print(f"region={credentials.region}")
    if not domains:
        print("No domains are visible to this access key.")
        return
    for domain in domains:
        print(f"{domain.id}  {domain.name}  {domain.url or ''}  {domain.status or ''}")
        print(f"credentials.set_domain_id({domain.id!r})")


if __name__ == "__main__":
    main()
