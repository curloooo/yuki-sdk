"""List the domains visible to the access key, before a domain is chosen.

Calls: Authenticate, Domains.
"""

from yuki_sdk import DomainSet

from examples.auth.auth import get_cred

yuki_cred = get_cred()

domains = DomainSet(yuki_cred)
domains.get()
print(f"{domains.count} domains visible in region {yuki_cred.region}")
for domain in domains:
    print(f"{domain.id}  {domain.name}  {domain.url or ''}  {domain.status or ''}")
