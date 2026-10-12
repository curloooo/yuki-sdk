"""Fill ``domain_id`` and ``admin_id`` in the stored credentials.

Takes the domain and the administration when the key sees exactly one; with
more, prints them and sets nothing. Pass a domain id and an administration id
to choose: ``python -m examples.auth.set_domain <domain_id> <admin_id>``.

Calls: Authenticate, Domains, then Authenticate, SetCurrentDomain, Administrations.
"""

import sys

from yuki_sdk import ContactService, discover_domains

from examples.auth.auth import get_cred

yuki_cred = get_cred()
wanted_domain = sys.argv[1] if len(sys.argv) > 1 else None
wanted_administration = sys.argv[2] if len(sys.argv) > 2 else None

domains = discover_domains(yuki_cred.api_key, yuki_cred.region)
for domain in domains:
    print(f"domain {domain.id}  {domain.name}  {domain.status or ''}")

domain_id = wanted_domain or (domains[0].id if len(domains) == 1 else None)
if not domain_id:
    sys.exit("More than one domain: pass the domain id as the first argument.")
yuki_cred.set_domain_id(domain_id)
print(f"domain_id = {domain_id}")

administrations = ContactService(yuki_cred).administrations()
for administration in administrations:
    print(f"administration {administration.id}  {administration.name}  start={administration.start_date}")

chosen = next((a for a in administrations if a.id == wanted_administration), None)
if chosen is None and len(administrations) == 1:
    chosen = administrations[0]
if chosen is None:
    sys.exit("More than one administration: pass the administration id as the second argument.")
yuki_cred.update_metadata(admin_id=chosen.id, administration_name=chosen.name or "")
print(f"admin_id = {chosen.id} ({chosen.name})")
