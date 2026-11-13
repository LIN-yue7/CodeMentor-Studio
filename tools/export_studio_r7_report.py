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

CODE='9f53dcd'
p('CodeMentor Studio','title');p('项目感知型实时编程学习工作台','h')
p('R7 阶段技术报告 | 2026-11-13 | 产品代码 '+CODE)
p('继承 R6 的真实工程，重构项目导航，连接检索、可审阅建议与实际复查。报告包含失败记录与未完成能力，不作为已冻结的正式参赛终稿。')
story.append(Image(str(ROOT/'docs/evidence/studio-r7/round-3/1440-feedback.png'),width=495,height=309))
p('图1：1440×900真实浏览器。左侧文件树、中央编辑器、右侧问题/原因/修改，底部教学区。非生成式示意图。','small')
p('本轮模型授权4次已用完；3次有效、1次格式失败。没有把测试中的模拟模型当成真实调用。')
page('1. 产品变化与实际范围')
for s in [
'左侧默认220px：项目名称菜单收纳打开、新建、导入和设置；创建使用弹窗，无常驻表单。文件树支持搜索、折叠、未保存与问题标记、文件及目录子树操作。无项目时有四个真实入口。',
'编辑器支持多文件标签、自动/Python/纯文本模式；更正语言时不重建编辑器选择。窄窗口切换面板，优先保留代码宽度。桌面支持面板折叠及反馈宽度、底部高度调整。',
'右侧统一为实时代码反馈。确定的解析错误直接解释哪里、为什么、怎样改；模型解释可通过自然语言操作调整深度。底部保留问题、易错点、代码解析、学习记录。',
'模型补丁包含源文件、行号、修改前后及理由。服务端逐字核对原行，前端展示Diff，明确批准后写入草稿；代码变化使旧结果失效。批准不代表补丁已经验证正确。',
'长期使用仍有边界：匿名身份7天，固定会话密钥未设置时重启无法自动恢复归属；可用JSON导入导出。逐文件撤销栈、空目录持久化、触屏操作和完整焦点管理尚待完善。']:p(s)
page('2. 分析、检索与执行边界')
for s in [
'高频本地层：650ms防抖后对当前未保存缓冲区做Python语法检查；返回中文根因和源位置。文件变化/切换清除旧证据。语法通过不等于逻辑或运行通过。',
'低频模型层：项目外发授权后，预览并手动发送；自动分析需单独开启，稳定1800ms后触发且最少间隔30秒。版本去重、取消、超时和失败暂停保留。',
'项目检索：解析导入、符号定义与文档词项；有界排序并输出候选理由和逐行原文。有效导入可从有语法错误的文件中恢复。当前是词法/结构检索，不是向量检索，也没有召回率和消融结论。',
'受限解释器：真实执行项目内导入、简单函数、条件、返回、列表索引、数值加减和print。无eval/exec或宿主IO；限制步骤、深度、值大小、输出展开。compile仅做语法验证。未实现的名称绑定、注解和其他语法明确拒绝。',
'真实学习事件：解析器观察、保存版本间语法复查、查看易错点、受限执行。事件所有者隔离并去重；不能由此推断掌握程度。个性化长期策略仍未完成。',
'安全边界：项目所有者、外发许可、敏感内容拦截、引用与补丁校验。秘密检测不穷尽，取消等待不能保证上游停止计费。当前为确定性工作流，不是自主Agent或Function Calling。']:p(s)
page('3. 真实模型实验与失败复盘')
table([['调用','条件与结果','证据'],['1','R6服务逻辑，同一错误代码/新问题；accepted 3875ms','live-01-baseline.json'],['2','R7检索、错误版；accepted 4906ms，给出return0补丁','live-02-retrieval.json'],['3','修复版；failed / invalid-output 4445ms','live-03-fixed.json'],['4','协议修复后真实浏览器；accepted，认为无需再改','live-04-browser/result.json']],[45,285,165])
story.append(Spacer(1,16))
for s in ['第3次响应包含6条真实引用，但旧schema最多5条，提示词没有明确数量。真实失败原文形成回归：修复前失败，提示词和schema统一为1–12条后通过；逐字引用校验未放松。第4次实际模型调用再次通过。',
'R6原失败仅保存failed，缺少原始输出，不能认定与本轮同因。第1次用相同代码和新的明确需求，属于近似复现。所有成功与失败原文保留；4个小样本不证明准确率、稳定性或教学效果。',
'真实错误版解释指出：helper空列表分支返回None，main将返回值加1，形成跨文件数值约定冲突；建议仅在空列表按0的需求下改return0。模型明确说明静态推断尚未执行。',
'修复版在真实浏览器完成模型分析，并独立运行受限解释器输出1。模型实测分次完成；演示需标注已录制真实结果，不假装一次连续现场调用。']:p(s)
page('4. 可重复教学闭环与验收')
story.append(Image(str(ROOT/'docs/evidence/studio-r7/round-3/1440-verified.png'),width=495,height=309))
p('图2：修改后在实际前端执行main.py，输出1。仅证明当前受支持子集及输入，不是完整项目测试通过。','small')
p('体验示例 → helper去掉冒号 → 自动错误定位和根因 → 恢复冒号 → main运行出现None+1 → helper改为return0 → main再运行输出1 → 学习记录更新。四个视口重复执行。')
table([['验证','最终结果与限制'],['后端','929通过，2项Windows符号链接相关跳过，82.35s'],['前端/浏览器','TypeScript/Vite生产构建通过；真实Edge64项通过，45.1s'],['视觉','三轮，1440×900、1366×768、900×700、390×844，非空项目和错误/修复截图'],['性能','8次本机输入到可见诊断666–686ms；p50=674、p95=686ms，含650ms防抖，非线上SLA']],[95,400])
rows=[]
for line in (ROOT/'docs/studio-score-matrix.md').read_text(encoding='utf-8-sig').splitlines():
 if line.startswith('|'):
  cells=[x.strip() for x in line.strip('|').split('|')]
  if len(cells)==5 and cells[1].isdigit():rows.append(cells)
