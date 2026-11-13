from app.services.project_verification import verify

def test_cross_file_failure_and_repair():
    files={'main.py':'import helper\nprint(helper.first([]) + 1)', 'helper.py':'def first(values):\n    if values:\n        return values[0]\n    return None'}
    result=verify(files,'main.py')
    assert result['status']=='runtime-error' and result['error']['path']=='main.py'
    assert any(t['path']=='helper.py' for t in result['trace'])
    files['helper.py']=files['helper.py'].replace('return None','return 0')
    result=verify(files,'main.py')
    assert result['status']=='passed' and result['stdout']=='1\n'

def test_interpreter_rejects_host_access_and_bounds_recursion():
    for code in ['open("secret.txt")','import os\nprint(os.environ)','while True: pass','def f():\n    return f()\nf()']:
        assert verify({'main.py':code},'main.py')['status']=='unsupported'

def test_nested_shared_output_is_bounded_before_expansion():
    code='a=[0]\n'+'a=[a,a]\n'*16+'print(a)'
    result=verify({'main.py':code},'main.py')
    assert result['status']=='unsupported' and len(result['stdout'])<=4000

def test_unsupported_bindings_and_context_syntax_never_pass():
    for code in ['def f():\n    break\nprint(1)', 'def f():\n    print(x)\n    x=1\nx=2\nf()', 'print=0\nprint(1)', 'def f(x: print(2)):\n    return x\nprint(1)']:
        assert verify({'main.py':code},'main.py')['status']!='passed'


def test_syntax_failure_has_navigable_source_location():
    result=verify({'main.py':'def f():\n    break'},'main.py')
    assert result['error']['path']=='main.py' and result['error']['line']==2
