from yuki_sdk import ArchiveService


def test_folders_and_tabs(yuki_cred, folders):
    assert folders
    assert all(folder.id is not None and folder.name for folder in folders)

    tabs = ArchiveService(yuki_cred).document_folder_tabs(folders[0].id)
    assert all(tab.id is not None for tab in tabs)


def test_documents_of_period(yuki_cred, period):
    start, end = period
    documents = ArchiveService(yuki_cred).documents(start_date=start, end_date=end, number_of_records=20)

    assert all(document.id for document in documents)


def test_document_of_a_ledger_line(yuki_cred, document_id):
    service = ArchiveService(yuki_cred)

    document = service.find_document(document_id)
    assert document is not None and document.id == document_id

    bundle = service.document_bundle(document_id)
    assert all(item.id for item in bundle)

    archived = service.document_file(document_id)
    assert archived.data, "a booked document has a file"
    assert archived.file_name