assert sum(int(r[1]) for r in rows)==100
for label,subset in [('5. 评分覆盖：AI与创新',rows[:9]),('6. 评分覆盖：工程与应用',rows[9:])]:
 page(label);p('依据用户提供《奇笑.docx》100分细则。列出功能证据，不预测得分或奖项。')
 table([['项目/分值','当前证据','状态与不足']]+[[r[0]+' / '+r[1],r[2],r[3]] for r in subset],[90,220,185])
page('7. 审查修复、未完成事项与复现')
for s in ['独立审查发现并修复：嵌套共享列表输出在限长前膨胀；设置迟到响应覆盖新草稿；部分Python上下文和名称绑定被误判通过。相应回归通过；拒绝超出支持的语义，不冒充完整CPython。',
'浏览器曾出现2个移动端输入失败。trace表明contenteditable fill追加了新代码，导致测试内容不同于预期。换用编辑器真实键盘全选输入并断言内容，聚焦重复15项通过后再跑全量；失败日志仍保留。',
'未完成：自主Agent、真实Function Calling/MCP、多模态、自适应长期画像、独立项目检索召回评测、完整多语言运行与流式输出。没有真实学生试用、商业付费意愿或教学效果实证。',
'本机复现：安装requirements-lock.txt；npm --prefix workbench-web ci及build；启动app.workbench:app。默认本地模式，不调用外部模型。README包含PowerShell命令与会话边界。',
'本版产品代码'+CODE+'，材料为阶段稿。正式GitHub/Gitee仓库、5–8分钟1080p普通话MP4、参赛身份与复用归属审核、全历史秘密扫描和正式公网发布尚未完成。',
'继续按2026-11-18准备省赛交付，具体批次和截止时刻由个人中心/组委会确认。正式视频、报告和仓库需锁定同一冻结版本；本报告不提前承诺尚未实现功能。']:p(s)
def footer(c,doc):
 c.setFont('STSong-Light',8);c.setFillColor(colors.HexColor('#777387'));c.drawString(50,28,'CodeMentor Studio | R7阶段稿 | 代码'+CODE);c.drawRightString(545,28,str(doc.page))
output=ROOT.parent/'CodeMentor-Studio-R7-技术报告-阶段稿.pdf'
SimpleDocTemplate(str(output),pagesize=(595.28,841.89),rightMargin=50,leftMargin=50,topMargin=45,bottomMargin=45).build(story,onFirstPage=footer,onLaterPages=footer)
print(output)
