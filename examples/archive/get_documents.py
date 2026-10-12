"""Archive documents of a period: all, per folder, per tab and per type.

Calls: one call per page for each get, plus DocumentFolders and DocumentFolderTabs.
"""

from datetime import date

from yuki_sdk import DocumentFolderSet, DocumentFolderTabSet, DocumentSet

from examples.auth.auth import get_cred

START = date(date.today().year, 1, 1)
END = date(date.today().year, 12, 31)

yuki_cred = get_cred()

documents = DocumentSet(yuki_cred)
documents.get(START, END)
print(f"{documents.count} documents in {START}..{END}")
for document in documents[:5]:
    print(f"{document.id}  {document.document_date}  {document.subject}  {document.amount}")
    print(f"    folder={document.folder_id}/{document.folder}  tab={document.tab_id}/{document.tab}  type={document.type}/{document.type_description}")
    print(f"    contact={document.contact_name} ({document.contact_id})  file={document.file_name} {document.content_type} {document.file_size} bytes")

folders = DocumentFolderSet(yuki_cred)
folders.get()
if folders.count:
    in_folder = DocumentSet(yuki_cred)
    in_folder.get_in_folder(folders[0].id, START, END)
    print(f"{in_folder.count} documents in folder {folders[0].name}")
    tabs = DocumentFolderTabSet(yuki_cred)
    tabs.get(folders[0].id)
    if tabs.count:
        in_tab = DocumentSet(yuki_cred)
        in_tab.get_in_tab(tabs[0].id, START, END)
        print(f"{in_tab.count} documents in tab {tabs[0].name}")

document_type = next((d.type for d in documents if d.type is not None), None)
if document_type is not None:
    of_type = DocumentSet(yuki_cred)
    of_type.get_by_type(int(document_type), START, END)
    print(f"{of_type.count} documents of type {document_type}")
