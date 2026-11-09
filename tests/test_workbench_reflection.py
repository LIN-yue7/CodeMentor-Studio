from fastapi.testclient import TestClient
from app.workbench import create_workbench
from tests.test_workbench_flow import diagnose


def test_reflection_is_self_reported_private_editable_and_used_next_time():
    app = create_workbench()
    with TestClient(app) as user, TestClient(app) as other:
        user.post('/api/session'); other.post('/api/session')
        result = diagnose(user)
        assert result['coaching']['attribution'] == 'unconfirmed'
        path = '/api/diagnoses/' + result['id'] + '/reflection'
        body = {'reason': 'typing', 'explanation': '知道不含上界，但多写了减一。'}
        assert other.post(path, json=body).status_code == 404
        assert user.post(path, json=body).status_code == 200
        assert user.post(path, json=body).status_code == 200
        memory = user.get('/api/learning-memory').json()['items']
        assert len(memory) == 1 and memory[0]['reflection']['reason'] == 'typing'
        assert other.get('/api/learning-memory').json()['items'] == []
        again = diagnose(user)
        assert again['coaching']['history']['self_reports']['typing'] == 1
        assert again['coaching']['attribution'] == 'unconfirmed'
        assert user.post(path, json={'reason':'concept','explanation':'修正自己的判断'}).status_code == 200
        assert user.get('/api/learning-memory').json()['items'][0]['reflection']['reason'] == 'concept'
        assert user.post(path + '/forget').status_code == 200
        assert user.get('/api/learning-memory').json()['items'] == []
        assert diagnose(user)['coaching']['history']['self_reports'] == {}


def test_reflection_validates_input():
    with TestClient(create_workbench()) as user:
        user.post('/api/session')
        result = diagnose(user)
        path = '/api/diagnoses/' + result['id'] + '/reflection'
        assert user.post(path, json={'reason':'stupid','explanation':''}).status_code == 422
        assert user.post(path, json={'reason':'unsure','explanation':'a'*601}).status_code == 422
