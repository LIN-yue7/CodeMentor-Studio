# DeepSeek 在线接入（2026-11-09）

在线指后端调用真实模型，网页仍只运行在本机，不是公网部署。尚未发起真实付费调用。

## 1. 获取密钥

登录 DeepSeek 官方开放平台 https://platform.deepseek.com/ ，自行创建 API Key 并查看账户余额与计费。不要把密钥发到聊天、截图或提交到 Git。是否充值、充值金额由你决定。

官方当前说明使用 https://api.deepseek.com 和 deepseek-flash：
https://api-docs.deepseek.com/ （2026-11-09 核对）
思考模式默认开启：https://api-docs.deepseek.com/guides/thinking_mode/
本项目短解释请求显式设置 disabled；新增客户端配置已通过模拟 HTTP 请求体测试，但真实服务成功率和延迟尚未验证。

## 2. 本地配置

在本项目根目录打开 PowerShell。若没有 .env，执行：

```powershell
if (-not (Test-Path .env)) { Copy-Item config/deepseek.env.example .env }
notepad .env
```

在记事本里把 `LLM__API_KEY=` 补上自己的密钥并保存。其余内容见模板；不要在 PowerShell 命令行中输入密钥，避免留入命令历史。

如果已有 .env，先备份，再核对上述字段。旧模板含有 LLM__MODELS__... 多模型表和 LLM__DEFAULT_MODEL，实际客户端会优先解析默认模型。新工作台可使用最小单模型文件；不要混用旧多模型表。进程中同名环境变量可能覆盖 .env。配置后须重启服务。

## 3. 启动独立试用端口

当前 8765 保留离线预览。进入项目目录，使用本工作区现有虚拟环境：

```powershell
$env:CODEMENTOR_AI_DAILY_LIMIT='3'
powershell -ExecutionPolicy Bypass -File tools/start_workbench.ps1 -Python ../../work/venv/Scripts/python.exe -Port 8767 -Live
```

打开 http://127.0.0.1:8767/ 。保持这个窗口运行，Ctrl+C 停止。在独立复制的源码包中，先按 docs/workbench.md 安装依赖，Python 路径改成 .venv/Scripts/python.exe。

启动本身不调用模型。你点击默认循环边界样例的“开始诊断”才会尝试模型调用，可能产生费用。建议先只点击一次；不要运行全量评测。此处单进程调用额度为每天最多 3 次且关闭自动重试；失败也占额度，重启会清空，不能替代供应商硬预算。

不要在 .env 中设置 CODEMENTOR_AI_MODE / CODEMENTOR_AI_DAILY_LIMIT 来期待生效：这两个开关直接读取进程环境；上述脚本负责模式，PowerShell 环境变量负责额度。

现有离线预览使用专用数据库，而此命令使用项目配置的数据库。两边学习历史可能不同。跨重启保留浏览器身份需要固定 CODEMENTOR_SESSION_SECRET 进程环境（至少 32 字符），当前匿名会话不是永久账号。

## 4. 判断是否真正在线成功

选择审核样例（循环边界），点击开始诊断：
- 顶部在线模式仅表示开关已启用。
- 出现“模型解释”，且工作步骤的“模型解释”为“校验通过”，才代表这次实际返回并通过结构校验。
- 超时、失败、未配置或输出未通过校验都不是在线成功；本地证据和练习仍可继续。
- 未匹配的任意代码不会触发模型推断，也不是在线模式坏了。

真实模型目前只解释可信证据。发送课程标准代码、检索知识卡和学习次数，不发送用户原始源码/注释、复盘自由文本或密钥之外的个人资料；密钥仅用于向配置的服务鉴权。个人错因仍需自述和后续验证，接上模型不会自动变成已验证的认知诊断。

排错：未配置先查 LLM__API_KEY 是否为空；请求失败检查账户权限/余额/网络/端点/模型名；超时可先重试一次；结构校验失败保留失败记录，不当成成功。不要贴带 Authorization 的原始日志。

回到离线：停止 8767 服务即可继续使用 8765；或启动同一脚本不加 -Live。
