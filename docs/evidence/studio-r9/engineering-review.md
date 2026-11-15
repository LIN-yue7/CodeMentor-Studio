# R9 工程复核

复核范围为真实评测入口、持久预算、保存修改事件及试用记录导出。复核使用合成密钥和模拟传输，未产生付费请求。

- 真实评测入口固定官方 DeepSeek 主机、`deepseek-flash`、非思考模式及每次最多 2400 输出 token。模拟 307 响应只产生一次 HTTP 请求。账本先预留费用再调用，跨输出目录共享并验证已有账本。以官方高峰计费为参照，预留费率高于人民币每百万未命中输入 2 元及输出 8 元。[模型与价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/) · [请求字段](https://api-docs.deepseek.com/api/create-chat-completion/)
- 保存成功与修改事件在同一事务提交。测试核对后续代码修改生成事件，原样保存不增加事件。浏览器下载用例核对事件类型，并检查导出文件省略文件名和源码片段。
- 独立运行 `python -m pytest -q -o addopts="" tests/test_r9_live_budget.py tests/test_r9_trial_events.py`，8 项通过。复核范围内未发现仍需阻断单检出目录真实评测的缺陷。此记录不衡量服务可用性或模型输出质量。
