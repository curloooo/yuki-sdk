"""Keep every raw response of a run as JSON, through ``response_hook``.

The hook sees each successful call after parsing; this is how a bulk extract
stores what Yuki sent before any mapping. Files go to local/raw/.

Calls: ActiveVATCodesList, DocumentFolders.
"""

import json
from itertools import count
from pathlib import Path

from yuki_sdk import DocumentFolderSet, VATCodeSet, to_jsonable

from examples.auth.auth import get_cred

yuki_cred = get_cred()
output = Path("local/raw")
output.mkdir(parents=True, exist_ok=True)
numbers = count(1)


def keep_raw(service, operation, parameters, result):
    path = output / f"{next(numbers):02d}_{service}_{operation}.json"
    payload = {"parameters": to_jsonable(parameters), "result": to_jsonable(result)}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"saved {path}")


yuki_cred.response_hook = keep_raw

VATCodeSet(yuki_cred).get()
DocumentFolderSet(yuki_cred).get()
