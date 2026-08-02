# -*- coding: utf-8 -*-
"""生成福彩3D百十个杀码V9.3天花板研究报告PDF"""
from fpdf import FPDF
import os

pdf = FPDF(format='A4')
pdf.set_auto_page_break(auto=True, margin=18)

FONT = 'C:/Windows/Fonts/msyh.ttc'
pdf.add_font('msyh', '', FONT)
pdf.add_font('msyh', 'B', 'C:/Windows/Fonts/msyhbd.ttc')

pdf.add_page()

# 标题
pdf.set_font('msyh', 'B', 20)
pdf.set_text_color(26, 35, 126)
pdf.cell(0, 14, '福彩3D 百十个杀码系统 V9.3', ln=1, align='C')
pdf.set_font('msyh', '', 12)
pdf.set_text_color(80, 80, 80)
pdf.cell(0, 8, '天花板论证与完整研究报告', ln=1, align='C')
pdf.set_font('msyh', '', 9)
pdf.cell(0, 6, '报告日期: 2026-08-02  |  数据截止: 2026-08-02 (第2026204期, 累计8711期)', ln=1, align='C')
pdf.ln(4)
pdf.set_draw_color(26, 35, 126); pdf.set_line_width(0.8)
pdf.line(15, pdf.get_y(), 195, pdf.get_y())
pdf.ln(6)

def section(title):
    pdf.ln(3)
    pdf.set_font('msyh', 'B', 13)
    pdf.set_text_color(26, 35, 126)
    pdf.cell(0, 8, title, ln=1)
    pdf.set_draw_color(26, 35, 126); pdf.set_line_width(0.4)
    pdf.line(15, pdf.get_y(), 60, pdf.get_y())
    pdf.ln(2)

def para(text, size=10):
    pdf.set_font('msyh', '', size)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(0, 5.5, text)
    pdf.ln(1)

def bullet(text, size=10):
    pdf.set_font('msyh', '', size)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(0, 5.5, '  •  ' + text)
    pdf.ln(0.5)

def table(headers, rows):
    n = len(headers)
    w = 180 / n
    pdf.set_font('msyh', 'B', 9)
    pdf.set_fill_color(26, 35, 126); pdf.set_text_color(255, 255, 255)
    for h in headers:
        pdf.cell(w, 7, h, 1, 0, 'C', True)
    pdf.ln()
    pdf.set_font('msyh', '', 9)
    pdf.set_text_color(40, 40, 40)
    fill = False
    for r in rows:
        if fill:
            pdf.set_fill_color(240, 242, 248)
        for c in r:
            pdf.cell(w, 6.5, str(c), 1, 0, 'C', fill)
        pdf.ln()
        fill = not fill
    pdf.ln(2)

def bold_line(text):
    pdf.set_font('msyh', 'B', 10)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 6, text, ln=1)

# ── 一、系统概况 ──
section('一、系统概况')
para('【一句话定位】福彩3D百位/十位/个位，每位置输出2个杀码（共6杀），6杀全中为命中。基于上期开奖号(b,s,g)的非线性算术公式，纯数学计算，无任何外部依赖。')
bold_line('【版本演进】')
table(['版本', '技术', '关键成果'], [
    ['V1-V5', '统计法时代', '命中率天花板~95.17%(单杀), 已废弃'],
    ['V6', '公式法突破', '非线性算术公式(平方/乘积/条件分支)'],
    ['V7', '固定条件决策树', '百10条件/十3条件/个12条件+回退队列'],
    ['V8', '十位V8a增强', '2处结构性漏洞精确修复, 200期98.17%'],
    ['V9', '6杀制', '每位置+独立kill2, 6杀全中为命中'],
    ['V9.3', '三轮kill2穷举', '100期6杀全中 77%→87% (+10pp)'],
])
bold_line('【核心架构】')
bullet('kill1: 原V8三位置算法(条件决策树+自适应备份)')
bullet('kill2: 独立算术公式 百=(b-span+9)%10, 十=(s-mid+5)%10, 个=(g²+|b-g|)%10')
bullet('重叠处理: kill2==kill1时自动+1偏移; 回退队列避免同昨日杀码')

# ── 二、实测数据 ──
section('二、最新实测数据 (2026-08-02)')
bold_line('【多窗口回测 - 6杀全中率衰减曲线】')
table(['窗口', '6杀全中率', '3杀综合', '说明'], [
    ['100期', '87.0%', '97.7%', '当前窗口红利期'],
    ['200期', '82.5%', '98.3%', '近半年, 仍显著优于基线'],
    ['300期', '75.0%', '96.2%', '一年, 开始回落'],
    ['500期', '66.8%', '93.0%', '两年, 明显下滑'],
    ['1000期', '59.9%', '91.8%', '四年, 贴近基线'],
    ['2000期', '56.0%', '90.8%', '八年, 几乎贴基线'],
    ['全量8710', '53.19%', '90.36%', '收敛至随机基线!'],
])
bold_line('【全量8710期 - 天花板铁证】')
table(['指标', '实测', '随机基线', '超额'], [
    ['百位单杀', '90.59%', '90%', '+0.59pp'],
    ['十位单杀', '90.38%', '90%', '+0.38pp'],
    ['个位单杀', '90.11%', '90%', '+0.11pp'],
    ['百位kill2', '90.45%', '90%', '+0.45pp'],
    ['十位kill2', '90.26%', '90%', '+0.26pp'],
    ['个位kill2', '90.11%', '90%', '+0.11pp'],
    ['6杀全中', '53.19%', '53.1%', '+0.09pp'],
])
para('结论: 拉长到23年全量数据, 所有公式的超额收益全部收敛到0.1~0.6pp, 6杀全中超额仅0.09pp。公式法没有长期预测能力, 只有近期窗口适配。')

