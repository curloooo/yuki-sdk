"""Authenticate and show the domains of the key and the domain the session is bound to.

Calls: Authenticate + SetCurrentDomain (skipped while the stored session is valid),
Authenticate + Domains, GetCurrentDomain.
"""

from yuki_sdk import DomainSet

from examples.auth.auth import get_cred

yuki_cred = get_cred()

session_id = yuki_cred.authenticate()
print(f"region={yuki_cred.region} session_ready={bool(session_id)} valid_until={yuki_cred.session_valid_until}")

domains = DomainSet(yuki_cred)
domains.get()
for domain in domains:
    print(f"{domain.id}  {domain.name}  {domain.url or ''}  {domain.status or ''}")

current = DomainSet(yuki_cred)
current.get_current()
print(f"current domain: {current[0].id}  {current[0].name}")
