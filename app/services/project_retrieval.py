"""Bounded static source retrieval; no code execution or probabilistic confidence."""
import ast
import io
import re
import tokenize

_DEFINITION = re.compile(r'^(?:async\s+)?(?:def|class)\s+([A-Za-z_]\w*)', re.M)


def source_coverage(files, snippets, paths=None):
    sent = {}
    for row in snippets:
        sent.setdefault(row['path'], set()).add(row['line'])
    coverage = {}
    for path in sent if paths is None else paths:
        lines = files[path].splitlines()
        coverage[path] = {
            'total_lines': len(lines),
            'complete': all(
                number in sent.get(path, ()) for number, line in enumerate(lines, 1)
                if line.strip()
            ),
        }
    return coverage


def _nodes(code):
    try:
        return list(ast.walk(ast.parse(code)))
    except (SyntaxError, ValueError, RecursionError):
        # Recover imports independently so a later syntax error does not erase them.
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
        # Parse isolated top-level definitions. A broken later block must not
        # hide an earlier valid helper. Never repair or synthesize source text.
        boundaries = list(_DEFINITION.finditer(code))
        for i, match in enumerate(boundaries):
            end = boundaries[i + 1].start() if i + 1 < len(boundaries) else len(code)
            try:
                parsed = ast.parse(code[match.start():end])
                ast.increment_lineno(parsed, code.count('\n', 0, match.start()))
                nodes.extend(ast.walk(parsed))
            except (SyntaxError, ValueError, RecursionError):
                pass
        return nodes


def _module_paths(module, files):
    stem = module.replace('.', '/')
    return [p for p in (stem + '.py', stem + '/__init__.py') if p in files]


def _bindings(nodes, path, files):
    """Map local import names to virtual module paths and original symbol names."""
    bindings = {}
    for node in nodes:
        if isinstance(node, ast.Import):
            for alias in node.names:
                for target in _module_paths(alias.name, files):
                    bindings[alias.asname or alias.name] = (target, None)
        elif isinstance(node, ast.ImportFrom):
            parts = path.split('/')[:-1]
            if node.level:
                if node.level > len(parts):
                    continue
                base = parts[:len(parts) - node.level + 1]
                module = '.'.join(base + ([node.module] if node.module else []))
            else:
                module = node.module or ''
            for alias in node.names:
                if alias.name == '*':
                    continue  # Wildcard binding is not established by this resolver.
                children = _module_paths('.'.join(filter(None, [module, alias.name])), files)
                targets = children or _module_paths(module, files)
                for target in targets:
                    bindings[alias.asname or alias.name] = (target, None if children else alias.name)
    return bindings


def _call_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _call_name(node.value)
        return base + '.' + node.attr if base else ''
    return ''


