"""Print the general ledger scheme for one administration."""

from src import GLAccountScheme

from examples.auth.auth import get_cred

ADMINISTRATION_ID = "e7c4b218-deba-437d-844d-d022e355d263"


def main() -> None:
    credentials = get_cred()
    credentials.set_domain_id('7c0445a0-99fe-44ec-8f71-2747747955cd')
    accounts = GLAccountScheme(credentials, ADMINISTRATION_ID).get()
    print(f"{len(accounts)} general ledger accounts")
    for account in accounts:
        print(f"{account.code}  {account.description}")


if __name__ == "__main__":
    main()
