"""Bounded local evidence for model guidance and proposed line replacements."""
import ast
import re

from app.services.project_verification import Machine, Unsupported, verify


def _name(node):
    return node.id if isinstance(node, ast.Name) else None


def _literal(node, expected):
    return isinstance(node, ast.Constant) and type(node.value) is type(expected) and (
        node.value == expected
    )


def teaching_fact(snapshot, data):
    """Recognize only simple, complete top-level function shapes in sent source."""
    path = snapshot['path']
    if not path.endswith('.py') or snapshot.get('language') == 'text':
        return None
    if not data.get('source_coverage', {}).get(path, {}).get('complete'):
        return None
    try:
        tree = ast.parse(snapshot['files'][path])
        compile(tree, path, 'exec')
    except (SyntaxError, ValueError, RecursionError):
        return None
    cursor = snapshot.get('cursor_line', 1)
    for fn in tree.body:
        if not isinstance(fn, ast.FunctionDef) or not fn.lineno <= cursor <= fn.end_lineno:
            continue
        args = fn.args
        if (fn.decorator_list or len(args.args) != 1 or args.defaults or args.posonlyargs
                or args.kwonlyargs or args.vararg or args.kwarg or getattr(fn, 'type_params', [])):
            return None
        arg = args.args[0].arg
        doc = ast.get_docstring(fn)
        body = fn.body[1:] if doc is not None else fn.body
        if (len(tree.body) == 1 and len(body) == 2 and isinstance(body[0], ast.Assign)
                and len(body[0].targets) == 1 and _name(body[0].targets[0]) == 'sum'
                and isinstance(body[0].value, ast.Constant)
                and type(body[0].value.value) is int
                and body[0].lineno == body[0].end_lineno < body[1].lineno
                and isinstance(body[1], ast.Return) and isinstance(body[1].value, ast.Call)):
            call = body[1].value
            if (_name(call.func) == 'sum' and len(call.args) == 1 and _name(call.args[0]) == arg
                    and not call.keywords and arg != 'sum' and fn.name != 'sum'
                    and fn.returns is None and args.args[0].annotation is None):
                return 'shadowed-sum', fn, arg, body
        if len(body) == 3 and isinstance(body[0], ast.Assign) and isinstance(body[1], ast.For):
            setup, loop, end = body
            accumulator = _name(setup.targets[0]) if len(setup.targets) == 1 else None
            item = _name(loop.target)
            if (accumulator and item and len({accumulator, arg, item}) == 3
                    and _literal(setup.value, 0) and _name(loop.iter) == arg
                    and not loop.orelse and len(loop.body) == 1
                    and isinstance(loop.body[0], ast.AugAssign)
                    and _name(loop.body[0].target) == accumulator
                    and isinstance(loop.body[0].op, ast.Add) and _name(loop.body[0].value) == item
                    and isinstance(end, ast.Return) and _name(end.value) == accumulator):
                return 'integer-accumulator', fn, arg, body
        # Only a simple integer predicate and an explicit boolean-return contract.
        if len(body) == 1 and isinstance(body[0], ast.If):
            branch = body[0]
            condition = branch.test
            if (not branch.orelse and len(branch.body) == 1
                    and isinstance(branch.body[0], ast.Return)
                    and _literal(branch.body[0].value, True)
                    and isinstance(condition, ast.Compare) and _name(condition.left) == arg
                    and len(condition.ops) == 1 and isinstance(condition.ops[0], ast.Gt)
                    and _literal(condition.comparators[0], 0)
                    and (_name(fn.returns) == 'bool'
                         or (doc and re.match(r'return (?:a )?bool(?:ean)?\b', doc, re.I)))):
                return 'implicit-none', fn, arg, body
    return None


