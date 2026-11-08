
# 架构与教学工作流

## 系统架构

```mermaid
flowchart LR
  Student["学生浏览器"] --> Workbench["React 工作台与 CodeMirror"]
  Workbench --> API["独立 FastAPI 工作台入口"]
  API --> Identity["签名会话与请求边界"]
  API --> Orchestrator["诊断编排"]
  Orchestrator --> Static["Python AST 与既有多语言解析器"]
  Orchestrator --> Corpus["受控知识点与版本化课程卡"]
  Orchestrator --> Model["可选模型解释与字段校验"]
  API --> Learning["变式选择与确定性评分"]
  Learning --> SQLite["SQLite 诊断、练习和作答记录"]
  Orchestrator --> SQLite
  Local["旧版单机入口"] --> Legacy["旧代码工具与学习报告"]
```

旧本地工具由单独应用启动。新版服务不挂载旧文件管理、旧身份接口或兼容接口。部署使用专用数据库。模型只收到标准示例、可信证据与尝试计数。学生代码不执行，原始提交也不发送给模型。

## 教学工作流

```mermaid
flowchart TD
  Submit["提交代码与题目要求"] --> Analyze["本地语法分析与模式匹配"]
  Analyze --> Verified{"有与题意匹配的静态反例"}
  Verified -- "否" --> Unsure["显示语法问题或证据不足"]
  Verified -- "是" --> Retrieve["检索本知识点的课程卡"]
  Retrieve --> Explain["可选模型解释并校验行号与引用"]
  Explain --> Select["选择尚未揭晓答案的版本化变式"]
  Select --> Attempt["记录提示级别并提交答案"]
  Attempt --> Grade{"确定性评分"}
  Grade -- "失败或提示后通过" --> Repeat["更换同知识点练习"]
  Grade -- "第一次独立通过" --> Transfer["不同题面复测"]
  Grade -- "两道不同题独立通过" --> VerifiedTwice["展示两份独立作答证据"]
```

分析事件只描述服务实际完成的步骤。诊断和作答采用不同的幂等键。作答更新和尝试记录共享同一事务。既有题目版本仍可判分，已看到答案的模板不会增加独立通过次数。
