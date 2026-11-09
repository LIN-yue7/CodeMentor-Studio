
# CodeMentor AI 2.0 工作台

Python 入门实验面向三个错因。用户先指定函数的预期行为。工作台把代码与任务要求对照，显示可以推导的错误行、反例和修正依据。完成变式后，可看到提示后通过、独立通过和失败的不同反馈。达到两道不同题独立通过时，页面显示已有两条复测证据。

## 本机启动

使用 Python 3.12 和 Node.js 24。Windows 上从仓库根目录执行。先确认 python --version 显示 3.12。若系统默认版本不同，用 Python 3.12 可执行文件的完整路径替代第一条命令的 python。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
npm --prefix workbench-web ci
npm --prefix workbench-web run build
powershell -ExecutionPolicy Bypass -File tools/start_workbench.ps1 -Python .\.venv\Scripts\python.exe
```

打开 `http://127.0.0.1:8765/`。默认使用本地证据模式，不需要模型密钥。非 Windows 环境可在仓库根目录运行 `python -m uvicorn app.workbench:app --host 127.0.0.1 --port 8765 --limit-concurrency 32`。旧版入口仍为 `app.main:app`，单机功能和运行方式见根 README 的旧版章节。

工作台默认使用项目的 SQLite 数据库，增加 `cm_diagnoses`、`cm_challenges`、`cm_attempts`，启动时创建缺失表。迁移不会重写旧表。代码提交仅保存指纹、证据和结果。匿名浏览器会话默认在重启后失效。要跨重启复用同一浏览器会话，在服务进程环境设置随机的 `CODEMENTOR_SESSION_SECRET`，至少 32 字符。Cookie 有效期七天。可以用 `DATABASE__SQLITE_PATH` 指定专用评审数据库。

## 模型开关

DeepSeek 接入请先读 [分步操作与验收标准](deepseek-online.md)，使用 config/deepseek.env.example 最小模板。旧多模型表会影响默认模型解析，避免与单模型配置混用。

用经授权的兼容服务配置本机 .env 中的 `LLM__BASE_URL`、`LLM__MODEL`、`LLM__API_KEY`。配置模型与真正启用是两个步骤。启动脚本加 `-Live` 才开启真实模型，其他平台可在启动前设置 `CODEMENTOR_AI_MODE=live`。仅发送课程标准例子、可信静态证据和学习次数。工作台不会把用户源码或注释发送给模型端点。评审只提交合成样例。

模型成功且响应通过校验时，界面显示“模型解释”。如果未配置、限额、超时或校验失败，仍能使用本地证据、知识卡和练习。开发测试用注入模拟模型，页面能区分模拟模式。当前模型集成由服务端在调用前执行课程检索。只读课程检索与课程证据标注已接通，模型原生 Function Calling 和文本流式输出不在当前版本证据范围内。工作步骤是服务端完成后返回的记录。取消停止浏览器等待，诊断请求 ID 可用于安全重试。

在单进程下，真实模型调用默认每天总量 60 次、每会话每天 12 次、同时最多 3 个。可通过 `CODEMENTOR_AI_DAILY_LIMIT` 调整总量。日界线为 UTC，计数随进程重启清空。部署时以供应商硬配额为成本上限。配置方式和限额见 `app/services/workbench_tutor.py`。

## 快速演示

1. 保持默认循环边界样例和“返回全部整数元素的和”，点击“开始诊断”。
2. 点“第 3 行”，确认编辑器定位到 range。展开课程卡，核对反例 [2, 3] 的推导值 2 和预期值 5。
3. 展开一条提示并输入 6，看到“提示后通过”和复练推荐。
4. 重新挑战，填入 7，看到“独立通过”和下一道不同题面的推荐。继续完成第三题，查看两份独立证据。
5. 在另一浏览器会话或无痕窗口直接独立答对首题，对照不同的教学动作。再试空列表、累加状态或移除题目要求观察不确定状态。

## 验证与评测

```powershell
.\.venv\Scripts\python.exe -m pytest -o addopts="" -q -rs
node tools/check_frontend_logic.mjs
npm --prefix workbench-web run build
$env:CODEMENTOR_TEST_PYTHON=(Resolve-Path .\.venv\Scripts\python.exe).Path
npm --prefix workbench-web run test:e2e
.\.venv\Scripts\python.exe -m tools.evaluate_workbench
```

浏览器测试默认使用 Microsoft Edge，可设置 `PLAYWRIGHT_CHANNEL=chrome` 改用 Chrome。用例分别覆盖桌面和移动视口。测试服务使用隔离 SQLite 并强制本地模式。

真实模型评测须授权服务和预算，使用合成样例。可先做一条 A/B/C 冒烟（匹配样例至多触发三个模型请求，评测命令会关闭自动重试）：

```powershell
.\.venv\Scripts\python.exe -m tools.evaluate_workbench --live --limit 1 --max-provider-calls 3 --output evaluation/live-smoke.json
```

正式全量真实评测包含 24 次 A 调用与 12 次 B、12 次 C 调用。指定 --max-provider-calls 48 后才可启动全量真实评测。方法、离线结果与可解释边界见 `evaluation/README.md`。

## 部署边界

评审可从源码本机复现。若后续获准公开，入口只启动 `app.workbench:app`。需要 HTTPS、受控反向代理和 Host 配置、可信转发头、限流及真实服务预算。用全新评审数据库和固定的服务端会话密钥。先验证部署环境下的 Cookie、跨会话访问、429、延迟和模型服务降级，再决定是否公开。旧入口允许本地文件管理，只在本机使用。
