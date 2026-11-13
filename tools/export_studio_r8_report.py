"""Export evidence-bounded R8 development report (requires reportlab)."""
from pathlib import Path
import subprocess
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Image,Table,TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
ROOT=Path(__file__).resolve().parents[1]
CODE=subprocess.check_output(['git','rev-parse','--short','HEAD'],cwd=ROOT,text=True).strip()
pdfmetrics.registerFont(TTFont('CN','C:/Windows/Fonts/simsun.ttc',subfontIndex=0))
styles={k:ParagraphStyle(k,fontName='CN',fontSize=size,leading=leading,wordWrap='CJK',spaceAfter=8,textColor=colors.HexColor('#272638')) for k,size,leading in [('title',25,34),('h',16,24),('p',10,16),('small',8,12)]}
story=[]
def p(text,kind='p'):return Paragraph(escape(text.replace('**','').replace('`','')),styles[kind])
def markdown(path):
    rows=[]
    def flush():
        if not rows:return
        n=len(rows[0]);widths=[495/n]*n
        if n==5:widths=[105,45,45,45,255] if '案例' in rows[0][0] else [80,30,170,130,85]
        t=Table([[p(c,'small') for c in row] for row in rows],colWidths=widths,repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8e4f0')),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#cbc8d4')),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]));story.append(t);story.append(Spacer(1,10));rows.clear()
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('|'):
            cells=[c.strip() for c in line.strip('|').split('|')]
            if not all(set(c)<=set('-: ') for c in cells):rows.append(cells)
            continue
        flush()
        if line.strip():story.append(p(line.lstrip('# '),'h' if line.startswith('#') else 'p'))
    flush()
story.extend([p('CodeMentor Studio','title'),p('R8 开发评测报告','h'),p('2026-11-13 | 代码 '+CODE+' | 非省赛冻结候选'),p('项目感知的实时编程学习工作台。保留R7布局，增加受控原生工具、证据绑定的分析流程、补丁撤回和真实评测。所有限制与失败均随报告公开。')])
story.append(Image(str(ROOT/'docs/evidence/studio-r8/release/1440-feedback.png'),width=495,height=309.375))
story.append(p('实际浏览器：双文件项目中的本地语法反馈。不是生成式设计图。','small'))
for source in ['docs/studio-r8-status.md','docs/evidence/studio-r8/evaluation-report.md','docs/studio-score-matrix.md']:
    story.append(PageBreak());markdown(ROOT/source)
story.append(PageBreak());story.append(p('实际运行与复查证据','h'))
story.append(Image(str(ROOT/'docs/evidence/studio-r8/release/1440-verified.png'),width=495,height=309.375))
story.append(p('受限解释器执行当前双文件输入，修复后输出1；只证明当前支持子集与输入，不等于完整项目测试通过。真实模型请求与浏览器验收分次进行。'))
story.append(p('复现：README的新工作台入口app.workbench:app；默认本地模式。源码含完整请求证据及失败案例，未包含本机密钥。正式GitHub/Gitee、5–8分钟1080p视频、资格与版权核查尚待完成。'))
def footer(c,doc):
    c.setFont('CN',8);c.setFillColor(colors.HexColor('#777387'));c.drawString(50,26,'CodeMentor Studio | R8开发评测稿 | '+CODE);c.drawRightString(545,26,str(doc.page))
out=ROOT.parent/'CodeMentor-Studio-R8-技术报告-开发评测稿.pdf'
SimpleDocTemplate(str(out),pagesize=(595.28,841.89),leftMargin=50,rightMargin=50,topMargin=45,bottomMargin=45).build(story,onFirstPage=footer,onLaterPages=footer)
print(out)
