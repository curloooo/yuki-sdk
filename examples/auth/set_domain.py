"""Show the domains and administrations an access key sees, and store the domain.

    python -m examples.auth.set_domain [domain_id] [administration_id]

With one domain it is stored; with more, pass the one to store. The administrations
of that domain are listed; one (or the one passed) is stored as ``admin_id``, the
default administration of the examples. The migrator takes the administration per run.

Calls: Authenticate, Domains, then Authenticate, SetCurrentDomain, Administrations.
"""

import sys

from yuki_sdk import AdministrationSet, DomainSet

from examples.auth.auth import get_cred

yuki_cred = get_cred()
wanted_domain = sys.argv[1] if len(sys.argv) > 1 else None
wanted_administration = sys.argv[2] if len(sys.argv) > 2 else None

domains = DomainSet(yuki_cred)
domains.get()
for domain in domains:
    print(f"domain {domain.id}  {domain.name}  {domain.status or ''}")

domain_id = wanted_domain or (domains[0].id if domains.count == 1 else None)
if not domain_id:
    sys.exit("More than one domain: pass the domain id as the first argument.")
yuki_cred.set_domain_id(domain_id)
print(f"domain_id = {domain_id}")

administrations = AdministrationSet(yuki_cred)
administrations.get()
for administration in administrations:
    print(f"administration {administration.id}  {administration.name}  start={administration.start_date}")

administration_id = wanted_administration or (administrations[0].id if administrations.count == 1 else None)
if administration_id:
    yuki_cred.update_metadata(admin_id=administration_id)
    print(f"admin_id = {administration_id}")