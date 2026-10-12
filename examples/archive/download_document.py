"""Download the file of an archive document to local/downloads/.

Calls: Documents (one page) when no document is given, then DocumentFile.
"""

from datetime import date
from pathlib import Path

from yuki_sdk import Document, DocumentSet

from examples.auth.auth import get_cred

START = date(date.today().year, 1, 1)
END = date(date.today().year, 12, 31)
DOCUMENT_ID = None  # a Yuki document id; None takes the first one found

yuki_cred = get_cred()

document_id = DOCUMENT_ID
if document_id is None:
    documents = DocumentSet(yuki_cred)
    documents.get_page(START, END, number_of_records=10)
    document_id = documents[0].id if documents.count else None
if document_id is None:
    print("No document in the period")
    exit()

# No read() needed: the file only needs the id.
archived = Document(yuki_cred, id=document_id).file()
print(f"{document_id}: {archived.file_name}  {len(archived.data or b'')} bytes")
if archived.data:
    target = Path("local/downloads") / (archived.file_name or f"{document_id}.bin")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(archived.data)
    print(f"written to {target.resolve()}")
