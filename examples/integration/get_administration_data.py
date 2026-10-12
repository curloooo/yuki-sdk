"""Company data of the administration: contact person, phone, bank account and logos.

Calls: GetAdministrationData. Writes the logos to local/downloads/.
"""

from pathlib import Path

from yuki_sdk import Company

from examples.auth.auth import get_cred

yuki_cred = get_cred()

company = Company(yuki_cred)
company.get()
print(f"{company.company_name}  {company.description}")
print(f"{company.address_line_1} {company.address_line_2 or ''}, {company.postcode} {company.city} {company.country}")
print(f"contact={company.main_contact_name} <{company.main_contact_email}>  phone={company.phone_work}  mobile={company.mobile_work}")
print(f"iban={company.iban} ({company.bank_account_name})  vat={company.vat_number}  coc={company.coc_number}")

for name, logo in (("company_logo", company.company_logo), ("navigation_logo", company.navigation_logo)):
    if logo:
        target = Path("local/downloads") / f"{name}.img"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(logo)
        print(f"{name}: {len(logo)} bytes written to {target.resolve()}")
