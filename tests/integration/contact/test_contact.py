from yuki_sdk import ContactService


def test_administrations_contain_the_configured_one(yuki_cred, administration_id):
    administrations = ContactService(yuki_cred).administrations()

    assert administration_id in {administration.id for administration in administrations}


def test_suppliers_and_customers_first_page(yuki_cred):
    contacts = ContactService(yuki_cred).suppliers_and_customers(active="Both", search_option="All")

    assert all(contact.id for contact in contacts)
    assert len({contact.id for contact in contacts}) == len(contacts)


def test_contacts_in_ledger_are_found(yuki_cred, transactions):
    """A contact on a ledger line can be found by its Yuki id."""

    contact = next((row.contact for row in transactions if row.contact and row.contact.id), None)
    if contact is None:
        return
    found = ContactService(yuki_cred).search(contact.id, search_option="ID")

    assert contact.id in {item.id for item in found}


def test_supported_languages(yuki_cred):
    assert ContactService(yuki_cred).supported_languages()
