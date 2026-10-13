from yuki_sdk import AdministrationSet, ContactSet, LanguageSet


def test_administrations_contain_the_configured_one(yuki_cred, administration_id):
    administrations = AdministrationSet(yuki_cred)
    administrations.get()

    assert administration_id in {administration.id for administration in administrations}


def test_contacts_first_page(yuki_cred):
    contacts = ContactSet(yuki_cred)
    contacts.get(max_pages=1)

    assert all(contact.id for contact in contacts)
    assert len({contact.id for contact in contacts}) == contacts.count


def test_contacts_in_ledger_are_found(yuki_cred, transactions):
    """A contact on a ledger line can be found by its Yuki id."""

    contact = next((row.contact for row in transactions if row.contact and row.contact.id), None)
    if contact is None:
        return
    found = ContactSet(yuki_cred)
    found.search(contact.id, search_option="ID")

    assert contact.id in {item.id for item in found}


def test_supported_languages(yuki_cred):
    languages = LanguageSet(yuki_cred)
    languages.get()

    assert languages
