from fastapi.testclient import TestClient
from app.workbench import create_workbench
from tests.test_workbench_flow import diagnose


def test_probe_private_immutable_and_does_not_claim_mastery():
    with TestClient(create_workbench()) as user, TestClient(create_workbench()) as other:
        user.post('/api/session'); other.post('/api/session')
        d = diagnose(user)
        path = '/api/diagnoses/' + d['id'] + '/self-check'
        question = user.get(path).json()
        assert question['available'] is True
        assert 'answer' not in question
        assert other.get(path).status_code == 404
        result = user.post(path, json={'choice':'inclusive'}).json()
        assert result['correct'] is False
        assert result['context'] == 'after-guidance'
        assert result['attribution'] == 'unconfirmed'
        assert user.post(path, json={'choice':'inclusive'}).json() == result
        assert user.post(path, json={'choice':'exclusive'}).status_code == 409
        assert user.get(path).json()['result'] == result
        again = diagnose(user)
        assert '自查未通过' in again['coaching']['next_action']
        assert again['coaching']['attribution'] == 'unconfirmed'
        assert user.post(path,json={'choice':'invented'}).status_code == 422
        assert other.post(path,json={'choice':'exclusive'}).status_code == 404


def test_probe_success_is_only_after_guidance_and_unknown_has_no_question():
    with TestClient(create_workbench()) as user:
        user.post('/api/session')
        d = diagnose(user)
        path = '/api/diagnoses/' + d['id'] + '/self-check'
        r = user.post(path,json={'choice':'exclusive'}).json()
        assert r['correct'] is True and r['context'] == 'after-guidance'
        assert '不能证明' in r['feedback']
        unknown = diagnose(user,'def f(x):\n    return x\n')
        path = '/api/diagnoses/' + unknown['id'] + '/self-check'
        assert user.get(path).json() == {'available':False}
        assert user.post(path,json={'choice':'exclusive'}).status_code == 409
