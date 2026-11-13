import json, pathlib, subprocess
root=pathlib.Path('.')
e=root/'evaluation/studio-r8'
(e/'r7_project_retrieval.py').write_bytes(subprocess.check_output(['git','show','222d1bd:app/services/project_retrieval.py']))
cases=[]
def add(id,theme,files,path,line,relevant,request='',issues=None):
    cases.append(dict(id=id,theme=theme,provenance='authored synthetic fixture; not a user project',files=files,path=path,cursor_line=line,request=request,language='python',issues=issues or [],relevant_lines=[{'path':p,'line':n} for p,n in relevant],label_rationale='Required source statements for the named relationship; other nonblank returned lines count as excess context, not necessarily harmful.'))
for i,name in enumerate(['normalize','total','safe_divide'],1):
    main=f'def {name}(x):\n    return x + {i}\n'+'\n'*35+f'def run(x):\n    return {name}(x)\n'
    add(f'same-{i}','same-file function links',{'main.py':main},'main.py',39,[('main.py',1),('main.py',2),('main.py',39)])
for i,name in enumerate(['convert','price','format_value'],1):
    add(f'cross-{i}','cross-file function links',{'main.py':f'from helpers import {name}\nresult = {name}(3)\n','helpers.py':'# header\n'*30+f'def {name}(x):\n    return x + {i}\n'},'main.py',2,[('main.py',1),('main.py',2),('helpers.py',31),('helpers.py',32)])
for i,name in enumerate(['load','parse','fetch'],1):
    add(f'similar-{i}','similar names',{'main.py':f'from service import {name}\nresult = {name}(3)\n','service.py':f'def {name}(x):\n    return x\n\ndef {name}_all(x):\n    return []\n','noise.py':f'def {name}_backup(x):\n    return None\n'},'main.py',2,[('main.py',1),('main.py',2),('service.py',1),('service.py',2)])
for i,(statement,call) in enumerate([('from chosen import compute as selected','selected(3)'),('import chosen as selected','selected.compute(3)'),('from chosen import compute','compute(3)')],1):
    add(f'alias-{i}','duplicate symbols and aliases',{'main.py':statement+'\nvalue = '+call+'\n','chosen.py':'# header\n'*30+'def compute(x):\n    return x + 1\n','decoy.py':'def compute(x):\n    return x - 1\n'},'main.py',2,[('main.py',1),('main.py',2),('chosen.py',31),('chosen.py',32)])
for i,(path,stmt,target) in enumerate([('pkg/main.py','from .utils import compute','pkg/utils.py'),('pkg/sub/main.py','from ..utils import compute','pkg/utils.py'),('pkg/main.py','from . import utils','pkg/utils.py')],1):
    call='utils.compute(3)' if i==3 else 'compute(3)'
    add(f'relative-{i}','relative imports',{path:stmt+'\nvalue = '+call+'\n',target:'# header\n'*30+'def compute(x):\n    return x + 1\n','other/utils.py':'def compute(x):\n    return x - 1\n'},path,2,[(path,1),(path,2),(target,31),(target,32)])
for i,name in enumerate(['compute','calculate','increment'],1):
    add(f'docs-{i}','docs contradict source',{'main.py':f'from helpers import {name}\nvalue = {name}(3)\n','helpers.py':f'def {name}(x):\n    return x + 1\n','README.md':f'{name} returns its argument minus one.\n'},'main.py',2,[('main.py',1),('main.py',2),('helpers.py',1),('helpers.py',2),('README.md',1)],'Compare implementation with documented contract')
for i,name in enumerate(['compute','calculate','adjust'],1):
    add(f'broken-{i}','syntaxbroken related files',{'main.py':f'from helpers import {name}\nvalue = {name}(3)\n','helpers.py':'# header\n'*30+f'def {name}(x):\n    return x + 1\n\ndef broken(:\n    pass\n'},'main.py',2,[('main.py',1),('main.py',2),('helpers.py',31),('helpers.py',32)])
for i,name in enumerate(['compute','calculate','adjust'],1):
    files={'main.py':f'from helpers import {name}\nvalue = {name}(3)\n','helpers.py':f'def {name}(x):\n    return x + 1\n'}
    files.update({f'noise{j:02}.py':f'def {name}(x):\n    return {j}\n' for j in range(18)})
    add(f'noise-{i}','large unrelated context',files,'main.py',2,[('main.py',1),('main.py',2),('helpers.py',1),('helpers.py',2)])
(e/'retrieval-cases.json').write_text(json.dumps({'schema_version':1,'label_policy':'Synthetic, development-set labels authored before R8 implementation. Relevant line recall counts exact path+line. Excess context is every returned nonblank line outside labels. These labels do not measure model diagnosis quality.','cases':cases},ensure_ascii=False,indent=2),encoding='utf-8')
