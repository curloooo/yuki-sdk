"""Read every Contact webservice method and print a short summary."""

from src import ContactService

from examples.auth.auth import get_cred
from examples.sample_ids import ADMINISTRATION_ID


def main() -> None:
    credentials = get_cred()
    service = ContactService(credentials)
    contacts = service.search("")
    print(f"SearchContacts: {len(contacts)}")
    for contact in contacts[:5]:
        print(f"  {contact.id}  {contact.name}  customer={contact.is_customer} supplier={contact.is_supplier}")

    relations = service.suppliers_and_customers()
    print(f"GetSuppliersAndCustomers: {len(relations)}")

    administrations = service.administrations()
    print(f"Administrations: {len(administrations)}")
    for administration in administrations:
        print(f"  {administration.id}  {administration.name}  domain={administration.domain_id}")

    coded = service.administrations_with_internal_customer_code()
    print(f"AdministrationsWithInternalCustomerCode: {len(coded)}")
    companies = service.companies()
    print(f"Companies: {len(companies)}")
    if administrations:
        found = service.administration_id(administrations[0].name or "")
        print(f"AdministrationID({administrations[0].name}): {found}")
    print(f"Language: {service.language()}")
    print("SupportedLanguages:")
    for language in service.supported_languages():
        print(f"  {language.code}  {language.description}  {language.native_description}")
    print(f"example administration id: {ADMINISTRATION_ID}")


if __name__ == "__main__":
    main()
