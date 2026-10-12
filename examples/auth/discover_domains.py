"""List the domains visible to the access key, before a domain is chosen.

Calls: Authenticate, Domains.
"""

from yuki_sdk import discover_domains

from examples.auth.auth import get_cred

yuki_cred = get_cred()

domains = discover_domains(yuki_cred.api_key, yuki_cred.region)
print(f"{len(domains)} domains visible in region {yuki_cred.region}")
for domain in domains:
    print(f"{domain.id}  {domain.name}  {domain.url or ''}  {domain.status or ''}")
