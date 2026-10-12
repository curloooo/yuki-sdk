"""One archive document: its data, the documents bundled with it, its download link and XML data.

Calls: Documents (first page) when no document is given, then FindDocument, DocumentBundle,
DocumentDownloadUrl, DocumentXmlData.
"""

from datetime import date

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

document = Document(yuki_cred)
document.read(id=document_id)
print(f"{document.id}  {document.subject}  {document.document_date}  {document.amount}  {document.folder}/{document.tab}")

for bundled in document.bundle():
    print(f"bundled: {bundled.id}  {bundled.file_name}  {bundled.subject}")

print(f"download url: {document.download_url()}")
print(f"xml data: {document.xml_data()}")
