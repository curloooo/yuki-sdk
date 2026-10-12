"""Administrations and companies of the domain.

Calls: Administrations, AdministrationsWithInternalCustomerCode, Companies.
"""

from yuki_sdk import AdministrationSet

from examples.auth.auth import get_cred

yuki_cred = get_cred()

administrations = AdministrationSet(yuki_cred)
administrations.get()
print(f"{administrations.count} administrations")
for administration in administrations:
    print(f"{administration.id}  {administration.name}  start={administration.start_date}  active={administration.active}")
    print(f"    {administration.address_line} {administration.address_line_2 or ''}, {administration.postcode} {administration.city} {administration.country}")
    print(f"    vat={administration.vat_number}  coc={administration.coc_number}")

administrations.get_with_internal_customer_code()
for administration in administrations:
    print(f"{administration.name}  internal code={administration.internal_customer_code}")

administrations.get_companies()
print(f"{administrations.count} companies")