def local_teaching(fact, request=""):
    """Build explanatory text from a recognized AST rule, including its limits."""
    kind, fn, arg, body = fact
    name = fn.name
    if kind == 'shadowed-sum':
        summary = f'第 {body[0].lineno} 行的局部变量 sum 遮蔽了内置求和函数。'
        root = f'第 {body[1].lineno} 行的 sum({arg}) 试图调用整数，会引发 TypeError。'
        mechanism = '函数内赋值让同名标识符成为局部变量，后面的调用使用该局部绑定。'
        example = f'静态推断：{name}([1, 2]) 会在调用局部整数时抛出 TypeError。'
        hint = f'若目标是求和，删除遮蔽赋值并保留 sum({arg})。也可以逐项累加后返回。'
        prevention = f'用 {name}([]) 和 {name}([1, 2]) 核对求和预期 0 和 3。'
        uncertainty = '输入元素类型和空输入的业务约定仍需结合调用方确认。'
    elif kind == 'integer-accumulator':
        accumulator = _name(body[0].targets[0])
        item = _name(body[1].target)
        summary = f'{accumulator} 在循环前已初始化为整数 0。'
        root = f'当前循环逐项执行 {accumulator} += {item}，累加器的作用域与初始化没有发现问题。'
        mechanism = ('整数起始值可以和常见数值相加。'
                     '若第一个元素是字符串，0 与字符串相加会引发 TypeError。')
        example = (f'静态推断：{name}([1, 2]) 得到 3，{name}([]) 得到 0，'
                   f'{name}(["a"]) 引发 TypeError。')
        hint = '如果调用方约定传入数值，保留当前累加方式。只有需求明确接受其他类型时才需要调整。'
        prevention = '用普通数值列表和空列表核对调用约定。'
        uncertainty = '允许的元素类型取决于调用方约定。'
    else:
        summary = f'{name} 在 {arg} <= 0 时会隐式返回 None。'
        root = f'第 {body[0].lineno} 行的条件为假时，控制流直接到达函数末尾，违背布尔返回约定。'
        mechanism = 'Python 函数走到末尾时会隐式返回 None。文档和类型标注不会替函数补上返回值。'
        example = f'静态推断：{name}(0) 和 {name}(-1) 返回 None，{name}(1) 返回 True。'
        hint = f'若约定为判断正数，在分支后显式返回 False，也可直接返回 {arg} > 0。'
        prevention = '用负数、0、正数测试三个输入，并检查结果是否为 True 或 False。'
        uncertainty = '非正数应映射到哪个布尔值仍由需求决定。'
    if kind == 'integer-accumulator' and re.search(r'复杂度|complexity|O\(', request, re.I):
        mechanism += (' 在数值序列和单次数值加法按常数成本计算的模型下，'
                      '遍历 n 个元素耗时 O(n)，累加器与循环变量占 O(1) 个辅助变量。'
                      'Python 大整数的位数增长会增加运算与存储成本；自定义迭代器和运算符需另行分析。')
    return {
        'explanation': f'{summary}{root}{mechanism}',
        'hints': [hint, prevention],
        'teaching': {
            'summary': summary, 'root_cause': root, 'mechanism': mechanism, 'example': example,
            'alternatives': [], 'prevention': prevention, 'uncertainty': uncertainty,
        },
    }


def _apply(files, patches):
    candidate = dict(files)
    for patch in sorted(patches, key=lambda item: item.line, reverse=True):
        lines = candidate[patch.path].split('\n')
        index = patch.line - 1
        if index >= len(lines) or lines[index] != patch.before:
            raise ValueError('patch line does not match editor source')
        lines[index] = patch.after
        candidate[patch.path] = '\n'.join(lines)
    return candidate


def _valid_python(path, code):
    try:
        compile(ast.parse(code), path, 'exec')
    except SyntaxError:
        return False
    except (ValueError, RecursionError):
        return None
    return True


def _sample_function(files, path, name, values):
    machine = Machine(files)
    try:
        scope = machine.module(path[:-3].replace('/', '.'))
        call = ast.Call(func=ast.Name(id=name), args=[
            ast.List(elts=[ast.Constant(value=value) for value in values])
        ], keywords=[])
        value = machine.expr(call, scope, path)
    except (Unsupported, SyntaxError, TypeError, ValueError, IndexError, KeyError, RecursionError):
        return None
    if type(value) in (int, float, bool, str):
        return (type(value), value)
    if value is None:
        return (type(None), None)
    return None


