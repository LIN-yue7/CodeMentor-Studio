# 最终复验中的环境中断

2026-11-14 的 Python 3.13 完整复验中断于环境问题，未计为通过。直接导入 app.workbench 的 15 秒 faulthandler 跟踪停在 platform._wmi_query，由 SQLAlchemy 的 platform.machine() 引发；Windows Get-CimInstance 同期不返回。Python 3.12 也依赖该查询。没有修改 Windows 服务，也没有在产品中替换 Python 标准库。改用平台查询能正常返回 AMD64 的 Python 3.11.9，在新的虚拟环境安装 requirements-lock.txt。

浏览器复跑第一次未选定虚拟环境，系统 Python 缺少 uvicorn，见 browser-freeze-check.log；随后默认高并发触发 Node 内存分配失败，见 browser-freeze-recheck.log。残留的本轮测试服务造成一次端口占用，见 browser-final-bounded.log，清理本轮测试进程后重新运行。降低并发为 2，Python 3.11 的最终 72 个浏览器测试通过，见 browser-python311-final.log。这些失败均未删除或替换为成功统计。

backend-freeze-check.log 和 backend-python311-final.log 是未结束的尝试，不能引用为完整通过。最终后端使用逐例日志和 faulthandler 超时栈，见 backend-python311-traced.log。安装记录为 python311-install.log。
