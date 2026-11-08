
"""Conservative evidence for small, named Python exercise patterns."""

import ast
from dataclasses import dataclass

from app.services.repo.parser import parse_source


@dataclass(frozen=True, slots=True)
class Rule:
    knowledge_id: str
    source: str
    location: tuple[int, ...]
    condition: str
    counterexample: str
    observed: str
    expected: str
    correction: str


RULES = (
    Rule("loop-boundary", "def total(xs):\n    result = 0\n    for i in range(len(xs) - 1):\n        result += xs[i]\n    return result\n",
         (1,), "任务要求遍历整数列表全部元素，但 range 上界排除了最后一个下标。",
         "[2, 3]", "2", "5", "使用 range(len(xs))，或直接遍历元素。"),
    Rule("empty-list", "def first(xs):\n    return xs[0]\n",
         (0,), "当任务允许空列表时，下标 0 不存在。此检查不推断业务默认值。",
         "[]", "IndexError", "走显式空列表分支", "先判断列表是否为空，按题意选择默认值或明确报错。"),
    Rule("accumulator", "def total(xs):\n    for x in xs:\n        result = 0\n        result += x\n    return result\n",
         (0, 0), "任务要求求和，但每轮循环都会重置累加器。",
         "[2, 3]", "3", "5", "将 result = 0 放在循环之前。"),
)


class NormalizeNames(ast.NodeTransformer):
    """Normalize only lexically bound local names. Keep builtins and literals intact."""

    def __init__(self, fn: ast.FunctionDef):
        names = [arg.arg for arg in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs]
        names.extend(node.id for node in ast.walk(fn)
                     if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store))
        self.names = {name: f"$local{index}" for index, name in enumerate(dict.fromkeys(names))}

    def visit_Name(self, node: ast.Name):
        node.id = self.names.get(node.id, node.id)
        return node

    def visit_arg(self, node: ast.arg):
        node.arg = self.names.get(node.arg, node.arg)
        return self.generic_visit(node)


def fingerprint(tree: ast.Module) -> str:
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        return ""
    fn = tree.body[0]
    if fn.args.vararg or fn.args.kwarg or fn.decorator_list:
        return ""
    fn.name = "$function"
    NormalizeNames(fn).visit(fn)
    return ast.dump(tree)


FINGERPRINTS = {fingerprint(ast.parse(rule.source)): rule for rule in RULES}


def analyze(code: str, language: str = "python") -> tuple[str, list[dict]]:
    if language != "python":
        parsed = parse_source(code.encode(), f"submission.{language}", language)
        if parsed.parse_error:
            return "syntax-error", [{"id": "syntax", "line": None, "condition": parsed.parse_error}]
        return "uncertain", []

    try:
        tree = ast.parse(code)
        # Compile to validate contextual syntax such as return outside a function.
        # The code object is discarded and is never executed.
        compile(tree, "submission.py", "exec")
        rule = FINGERPRINTS.get(fingerprint(tree))
    except SyntaxError as exc:
        return "syntax-error", [{"id": "syntax", "line": exc.lineno, "condition": exc.msg}]
    except (ValueError, RecursionError):
        return "uncertain", []
    if rule is None:
        return "uncertain", []

    node = tree.body[0]
    for index in rule.location:
        node = node.body[index]
    return "confirmed", [{
        "id": f"local:{rule.knowledge_id}", "knowledge_id": rule.knowledge_id, "line": node.lineno,
        "condition": rule.condition, "counterexample": rule.counterexample,
        "observed": rule.observed, "expected": rule.expected, "correction": rule.correction,
        "method": "reviewed-static-pattern",
    }]