def _inline_literal_return(files, path, name):
    """Resolve a straight-line local literal returned by a simple function.

    The execution subset deliberately rejects local rebinding. Reduce only
    this one proven assignment/return pattern before sampling the function.
    """
    code = files[path]
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError):
        return files
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        return files
    fn = tree.body[0]
    body = fn.body[1:] if ast.get_docstring(fn) is not None else fn.body
    if (fn.name != name or len(body) != 2 or not isinstance(body[0], ast.Assign)
            or not isinstance(body[1], ast.Return)):
        return files
    assignment, returned = body
    if (len(assignment.targets) != 1 or _name(assignment.targets[0]) is None
            or _name(assignment.targets[0]) != _name(returned.value)
            or not isinstance(assignment.value, ast.Constant)):
        return files
    fn.body[-2:] = [ast.Return(value=assignment.value)]
    return {**files, path: ast.unparse(tree)}


def _preservation_check(files, candidate, changed, patches):
    """Check narrowly recognized numeric behavior without executing unsupported syntax."""
    for path in changed:
        try:
            original = ast.parse(files[path])
            updated = ast.parse(candidate[path])
        except (SyntaxError, ValueError, RecursionError):
            continue
        updated_functions = {node.name: node for node in updated.body if isinstance(node, ast.FunctionDef)}
        for fn in original.body:
            if not isinstance(fn, ast.FunctionDef):
                continue
            if not any(patch.path == path and fn.lineno <= patch.line <= fn.end_lineno for patch in patches):
                continue
            if sum(isinstance(node, ast.FunctionDef) and node.name == fn.name for node in updated.body) > 1:
                return {'status': 'withheld', 'reason': 'preservation-unconfirmed'}
            fact = teaching_fact({'files': files, 'path': path, 'cursor_line': fn.lineno},
                                 {'source_coverage': {path: {'complete': True}}})
            if not fact or fact[0] not in {'integer-accumulator', 'implicit-none'}:
                continue
            replacement = updated_functions.get(fn.name)
            if replacement is None or ast.dump(fn.args) != ast.dump(replacement.args):
                return {'status': 'withheld', 'reason': 'preservation-unconfirmed'}
            body = replacement.body[1:] if ast.get_docstring(replacement) is not None else replacement.body
            old_body = fact[3]
            if fact[0] == 'implicit-none':
                if not body or not isinstance(body[0], ast.If):
                    return {'status': 'withheld', 'reason': 'preservation-unconfirmed'}
                branch = body[0]
                if ast.dump(branch.test) != ast.dump(old_body[0].test):
                    return {'status': 'withheld', 'reason': 'preservation-unconfirmed'}
                if ([ast.dump(node) for node in branch.body]
                        != [ast.dump(node) for node in old_body[0].body]):
                    reason = 'preservation-unconfirmed'
                    if (len(branch.body) == 1 and isinstance(branch.body[0], ast.Return)
                            and _literal(branch.body[0].value, False)):
                        reason = 'existing-branch-regression'
                    return {'status': 'withheld', 'reason': reason}
            elif (len(body) == 3 and ast.dump(body[0]) == ast.dump(old_body[0])
                  and ast.dump(body[1]) == ast.dump(old_body[1])
                  and isinstance(body[2], ast.Return) and isinstance(body[2].value, ast.Constant)
                  and type(body[2].value.value) in (int, float)):
                samples = []
                for values in ([], [2, 3], [-4, 2]):
                    expected, actual = sum(values), body[2].value.value
                    samples.append({'input': values, 'reference': expected, 'candidate': actual})
                    if expected != actual:
                        return {'status': 'withheld', 'reason': 'accumulator-regression',
                                'samples': samples, 'evidence_kind': 'static-numeric-reference'}
            elif ast.dump(replacement) != ast.dump(fn):
                return {'status': 'withheld', 'reason': 'preservation-unconfirmed'}
    return None


def _terminates(body):
    """Recognize unconditional return/raise paths; no general control-flow proof."""
    for node in body:
        if isinstance(node, (ast.Return, ast.Raise)):
            return True
        if isinstance(node, ast.If) and _terminates(node.body) and _terminates(node.orelse):
            return True
    return False


