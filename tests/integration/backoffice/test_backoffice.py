from yuki_sdk import BackofficeService


def test_workflow_and_questions(yuki_cred, administration_id):
    service = BackofficeService(yuki_cred)

    service.workflow(administration_id)
    service.outstanding_questions(administration_id)
