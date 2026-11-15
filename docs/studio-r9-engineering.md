# R9 工程来源与发布检查

2026-11-13从00db306创建studio-r9，完整继承本地48个提交。保留根LICENSE中的原作者zhaoyiang与MIT许可。新增代码作为本项目增量，比赛原创归属及团队申报由参赛人确认。

## 源码与依赖

Python精确版本锁定见requirements-lock.txt，前端见workbench-web/package-lock.json。审计清单位于docs/evidence/studio-r9/python-dependencies.json和node-dependencies.json。Node锁文件90个条目均有许可证元数据，涵盖MIT、Apache-2.0、ISC、BSD-3-Clause及MPL-2.0。Python环境另含开发工具pip/ruff，应以requirements-lock.txt为安装范围。

MPL-2.0依赖包含certifi及前端锁中的相关包，分发时保留其许可证与适用的源码义务。MIT/BSD/Apache依赖的版权声明随依赖安装保留。源码包不打包node_modules和.venv。许可证检查是工程资料核对，参赛资格与复用声明仍需团队签署确认。

## 历史扫描

扫描所有本地refs可达的883个Git blob、48个提交。45条模式命中已核对为代码变量传递、空配置示例或带测试标记的伪凭据，详见history-audit.json。未命中私钥头或SQLite数据库签名。扫描未覆盖不可达对象或用户私密工作文件，模式匹配无法证明所有形式的隐私均不存在。

.gitignore补充数据库、旁路日志、密钥文件及work目录。公开包从Git提交导出，排除.env、数据库、依赖环境和私密配置。发布前需再次扫描最终提交及确认外部仓库可见性。

## 安装与身份

本机全新Python虚拟环境按锁文件安装成功，独立前端目录npm ci成功；记录见clean-install.log与clean-npm-install.log。这是同一台机器的独立环境复现，第二台机器尚待团队核验。

首次安装运行tools/prepare_studio.ps1，生成私有稳定会话签名并构建前端。后续双击Start-Studio.cmd即可本地启动。签名变化会影响旧浏览器身份，已有.env由安装脚本保留。浏览器身份有效期仍为7天，定期导出项目JSON。

正式GitHub/Gitee仓库尚待用户授权创建，评委访问验证需在发布后以未登录浏览器实际检查。当前origin为本地交接目录。

新环境启动与进程重启后项目恢复已验证，证据见clean-start-recovery-recheck.log。首次检查受本机HTTP代理干扰，日志保留于clean-start-recovery.log，检查脚本显式直连本机后通过。Python元数据未填License字段的aiosqlite与tree-sitter已核对发行包LICENSE为MIT，colorama发行包为BSD许可。

2026-11-15使用Python 3.11.9重新创建独立虚拟环境，锁定依赖安装成功，最终完整后端1022通过、2跳过及浏览器72通过。Python 3.12/3.13的WMI阻塞、浏览器高并发内存中断及重试过程单独保留于environment-incidents.md。Windows演示推荐已验证的3.11环境与浏览器测试workers=2。

最终源码另行复制到干净目录，实际执行prepare_studio.ps1安装Python/前端并构建；通过Start-Studio.cmd本地启动，双文件项目输出7，保存后重启服务，同一浏览器会话恢复文件和修订成功。无模型请求。证据为release-clean-prepare.log与release-startup-recovery.json。最终候选709个文件的扫描未发现禁止分发路径；20个模式命中均与已审历史代码、示例或伪凭据一致，见candidate-audit.json。
