"""Bounded lexical/structural retrieval over virtual files; no execution or embeddings."""
import ast
import io
import re
import tokenize


def _nodes(code):
    try:
        return list(ast.walk(ast.parse(code)))
    except (SyntaxError, ValueError, RecursionError):
        # Parse complete logical statements separately: a later syntax error must
        # not discard a valid import, including parenthesized multi-line imports.
        nodes, statement = [], []
        try:
            for token in tokenize.generate_tokens(io.StringIO(code).readline):
                if token.type in (tokenize.INDENT, tokenize.DEDENT):
                    continue
                statement.append(token)
                if token.type == tokenize.NEWLINE:
                    source = tokenize.untokenize([(t.type, t.string) for t in statement]).strip()
                    if source.startswith(('import ', 'from ')):
                        try:
                            parsed = ast.parse(source)
                            ast.increment_lineno(parsed, statement[0].start[0] - 1)
                            nodes.extend(ast.walk(parsed))
                        except (SyntaxError, ValueError):
                            pass
                    statement = []
        except (tokenize.TokenError, IndentationError, SyntaxError):
            pass
        return nodes


def _module_paths(module, files):
    stem = module.replace('.', '/')
    return [p for p in (stem + '.py', stem + '/__init__.py') if p in files]


def retrieve_project(files, path, cursor_line=1, request='', language='auto', issues=None,
                     max_chars=6000, max_candidates=12):
    """Return ranked ranges and exact line snippets. Scores are heuristics, not confidence."""
    code = files[path]
    python = language == 'python' or (language == 'auto' and path.endswith('.py'))
    nodes = _nodes(code) if python else []
    identifiers = set(re.findall(r'\b[A-Za-z_]\w*\b', code + '\n' + request))
    calls = set(re.findall(r'\b([A-Za-z_]\w*)\s*\(', code)) if python else set()
    imports = {}
    for node in nodes:
        if isinstance(node, ast.Import):
            for alias in node.names:
                for target in _module_paths(alias.name, files):
                    imports.setdefault(target, set()).add(alias.name.rsplit('.', 1)[-1])
        elif isinstance(node, ast.ImportFrom):
            parts = path.split('/')[:-1]
            if node.level:
                if node.level > len(parts):
                    continue
                base = parts[:len(parts) - node.level + 1]
                module = '.'.join(base + ([node.module] if node.module else []))
            else:
                module = node.module or ''
            for target in _module_paths(module, files):
                imports.setdefault(target, set()).update(a.name for a in node.names)
            for alias in node.names:
                for target in _module_paths('.'.join(filter(None, [module, alias.name])), files):
                    imports.setdefault(target, set()).add(alias.name)
    candidates = []
    for target, content in sorted(files.items()):
        if target == path:
            continue
        lines = content.splitlines()
        if not lines:
            continue
        target_nodes = _nodes(content) if target.endswith('.py') else []
        symbols = [(n.name, n.lineno, min(getattr(n, 'end_lineno', n.lineno) or n.lineno, n.lineno + 15))
                   for n in target_nodes if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        matched = [(name, start, end) for name, start, end in symbols
                   if name in identifiers or name in imports.get(target, set())]
        if target in imports:
            if matched:
                for name, start, end in matched:
                    candidates.append({'path':target,'start_line':start,'end_line':end,
                                       'score':100 + (30 if name in calls else 0),
                                       'reasons':['项目内导入定位', f'符号定义：{name}']})
            else:
                candidates.append({'path':target,'start_line':1,'end_line':min(16,len(lines)),
                                   'score':80,'reasons':['项目内导入定位；未确定具体定义']})
        elif target.endswith(('.md', '.txt')):
            terms = (calls | set().union(*imports.values()) if imports else calls)
            terms |= set(re.findall(r'\b[A-Za-z_]\w{2,}\b', request))
            hits = [(i, set(re.findall(r'\b[A-Za-z_]\w*\b', line)) & terms) for i,line in enumerate(lines)]
            for i, overlap in hits:
                if overlap:
                    candidates.append({'path':target,'start_line':max(1,i),'end_line':min(len(lines),i+4),
                                       'score':40 + min(20,len(overlap)*5),
                                       'reasons':['文档词项匹配：' + ', '.join(sorted(overlap))]})
        else:
            for name, start, end in matched:
                if name in calls:
                    candidates.append({'path':target,'start_line':start,'end_line':end,
                                       'score':55,'reasons':[f'调用名与定义匹配：{name}；绑定关系未确认']})
    candidates.sort(key=lambda c: (-c['score'], c['path'], c['start_line']))
    candidates = candidates[:max(0,min(20,max_candidates))]
    snippets, seen, remaining = [], set(), min(6000,max(0,max_chars))
    def add(target, start, end):
        nonlocal remaining
        lines = files[target].splitlines()
        for index in range(max(0,start-1),min(len(lines),end)):
            if (target,index) in seen:
                continue
            text = lines[index]
            if len(text)>500 or len(text)>remaining or len(snippets)>=160:
                continue
            seen.add((target,index))
            snippets.append({'path':target,'line':index+1,'quote':text})
            remaining -= len(text)
    # Exact parser-marked lines have precedence over cursor windows and retrieval.
    for issue in issues or []:
        if issue.get('line'):
            add(path, issue['line'], issue['line'])
            add(path, issue['line']-3, issue['line']+3)
    add(path,cursor_line-7,cursor_line+16)
    for candidate in candidates:
        add(candidate['path'],candidate['start_line'],candidate['end_line'])
    return {'method':'local-import-symbol-lexical-ranking','candidates':candidates,
            'snippets':snippets,'related_files':list(dict.fromkeys(c['path'] for c in candidates)),
            'limits':{'characters':6000,'line_characters':500,'candidates':20},
            'boundary':'静态检索候选与逐行原文；未执行代码，也不证明调用绑定或业务逻辑正确。'}
