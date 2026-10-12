"""Search the archive, and list the documents changed since a date (for a refresh run).

Calls: SearchDocuments, DocumentFolders, ModifiedDocumentsInFolder (one per page).
"""

from datetime import date

from yuki_sdk import DocumentFolderSet, DocumentSearchOption, DocumentSet

from examples.auth.auth import get_cred

yuki_cred = get_cred()

found = DocumentSet(yuki_cred)
found.search("factuur", search_option=DocumentSearchOption.SUBJECT, number_of_records=10)
print(f"{found.count} documents with 'factuur' in the subject")
for document in found:
    print(f"{document.id}  {document.document_date}  {document.subject}")

folders = DocumentFolderSet(yuki_cred)
folders.get()
if folders.count:
    since = date(date.today().year, 1, 1)
    changed = DocumentSet(yuki_cred)
    changed.get_modified_in_folder(folders[0].id, since)
    print(f"{changed.count} documents in {folders[0].name} changed since {since}")