def retrieve_project(files, path, cursor_line=1, request='', language='auto', issues=None,
                     max_chars=6000, max_candidates=12):
    """Return exact source lines; ranks express static evidence, not correctness."""
    code = files[path]
    python = language == 'python' or (language == 'auto' and path.endswith('.py'))
    indexes = {}
    for target, content in files.items():
        indexes[target] = _nodes(content) if target.endswith('.py') or (target == path and python) else []
    nodes = indexes[path] if python else []
    definitions = {
        target: [n for n in ns if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        for target, ns in indexes.items()
    }
    # Restrict names to the enclosing function/class, rather than every unrelated
    # function in the file. The cursor window remains useful for top-level code.
    enclosing = [n for n in definitions[path]
                 if n.lineno <= cursor_line <= (n.end_lineno or n.lineno)]
    if enclosing:
        scope = min(enclosing, key=lambda n: (n.end_lineno or n.lineno) - n.lineno)
        focus_nodes = list(ast.walk(scope))
        focus = '\n'.join(code.splitlines()[scope.lineno - 1:scope.end_lineno])
    else:
        start, end = max(1, cursor_line - 7), cursor_line + 16
        focus_nodes = [n for n in nodes if start <= getattr(n, 'lineno', 0) <= end]
        focus = '\n'.join(code.splitlines()[start - 1:end])
    names = {n.id for n in focus_nodes if isinstance(n, ast.Name)}
    request_names = set(re.findall(r'\b[A-Za-z_]\w*\b', request))
    calls = {_call_name(n.func) for n in focus_nodes if isinstance(n, ast.Call)} - {''}
    if python and not names and not calls:
        # Syntax-broken focus: lexical candidates remain explicitly tentative.
        calls = set(re.findall(r'\b([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*\(', focus))
        names = set(re.findall(r'\b[A-Za-z_]\w*\b', focus))
    bindings = _bindings(nodes, path, files)
    candidates = []
    candidate_keys = set()

    def candidate(target, start, end, score, reason):
        key = (target, start, end)
        if key not in candidate_keys:
            candidate_keys.add(key)
            candidates.append({'path': target, 'start_line': start, 'end_line': end,
                               'score': score, 'reasons': [reason]})

    def symbol(target, name, score, reason):
        matched = [n for n in definitions[target] if n.name == name]
        for node in matched:
            candidate(target, node.lineno, min(node.end_lineno or node.lineno, node.lineno + 39),
                      score, reason + f'；符号定义：{name}')
        return matched

    resolved = set()
    terms = set(request_names)
    for bound, (target, original) in bindings.items():
        used_calls = [call for call in calls if call == bound or call.startswith(bound + '.')]
        if not used_calls and bound not in names and bound not in request_names:
            continue
        resolved.update(used_calls)
        wanted = {original} if original else {call[len(bound) + 1:].split('.')[0]
                                              for call in used_calls if call.startswith(bound + '.')}
        terms.update(wanted)
        found = False
        for name in sorted(wanted):
            found = bool(symbol(target, name, 130, '项目内显式导入绑定')) or found
        if not found:
            candidate(target, 1, min(16, len(files[target].splitlines())), 90,
                      '项目内导入定位；未确定具体定义，需核对动态绑定或语法')
    # Follow same-file helper links for at most two hops; no dynamic call inference.
    pending = {call for call in calls if '.' not in call and call not in resolved} | request_names
    for _ in range(2):
        following = set()
        for name in sorted(pending):
            found = symbol(path, name, 120, '同文件静态调用名匹配；需核对运行时绑定')
            if found:
                resolved.add(name)
                terms.add(name)
                for node in found:
                    following.update(_call_name(n.func) for n in ast.walk(node) if isinstance(n, ast.Call))
        pending = following - resolved
    # Unbound same-name definitions are weaker evidence; suppress duplicate-symbol
    # decoys once an explicit import or same-file definition explains the call.
    unbound = {call for call in calls if '.' not in call and call not in resolved}
    terms.update(unbound)
    for target in sorted(files):
        if target != path and target.endswith('.py'):
            for name in sorted(unbound):
                symbol(target, name, 55, '调用名与定义匹配；绑定关系未确认')
        elif target.endswith(('.md', '.txt')) and target != path:
            for i, line in enumerate(files[target].splitlines(), 1):
                overlap = set(re.findall(r'\b[A-Za-z_]\w*\b', line)) & terms
                if overlap:
                    candidate(target, max(1, i - 1), min(len(files[target].splitlines()), i + 2),
                              40 + min(20, len(overlap) * 5),
                              '文档词项匹配（文档可能与实现不一致）：' + ', '.join(sorted(overlap)))
    candidates.sort(key=lambda c: (-c['score'], c['path'], c['start_line']))
    candidates = candidates[:max(0, min(20, max_candidates))]
    snippets, seen, remaining = [], set(), min(6000, max(0, max_chars))

    def add(target, start, end):
        nonlocal remaining
        lines = files[target].splitlines()
        for index in range(max(0, start - 1), min(len(lines), end)):
            if (target, index) in seen:
                continue
            text = lines[index]
            if len(text) > 500 or len(text) > remaining or len(snippets) >= 160:
                continue
            seen.add((target, index))
            snippets.append({'path': target, 'line': index + 1, 'quote': text})
            remaining -= len(text)

    for issue in issues or []:
        if issue.get('line'):
            add(path, issue['line'], issue['line'])
            add(path, issue['line'] - 3, issue['line'] + 3)
    add(path, cursor_line - 7, cursor_line + 16)
    for item in candidates:
        add(item['path'], item['start_line'], item['end_line'])
    return {'method': 'local-scope-import-symbol-lexical-ranking', 'candidates': candidates,
            'snippets': snippets,
            'related_files': list(dict.fromkeys(c['path'] for c in candidates if c['path'] != path)),
            'limits': {'characters': 6000, 'line_characters': 500, 'candidates': 20},
            'boundary': '静态检索候选与逐行原文；未执行代码，也不证明调用绑定或业务逻辑正确。'}
