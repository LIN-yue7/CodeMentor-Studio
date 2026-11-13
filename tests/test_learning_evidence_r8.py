from app.services.project_learning import summarize_learning
from app.services.project_verification import verify

def test_profile_counts_observed_versions_without_claiming_mastery():
    assert summarize_learning([])['status']=='insufficient'
    errors=[{'kind':'syntax-error','path':'main.py','buffer_hash':str(i),'concept':'missing-colon'} for i in range(3)]
    hints=[{'kind':'hint-viewed','path':'main.py','buffer_hash':str(i)} for i in range(2)]
    profile=summarize_learning(errors+hints)
    assert profile['status']=='observed-pattern'
    assert profile['evidence'][0]['hint_viewed_versions']==2
    assert profile['evidence'][0]['saved_syntax_rechecks']==0

def test_actual_trace_contains_input_branch_and_return_values():
    result=verify({'main.py':'def first(values):\n    if values:\n        return values[0]\n    return 0\nprint(first([])+1)'},'main.py')
    assert result['status']=='passed' and result['stdout']=='1\n'
    assert any(e['event']=='call-parameters' and e['values']=={'values':[]} for e in result['trace'])
    assert any(e['event']=='condition' and e['value'] is False for e in result['trace'])
    assert any(e['event']=='return-value' and e['value']==0 for e in result['trace'])
