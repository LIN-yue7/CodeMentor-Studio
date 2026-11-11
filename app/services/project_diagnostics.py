"""Parser-backed teaching notes, never execution or inferred learner traits."""
import ast
import re


def explain_syntax(path: str, code: str, exc: SyntaxError) -> dict:
    lines = code.splitlines()
    line = max(1, exc.lineno or 1)
    source = lines[line - 1] if line <= len(lines) else ''
    message = exc.msg
    concept = 'python-syntax'
    title = '这段代码不符合 Python 语法'
    why = 'Python 解析器无法把这些字符组成合法语句。标记位置是解析停止处，根因也可能位于上一行。'
    fix = '先对照标记行和上一行检查运算符、括号、引号以及语句是否完整；一次只修改一个问题。'
    example = ''
    prevention = '写完一个完整语句或代码块就复查；语法通过后再检查输入、输出与边界条件。'
    # Only classify language mismatch on the failing line, after Python rejects it.
    if re.match(r'\s*(?:typedef\b|#include\b|(?:int|void|double|float|char)\s+\w+\s*\(|(?:const\s+)?(?:let|var)\s+\w+\s*=)', source):
        concept, title = 'language-mismatch', '文件类型与代码语法可能不一致'
        why = '当前 .py 文件由 Python 解析；这一行具有 C / JavaScript 等语言的声明形式，Python 不接受这种写法。具体目标语言仍需你确认。'
        fix = '先确认目标语言。如果目标是 Python，按 Python 语法改写；如果目标是 C 等语言，应使用对应文件类型和工具链，改扩展名本身不能证明代码正确。'
        prevention = '新建文件时先确认语言与扩展名，再选择解析器；不要把不同语言的语法直接混写在一个 Python 模块中。'
    elif isinstance(exc, IndentationError):
        concept, title = 'python-indentation', '代码块的缩进不符合规则'
        why = 'Python 用缩进界定语句属于哪个代码块。同一层级应对齐，冒号后的代码块需要更深一级缩进；Tab 与空格混用也可能造成冲突。'
        fix = '检查报错行与所属的 def / if / for 等头部，使用一致的空格缩进；不要改变原本希望执行的分支归属。'
        example = 'if condition:\n    do_something()'
        prevention = '每次缩进前先判断这行属于哪个代码块。通常每层使用 4 个空格。'
    elif "expected ':'" in message:
        concept, title = 'python-suite', '代码块头部缺少冒号'
        why = '函数定义、条件和循环等复合语句用冒号结束头部，告诉 Python 下一段缩进代码属于这个代码块。缺少冒号时，解析器无法继续构造它。'
        fix = '在该代码块头部末尾补上冒号，并确认下一行使用正确缩进；保持原有参数和计算逻辑。'
        example = source.rstrip() + ':\n    # 在这里保留原有代码块'
        prevention = '写 def、if、for、while、class 等头部时，同时检查“冒号 + 缩进”这一对结构。'
    elif 'was never closed' in message or 'does not match' in message or 'unmatched' in message:
        concept, title = 'python-delimiter', '括号没有正确配对'
        why = '圆括号、方括号和花括号必须按类型和嵌套顺序配对。缺失或错配会让解析器无法确定表达式在哪里结束。'
        fix = '从标记的括号开始，按从内到外的顺序核对闭合位置；先确认表达式边界，再补对应括号。'
        prevention = '先写一对括号，再填写内容；复杂表达式分行时保留清晰的嵌套关系。'
    elif 'string literal' in message:
        concept, title = 'python-string', '字符串引号未正确结束'
        why = '字符串需要相互匹配的起止引号。普通单引号或双引号字符串不能直接跨物理行；内容中的同类引号需要转义。'
        fix = '确认文字的结束位置，补齐对应引号；需要多行文本时选择三引号或显式换行转义。'
        prevention = '区分包围字符串的引号和字符串内容中的引号，避免复制时混入弯引号。'
    elif 'outside' in message or 'not properly in loop' in message:
        concept, title = 'python-scope', '语句出现在不允许的作用域'
        why = 'return 必须位于函数体内；break / continue 必须位于相应循环中。语句本身可能完整，但放置位置违反了 Python 的上下文规则。'
        fix = '核对当前语句所属的函数或循环及其缩进。若确实处于模块顶层，应重新确认你想表达的是返回、输出还是终止循环。'
        prevention = '阅读缩进层级，先确定当前处于模块、函数还是循环，再选择控制流语句。'
    return {
        'path': path, 'line': line, 'column': max(1, exc.offset or 1),
        'end_line': exc.end_lineno, 'end_column': exc.end_offset,
        'message': message, 'title': title, 'why': why, 'fix': fix,
        'example': example, 'concept': concept, 'prevention': prevention,
        'intent': '仅凭语法错误无法确定业务意图；请结合函数目标和预期输入、输出确认修改方向。',
        'observed': '解析器已拒绝当前代码；程序未执行，因此没有真实运行输出。',
        'source': 'python-parser + reviewed-local-rule',
    }


def inspect_python(path: str, code: str) -> dict:
    if not path.endswith('.py'):
        return {'status':'unsupported','issues':[], 'summary':'此文件可编辑保存，暂未接入该语言的自动检查。'}
    try:
        tree = ast.parse(code)
        compile(tree, path, 'exec')  # Compile for contextual syntax validation; NEVER execute.
    except SyntaxError as exc:
        return {'status':'syntax-error', 'issues':[explain_syntax(path, code, exc)],
                'summary':'发现 Python 语法错误；不代表已检查全部逻辑。'}
    except (ValueError, RecursionError):
        return {'status':'uncertain','issues':[], 'summary':'代码结构无法安全解析，请缩小文件。'}
    return {'status':'syntax-ok','issues':[], 'summary':'Python 语法检查通过。业务逻辑、导入依赖和运行结果尚未验证。'}
