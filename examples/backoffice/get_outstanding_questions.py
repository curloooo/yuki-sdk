"""Open back-office questions of the administration.

Calls: GetOutstandingQuestions.
"""

from yuki_sdk import OutstandingQuestions

from examples.auth.auth import get_cred

yuki_cred = get_cred()

questions = OutstandingQuestions(yuki_cred)
questions.get()
print(str(questions.data)[:1000])
