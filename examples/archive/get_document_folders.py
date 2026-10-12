"""Archive folders, the tabs of a folder, and document counts per folder.

Calls: DocumentFolders, DocumentFolderTabs, DocumentFolderCounts.
"""

from datetime import date

from yuki_sdk import DocumentFolderSet, DocumentFolderTabSet

from examples.auth.auth import get_cred

YEAR = date.today().year

yuki_cred = get_cred()

folders = DocumentFolderSet(yuki_cred)
folders.get()
print(f"{folders.count} folders")
for folder in folders:
    print(f"{folder.id}  {folder.name}")

if folders.count == 0:
    exit()

tabs = DocumentFolderTabSet(yuki_cred)
tabs.get(folders[0].id)
for tab in tabs:
    print(f"  tab {tab.id}  {tab.name}")

folders.get_counts(YEAR)
for folder in folders:
    print(f"{folder.name}: {folder.fields}")