# ── 三、天花板论证 ──
section('三、为什么说这是天花板 (数学论证)')
bold_line('【1. 独立概率的理论上限】')
para('福彩3D每个位置开奖独立均匀分布于0-9。杀1个数: P(对)=0.9; 杀2个数: 每位置P=0.8, 三位置全对P=0.8³=51.2%。如果算法完全随机(无信息), 6杀全中率=51.2%。实测全量53.19%, 仅比随机高0.09pp ≈ 数学噪音。')
bold_line('【2. 信息量上限】')
para('公式法输入只有上期b,s,g三个数字(共1000种组合)。彩票本质是独立随机序列, 上期与下期没有任何因果关系(已用卡方检验/自相关验证, |ρ|≈0.03)。因此任何基于历史号码的公式, 信息增益理论上限≈0。')
bold_line('【3. 为什么近期能到87%?】')
para('87% ≈ 短期窗口内的适配红利。全历史167个滑动100期窗口, 6杀全中均值52.9%, 标准差6.4pp, P10=46%, P90=59%。当前87%是全历史最高值, 比均值高5.3个标准差(概率<10万分之1), 统计学上必然均值回归。')
bold_line('【4. 为什么再也无法提升?】')
bullet('公式池穷举: 298K线性公式池+二次项+条件组合, 最优方案200期92% vs V7 98% (反而更差)')
bullet('30+优化方法: 投票/加权/反共识/马尔可夫/自适应, 无一能在200期窗口超越当前公式')
bullet('任何恰好对历史拟合好的公式, 样本外窗口全部回落基线附近 (过拟合幸存者偏差)')
bullet('数学上限: 6杀全中 51.2%~53.1%, 已是贴着天花板')

# ── 四、衰减规律 ──
section('四、衰减规律与预测 (关键结论)')
bold_line('【6杀全中率随时间演化规律】')
bullet('全历史167个滑动100期窗口: 均值52.9%, 中位53%, 标准差6.4pp, 正常波动47%~59%')
bullet('历史高位段(>=65%)23年仅出现2次: 2008年66%, 2026年至今87%')
bullet('局部峰值回落到<55%耗时: 25~125期, 中位50~75期')
bold_line('【当前87%的回落预测】')
bullet('2~3个月(50~75期)内 大概率跌破70%')
bullet('3~5个月(100~150期)内 大概率回到55%附近')
bullet('最终稳定在 53%±6pp (47%~59%)')
bold_line('【升级策略建议】')
para('不建议定期升级(每次仅+1~5pp且依赖当前窗口)。建议触发式升级, 满足任一即重新穷举6个算法: ① 滚动100期6杀全中率跌破70%; ② 单月(30天)下滑超过8pp。系统已内置自动检测(每次cron自动判断, 触发时页面顶部红色横幅告警)。')

# ── 五、工程状态 ──
section('五、项目工程状态')
bullet('数据源: 灰鸟API(唯一真活源)+中彩网(备份,期号校验拦截)')
bullet('跨年bug: 已修复(next_issue_calc, 优先数据源next_code)')
bullet('三重cron: 北京22:00/23:30/01:00 (开奖后执行)')
bullet('升级触发器: 自动检测6杀跌破70%/月降8pp')
bullet('累计8711期 (2002-02-23 ~ 2026-08-02), 数据完整性审计通过')
bullet('本地vs云端公式一致性: 1000组随机输入0不一致; 反作弊审计通过')

# ── 六、免责 ──
section('六、免责声明')
para('本系统基于历史数据的统计研究, 所有结论均为概率性质。福彩3D是独立随机过程, 任何算法都无法预测开奖结果。历史回测不代表未来表现, 请理性参考, 勿沉迷投注。彩票投注有风险, 请量力而行。')
pdf.ln(4)
pdf.set_draw_color(26, 35, 126); pdf.line(15, pdf.get_y(), 195, pdf.get_y())
pdf.ln(3)
pdf.set_font('msyh', 'B', 10); pdf.set_text_color(26, 35, 126)
pdf.cell(0, 6, '— 报告完 —', ln=1, align='C')

out = 'D:/百十个/福彩3D百十个杀码V9.3天花板研究报告.pdf'
pdf.output(out)
print('PDF生成成功:', out, os.path.getsize(out), '字节')
