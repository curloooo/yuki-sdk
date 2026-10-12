"""The mapping of the Yuki accounts on the reference scheme (RGS).

Calls: GetRGSScheme.
"""

from yuki_sdk import RGSEntrySet

from examples.auth.auth import get_cred

yuki_cred = get_cred()

entries = RGSEntrySet(yuki_cred)
entries.get()
print(f"{entries.count} RGS entries")
for entry in entries[:10]:
    print(f"{entry.yuki_code}  {entry.yuki_description}  -> {entry.rgs_reference_code} {entry.rgs_description}  enabled={entry.yuki_is_enabled}")
