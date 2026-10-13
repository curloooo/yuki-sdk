from yuki_sdk import OutstandingQuestions, Workflow


def test_workflow_and_questions(yuki_cred, administration_id):
    Workflow(yuki_cred, administration_id).get()
    OutstandingQuestions(yuki_cred, administration_id).get()
