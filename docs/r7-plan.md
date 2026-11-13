# R7 实施计划

依据：用户本轮完整R7指令。继续876ac18，保护历史，不重写。

1. 导航与编辑：项目菜单和模态创建/导入/示例，文件树搜索、右键增删改、未保存/问题标记，多标签与语言更正；900px反馈抽屉，四视口。
2. 后端：真实项目检索、跨文件边界回归、持久化观察与提示事件、受限可验证示例闭环。不得执行任意用户代码。
3. 模型：记录安全错误种类、复现旧跨文件样例，真实模型重验；证据引用严格验证，失败可靠降级。自然深入解释与Diff审批。
4. 验收：新旧测试、四视口三轮真实截图和问题清单、非空双文件闭环、评分台账与完成清单、Git提交。

分工：navigation代理仅前端导航/Station/Editor/独立r7.css；backend代理仅Python API/模型表/项目检索与学习记录；主线程ProjectReview/StudioDiagnostics/模型服务、最终集成与浏览器。
共享接口：后端提供项目级GET /projects/{id}/learning（items事件含path/kind/concept/message）；POST /projects/{id}/learning-action（path,action为hint-viewed）；context增加project_issues字典，learning.items和related_files继续存在。模型review沿用bundle(payload,context)。
授权：用户另行批准本轮最多4次合成调用，已全部用完；无重试、每次最多2400输出token。
不得把固定流程说成自主Agent，不得把模拟回复说成真实模型，不宣称未实现功能完成。
