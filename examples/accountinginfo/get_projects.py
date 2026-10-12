"""Projects (the analytic dimension) and their balance per account.

Calls: GetProjectsAndID, GetProjectBalance.
"""

from datetime import date

from yuki_sdk import ProjectBalanceSet, ProjectSet

from examples.auth.auth import get_cred

START = date(date.today().year, 1, 1)
END = date(date.today().year, 12, 31)

yuki_cred = get_cred()

projects = ProjectSet(yuki_cred)
projects.get()
print(f"{projects.count} projects")
for project in projects[:10]:
    print(f"{project.code}  {project.description}  {project.start_date}..{project.end_date}  contact={project.contact}  tags={project.tags}")

if projects.count == 0:
    exit()

balances = ProjectBalanceSet(yuki_cred)
balances.get(START, END, project_code=projects[0].code or "")
print(f"{balances.count} balance lines for project {projects[0].code}")
for balance in balances[:10]:
    print(f"{balance.gl_account_code}  {balance.amount}")
