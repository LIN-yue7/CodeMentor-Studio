"""Keep actual rejected provider output as a regression, without paid requests."""
import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from app.services.project_review import SYSTEM, validate_review


def test_complete_source_is_distinguished_from_partial_snippets():
    from app.services.project_review import bundle
    from app.api.workbench_projects import ReviewInput
    payload=ReviewInput(files={'main.py':'def f(x):\n    if x:\n        return True\n'},path='main.py',revision=0)
    snippets=[{'path':'main.py','line':i+1,'quote':s} for i,s in enumerate(payload.files['main.py'].splitlines())]
    context={'status':'syntax-ok','issues':[],'context':{'related_files':[]},'retrieval':{'snippets':snippets}}
    assert bundle(payload,context)['source_coverage']['main.py']['complete'] is True
    context['retrieval']['snippets']=snippets[:2]
    assert bundle(payload,context)['source_coverage']['main.py']['complete'] is False


def test_extra_plain_text_suggestions_are_grouped_without_losing_text():
    value={'explanation':'Evidence remains unverified','hints':['one','two','three','four'],
           'citations':[{'path':'main.py','line':1,'quote':'x = 1'}]}
    parsed,failure=validate_review(json.dumps(value),{'snippets':value['citations']})
    assert failure is None and parsed.hints==['one','two','three\n\nfour']
    value['citations'][0]['quote']='invented'
    assert validate_review(json.dumps(value),{'snippets':[{'path':'main.py','line':1,'quote':'x = 1'}]})[1]=='invalid-citation'
    value['hints']=[{'untrusted':'object'}]
    with pytest.raises(ValidationError):validate_review(json.dumps(value),{'snippets':[]})


def test_live_object_alternatives_remain_rejected_and_prompt_is_explicit():
    record = json.loads(Path('docs/evidence/studio-r8/live-pilot/request-002.json').read_text(encoding='utf-8'))
    data = json.loads(record['messages'][1]['content'])
    with pytest.raises(ValidationError):
        validate_review(record['content'], data)
    assert 'alternatives 必须是字符串数组' in SYSTEM
    # Normalizing only the observed schema deviation keeps exact citations intact.
    value = json.loads(record['content'])
    value['teaching']['alternatives'] = [str(item) for item in value['teaching']['alternatives']]
    accepted, failure = validate_review(json.dumps(value), data)
    assert accepted and failure is None
