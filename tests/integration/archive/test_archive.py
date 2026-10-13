from yuki_sdk import Document, DocumentFolderTabSet, DocumentSet


def test_folders_and_tabs(yuki_cred, folders):
    assert folders
    assert all(folder.id is not None and folder.name for folder in folders)

    tabs = DocumentFolderTabSet(yuki_cred)
    tabs.get(folders[0].id)
    assert all(tab.id is not None for tab in tabs)


def test_documents_of_period(yuki_cred, period):
    start, end = period
    documents = DocumentSet(yuki_cred)
    documents.get_page(start, end, number_of_records=20)

    assert all(document.id for document in documents)


def test_document_of_a_ledger_line(yuki_cred, document_id):
    document = Document(yuki_cred)
    document.read(document_id)
    assert document.id == document_id

    bundle = document.bundle()
    assert all(item.id for item in bundle)

    archived = document.file()
    assert archived.data, "a booked document has a file"
    assert archived.file_name
