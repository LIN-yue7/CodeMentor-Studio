from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import json
ROOT=Path(__file__).resolve().parents[1]
pdfmetrics.registerFont(TTFont('STSong-Light', 'C:/Windows/Fonts/simsun.ttc', subfontIndex=0))
styles={
 'title':ParagraphStyle('title',fontName='STSong-Light',fontSize=28,leading=36,textColor=colors.HexColor('#262342'),spaceAfter=18),
 'h':ParagraphStyle('h',fontName='STSong-Light',fontSize=17,leading=25,textColor=colors.HexColor('#55417e'),spaceAfter=12),
 'p':ParagraphStyle('p',fontName='STSong-Light',fontSize=10.5,leading=17,spaceAfter=11,wordWrap='CJK'),
 'small':ParagraphStyle('small',fontName='STSong-Light',fontSize=8,leading=12,spaceAfter=5,wordWrap='CJK')}
story=[]
def p(s,kind='p'):story.append(Paragraph(escape(s),styles[kind]))
def title(s):p(s,'h')
def page(s):story.append(PageBreak());title(s)
def table(rows,widths):
 cells=[[Paragraph(escape(str(x)),styles['small']) for x in row] for row in rows]
 t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e9e4f2')),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#c9c7d4')),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
 story.append(t)
p('CodeMentor Studio','title');p('项目感知型实时编程学习工作台','h')
p('R6 阶段技术报告 | 2026-11-12 | 产品代码 846f0f0')
p('面向编程初学者和进阶学习者，在编写真实项目的过程中，提供可定位的错误证据、原因解释、修改方向和复查反馈。')
story.append(Image(str(ROOT/'docs/evidence/studio-r6/desktop-diagnosis-final.png'),width=495,height=309))
p('图1：1440×900真实浏览器截图。展示本地解析器证据，不是模型生成的界面。','small')
p('交付性质：阶段稿。完整自主Agent、项目RAG、Function Calling、多模态、长期项目学习画像与可审阅补丁尚未实现。不得作为已完成的参赛终稿提交。')
page('1. 需求与产品边界')
for s in ['核心任务是让学习者理解当前项目的问题，并自主完成修改，而不是仅收到一段替代代码。错误反馈回答位置、原因、可能意图、实际证据、修改方向和避免方式。','布局采用左侧文件树、中央专业编辑器、右侧实时诊断与底部教学区。中央代码占据主要空间；新建表单收纳；删除显式指导模式选择。桌面独立面板滚动，手机切换面板。','现有工程为React + TypeScript + Vite + CodeMirror，后端FastAPI + SQLite。迁移从4a0f016继承完整Git历史，未从零重写。保存、冲突检测、导出和旧教学实验继续复用。','当前支持1–30个文件、总内容50KB。Python进行静态语法检查；其他支持的文本文件仅编辑保存。没有项目代码执行环境，因此不能把语法通过解释为运行正确。'] :p(s)
table([['状态','能力'],['已实现','本地实时检查、中文诊断、授权模型审查、受控自动分析、引用校验、调整与折叠面板'],['部分实现','跨文件上下文、会话学习记录、真实模型稳定性、匿名项目持久化'],['尚未实现','项目RAG、自主工具选择、真实Function Calling、多模态、可审阅补丁、长期项目画像'],['未经充分验证','真实教学效果、低端设备/弱网表现、大样本模型准确性、正式公网可靠性']],[90,405])
page('2. 技术架构与实时分析机制')
for s in ['浏览器编辑缓冲区 -> 650ms防抖 -> 服务端所有者检查 -> Python AST解析与编译检查 -> 中文证据诊断 -> 用户修改 -> 自动复查。compile仅验证上下文语法，不执行代码。','项目授权默认关闭。授权后可手动预览并发送，也可单独开启本次自动分析。代码稳定1800ms后触发；两次调用至少间隔30秒，最近50个版本去重。变更或切文件撤销等待并丢弃迟到回复。','模型上下文优先纳入错误附近代码，并补充光标区域和最多两个直接引用文件。单行500字符、源码片段共6000字符。诊断元信息做投影，教学示例不会绕过源码预算。','模型输出校验JSON结构及逐字代码引用。引用成立只证明代码存在，不能证明语义推断正确。超时或失败暂停自动分析，用户可重新预览后手动重试。','安全边界包含项目所有者隔离、服务端外发许可、跨站防护、体积限制、常见秘密拦截、取消与失败兜底。检测不穷尽；撤销不能收回已发送内容，前端取消不能保证服务商停止计费。','当前流程由确定性程序编排，不宣称自主Agent。直接导入文件拼接不宣称为经过评测的RAG。'] :p(s)
page('3. 测试与真实模型证据')
table([['检查','结果及边界'],['后端回归','917通过，2项Windows符号链接相关测试跳过；83.79秒'],['浏览器回归','40通过，20.9秒；含桌面/手机、旧教学流程、权限和迟到回复'],['构建与截图','TypeScript/Vite构建通过；真实Edge截图，未捕获pageerror'],['本地响应','最终8次829/826/828/830/834/823/825/833ms；p50=828ms，p95=834ms，含650ms防抖；非线上SLA']],[100,395])
story.append(Spacer(1,16))
table([['真实模型案例','结果','耗时'],['缺冒号','accepted；根因与引用通过校验','3912ms'],['跨文件返回值约定','failed；当时未细分原因','4184ms'],['正确代码对照','accepted；仍有过多防御性建议','2872ms']],[190,220,85])
p('用户授权的3次合成测试，无自动重试、无现有私人项目输入。实测代码为a3fd465。后续边界修复与失败分类仅做离线验证，未追加付费调用。2次accepted不能换算为诊断准确率或教学效果。')
p('独立只读评审发现并修复了特殊目录名崩溃、长源码通过教学示例绕过预算的问题；补回归测试先失败再通过。另细化await的异步上下文解释。最后全量回归通过，未做第二轮独立评审。')
rows=[]
for line in (ROOT/'docs/studio-score-matrix.md').read_text(encoding='utf-8-sig').splitlines():
 if line.startswith('|'):
  cells=[x.strip() for x in line.strip('|').split('|')]
  if len(cells)==5 and cells[1].isdigit():rows.append(cells)