def _fills_return_contract(files, candidate, changed, patches):
    # A previously missing return can be an intentional None sentinel. Making
    # one arithmetic caller succeed cannot establish the desired default value.
    for path in changed:
        try:
            original, updated = ast.parse(files[path]), ast.parse(candidate[path])
        except (SyntaxError, ValueError, RecursionError):
            continue
        functions = {node.name: node for node in updated.body if isinstance(node, ast.FunctionDef)}
        for fn in original.body:
            if not isinstance(fn, ast.FunctionDef) or _terminates(fn.body):
                continue
            replacement = functions.get(fn.name)
            if (replacement is not None and _terminates(replacement.body)
                    and any(p.path == path and fn.lineno <= p.line <= fn.end_lineno for p in patches)):
                return True
    return False


def check_patch(snapshot, patches, fact):
    """Screen contradictions and compare bounded observations; never prove equivalence."""
    def result(status, reason, **evidence):
        return {'status': status, 'reason': reason, **evidence}

    if not snapshot:
        return result('unknown', 'missing-snapshot')
    files, entry = snapshot['files'], snapshot['path']
    try:
        candidate = _apply(files, patches)
    except (KeyError, ValueError):
        return result('withheld', 'editor-line-mismatch')
    changed = {patch.path for patch in patches}
    if (snapshot.get('language') == 'text' and entry in changed) or any(
        not path.endswith('.py') for path in changed
    ):
        return result('unknown', 'unsupported')
    for path in changed:
        parsed = _valid_python(path, candidate[path])
        if parsed is False:
            return result('withheld', 'candidate-syntax-error')
        if parsed is None:
            return result('unknown', 'unsupported')
    preservation = _preservation_check(files, candidate, changed, patches)
    if preservation:
        return preservation
    if _fills_return_contract(files, candidate, changed, patches):
        return result('unknown', 'return-contract-unconfirmed')
    if fact and fact[0] == 'shadowed-sum' and entry in changed:
        _, fn, _, body = fact
        # The direct call to the name sum in the original code supplies the
        # reference. Restore that lookup by removing the integer assignment.
        lines = files[entry].split('\n')
        lines[body[0].lineno - 1] = ''
        reference = {**files, entry: '\n'.join(lines)}
        probe_candidate = _inline_literal_return(candidate, entry, fn.name)
        comparisons = []
        for values in ([], [2, 3], [-4, 2]):
            expected = _sample_function(reference, entry, fn.name, values)
            actual = _sample_function(probe_candidate, entry, fn.name, values)
            if expected is None or actual is None:
                return result('unknown', 'unsupported')
            comparisons.append({'input': values, 'reference': expected[1], 'candidate': actual[1]})
            if expected != actual:
                return result('withheld', 'reference-mismatch', samples=comparisons)
        # These calls cover a sample of the inferred sum behavior only. If
        # another file also changed, continue to compare the entry's behavior.
        if changed == {entry}:
            return result('sampled', 'sum-reference-samples', samples=comparisons)
    before, after = verify(files, entry), verify(candidate, entry)
    states = {'before': before['status'], 'after': after['status']}
    if 'unsupported' in states.values():
        return result('unknown', 'unsupported', **states)
    if after['status'] == 'runtime-error':
        before_error, after_error = before['error'], after['error']
        if before['status'] == 'passed' or (
            before_error['path'], before_error['message']
        ) != (after_error['path'], after_error['message']):
            return result('withheld', 'new-runtime-error', **states)
        return result('review-required', 'existing-runtime-error', **states)
    if before['status'] == 'runtime-error':
        return result('review-required', 'observed-error-removed', **states)
    if before['stdout'] != after['stdout']:
        return result('review-required', 'output-changed', **states)
    observed_lines = {(item['path'], item['line']) for item in before['trace']}
    if not before['stdout'] or any((patch.path, patch.line) not in observed_lines for patch in patches):
        return result('unknown', 'no-observed-output', **states)
    return result('sampled', 'same-observed-output', **states)
