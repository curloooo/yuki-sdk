"""Authenticate and show the domain the session is bound to.

Calls: Authenticate + SetCurrentDomain (skipped while the stored session is valid), Domains, GetCurrentDomain.
"""

from examples.auth.auth import get_cred

yuki_cred = get_cred()

session_id = yuki_cred.authenticate()
print(f"region={yuki_cred.region} session_ready={bool(session_id)} valid_until={yuki_cred.session_valid_until}")

for domain in yuki_cred.list_domains():
    print(f"{domain.id}  {domain.name}  {domain.url or ''}  {domain.status or ''}")

current = yuki_cred.current_domain()
print(f"current domain: {current.id}  {current.name}")
