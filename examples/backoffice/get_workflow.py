"""Documents that wait in the back-office workflow.

Calls: GetWorkflow.
"""

from yuki_sdk import Workflow

from examples.auth.auth import get_cred

yuki_cred = get_cred()

workflow = Workflow(yuki_cred)
workflow.get()
print(str(workflow.data)[:1000])