for label,subset in [('4. 评分覆盖：AI与创新',rows[:9]),('5. 评分覆盖：工程与应用',rows[9:])]:
 page(label);p('依据用户提供《奇笑.docx》，按100分换算。此表是覆盖证据，不是预计得分；完整台账见studio-score-matrix.md。')
 table([['评分项 / 分值','当前证据','不足与后续']]+[[r[0]+' / '+r[1],r[2],r[3]+'；'+r[4]] for r in subset],[88,190,217])
page('6. 运行、后续实施与提交准备')
for s in ['本机启动：创建.venv，安装requirements-lock.txt，npm --prefix workbench-web ci并build，再以tools/start_workbench.ps1启动app.workbench:app。默认本地模式，地址127.0.0.1:8780。详细命令见README。','匿名浏览器身份有效期7天；未配置固定会话密钥时重启会改变签名。当前必须导出备份，跨浏览器账号和导入恢复尚未完成。这是长期使用的重要缺口。','后续P0优先排查跨文件模型失败与正确代码过度建议；新增安全失败类型已经落地，但仍需要另行授权的真实样本验证。P1接入项目检索、真实工具选择、持久化学习事件和可审阅补丁；P2再引入与源码定位相关的多模态。','按2026-11-18准备省赛交付，具体批次和截止时刻以个人中心/组委会为准。《奇笑.docx》中对最终提交批次及国赛奖项比例存在需核对表述，不能据此推算获奖概率。','正式托管仓库及访问权限、原项目复用归属、团队信息、全历史秘密扫描尚未完成。现有本地origin仅为交接目录。公网发布须另行确认。','已编写约6分30秒的普通话演示脚本。正式MP4尚未录制；要求5–8分钟、1080p及以上。视频、PDF和仓库必须对应同一最终代码版本。','本报告为阶段稿，未验证的技术、商业与教学成效均不能作为已实现成果。当前材料为进一步开发和参赛内审提供依据。']:p(s)

def footer(c,doc):
 c.setFont('STSong-Light',8);c.setFillColor(colors.HexColor('#777387'));c.drawString(50,28,'CodeMentor Studio | R6阶段稿 | 代码846f0f0');c.drawRightString(545,28,str(doc.page))
output=ROOT.parent/'CodeMentor-Studio-R6-技术报告-阶段稿.pdf'
SimpleDocTemplate(str(output),pagesize=(595.28,841.89),rightMargin=50,leftMargin=50,topMargin=45,bottomMargin=45).build(story,onFirstPage=footer,onLaterPages=footer)
print(output)
