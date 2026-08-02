"""
生成自包含的前端HTML面板 — V9 100期6杀制
"""
import json

with open('D:/百十个/prediction_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

json_str = json.dumps(data, ensure_ascii=False)
stats = data['stats']

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>福彩3D 百十个杀码预测 V9</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, "Microsoft YaHei", "PingFang SC", sans-serif; background: #f5f7fa; color: #2c3e50; min-height:100vh; }}
.container {{ max-width: 1200px; margin:0 auto; padding:20px; }}
.header {{ text-align:center; padding:30px 0 20px; }}
.header h1 {{ font-size:28px; font-weight:700; color:#1a237e; letter-spacing:1px; }}
.header h1 span {{ display:inline-block; margin:0 4px; }}
.header .subtitle {{ font-size:13px; color:#78909c; margin-top:6px; }}
.pred-card {{ background: linear-gradient(135deg, #1a237e 0%, #283593 50%, #3949ab 100%); border-radius:16px; padding:30px; color:white; margin-bottom:24px; box-shadow: 0 8px 32px rgba(26,35,126,.25); position:relative; overflow:hidden; }}
.pred-card::before {{ content:''; position:absolute; top:-50%; right:-50%; width:200%; height:200%; background: radial-gradient(circle, rgba(255,255,255,.06) 0%, transparent 70%); animation: shimmer 3s infinite; }}
@keyframes shimmer {{ 0%,100% {{ transform:translate(0,0); }} 50% {{ transform:translate(10px,10px); }} }}
.pred-card .badge {{ display:inline-block; background:rgba(255,255,255,.18); border-radius:20px; padding:5px 16px; font-size:12px; margin-bottom:20px; letter-spacing:1px; position:relative; z-index:1; }}
.pred-card .issue {{ font-size:16px; font-weight:600; opacity:.9; margin-bottom:24px; position:relative; z-index:1; }}
.pred-card .positions {{ display:flex; gap:16px; justify-content:center; flex-wrap:wrap; position:relative; z-index:1; }}
.pred-card .pos {{ background:rgba(255,255,255,.12); backdrop-filter:blur(4px); border-radius:12px; padding:20px 28px; text-align:center; min-width:140px; border:1px solid rgba(255,255,255,.15); transition:transform .2s; }}
.pred-card .pos:hover {{ transform:translateY(-3px); }}
.pred-card .pos-label {{ font-size:13px; opacity:.75; margin-bottom:8px; }}
.pred-card .pos-num {{ font-size:48px; font-weight:800; line-height:1; text-shadow: 0 2px 8px rgba(0,0,0,.2); }}
.pred-card .pos-sub {{ font-size:11px; opacity:.6; margin-top:6px; }}
.section-title {{ font-size:18px; font-weight:700; color:#1a237e; margin:28px 0 16px; padding-bottom:8px; border-bottom:2px solid #e8eaf6; display:flex; align-items:center; gap:8px; }}
.section-title .dot {{ width:8px; height:8px; border-radius:50%; background:#3949ab; }}
.stats-row {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(180px,1fr)); gap:16px; margin-bottom:24px; }}
.stat-card {{ background:white; border-radius:12px; padding:20px; box-shadow:0 2px 8px rgba(0,0,0,.06); text-align:center; border-top:3px solid transparent; }}
.stat-card.h {{ border-top-color:#4caf50; }}
.stat-card.t {{ border-top-color:#2196f3; }}
.stat-card.o {{ border-top-color:#ff9800; }}
.stat-card.a6 {{ border-top-color:#e94560; }}
.stat-card .stat-label {{ font-size:13px; color:#78909c; margin-bottom:8px; }}
.stat-card .stat-val {{ font-size:32px; font-weight:800; }}
.stat-card .stat-detail {{ font-size:12px; color:#90a4ae; margin-top:4px; }}
.stat-card.h .stat-val {{ color:#2e7d32; }}
.stat-card.t .stat-val {{ color:#1565c0; }}
.stat-card.o .stat-val {{ color:#e65100; }}
.stat-card.a6 .stat-val {{ color:#e94560; }}
.table-wrap {{ background:white; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,.06); overflow:hidden; margin-bottom:24px; }}
.table-scroll {{ max-height:600px; overflow-y:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:12px; }}
thead {{ position:sticky; top:0; z-index:2; }}
th {{ background:#1a237e; color:white; padding:10px 6px; font-weight:600; font-size:11px; text-align:center; white-space:nowrap; }}
td {{ padding:6px; text-align:center; border-bottom:1px solid #f0f0f0; }}
tr:hover td {{ background:#f5f7ff; }}
tr.row-fail {{ background:#fff3f0; }}
tr.row-fail:hover td {{ background:#ffe8e0; }}
.cell-ok {{ color:#2e7d32; font-weight:600; }}
.cell-fail {{ color:#c62828; font-weight:700; }}
.cell-kill {{ font-weight:600; }}
.cell-actual {{ font-weight:500; }}
.summary-row td {{ background:#fafafa; font-size:12px; color:#78909c; border-top:2px solid #e0e0e0; }}
.info-card {{ background:white; border-radius:12px; padding:24px; box-shadow:0 2px 8px rgba(0,0,0,.06); margin-bottom:24px; line-height:1.8; }}
.info-card h3 {{ color:#1a237e; font-size:15px; margin-bottom:8px; }}
.info-card p {{ font-size:13px; color:#546e7a; margin-bottom:6px; }}
.info-card code {{ background:#e8eaf6; padding:2px 6px; border-radius:4px; font-size:12px; color:#3949ab; }}
.info-card .warn {{ background:#fff3e0; border-left:3px solid #ff9800; padding:10px 14px; border-radius:0 8px 8px 0; margin-top:12px; font-size:12px; color:#e65100; }}
.legend {{ display:flex; gap:16px; margin-bottom:12px; font-size:12px; color:#78909c; }}
.legend-item {{ display:flex; align-items:center; gap:4px; }}
.legend-dot {{ width:10px; height:10px; border-radius:3px; }}
.legend-dot.ok {{ background:#c8e6c9; border:1px solid #66bb6a; }}
.legend-dot.fail {{ background:#ffcdd2; border:1px solid #ef5350; }}
.disclaimer {{ text-align:center; padding:20px; font-size:11px; color:#b0bec5; border-top:1px solid #eceff1; margin-top:20px; }}
@media (max-width: 768px) {{
  .pred-card .positions {{ flex-direction:column; align-items:center; }}
  .stats-row {{ grid-template-columns:1fr; }}
  .pred-card .pos-num {{ font-size:36px; }}
}}
</style>
</head>
<body>

<div class="container">

<!-- Header -->
<div class="header">
  <h1><span>福彩3D</span><span>百位·十位·个位</span><span>杀码预测 V9</span></h1>
  <div class="subtitle">数据截至 {data['lastDate']}（第{data['lastIssue']}期） · 6杀制 · 算法不含未来信息</div>
</div>

<!-- Prediction Card -->
<div class="pred-card" id="predCard">
  <div class="badge">🔮 今日预测（6杀制）</div>
  <div class="issue">第 <strong id="predIssue">{data['prediction']['issue']}</strong> 期 · {data['prediction']['date']} <small style="opacity:.6">（基于截止第{data['lastIssue']}期数据）</small></div>
  <div class="positions">
    <div class="pos">
      <div class="pos-label">百位杀码</div>
      <div class="pos-num" id="predH">{data['prediction']['hundreds']},{data['prediction'].get('hundreds2','-')}</div>
      <div class="pos-sub">kill1 + kill2</div>
    </div>
    <div class="pos">
      <div class="pos-label">十位杀码</div>
      <div class="pos-num" id="predT">{data['prediction']['tens']},{data['prediction'].get('tens2','-')}</div>
      <div class="pos-sub">kill1 + kill2</div>
    </div>
    <div class="pos">
      <div class="pos-label">个位杀码</div>
      <div class="pos-num" id="predO">{data['prediction']['ones']},{data['prediction'].get('ones2','-')}</div>
      <div class="pos-sub">kill1 + kill2</div>
    </div>
  </div>
</div>

<!-- Stats: 100期 3杀 + 6杀 -->
<div class="section-title"><span class="dot"></span>近100期回测（3杀 + 6杀）</div>
<div class="stats-row">
  <div class="stat-card h">
    <div class="stat-label">百位 kill1</div>
    <div class="stat-val">{stats['h']}%</div>
    <div class="stat-detail">{stats['hC']}正确 / {stats['hW']}错误</div>
  </div>
  <div class="stat-card t">
    <div class="stat-label">十位 kill1</div>
    <div class="stat-val">{stats['t']}%</div>
    <div class="stat-detail">{stats['tC']}正确 / {stats['tW']}错误</div>
  </div>
  <div class="stat-card o">
    <div class="stat-label">个位 kill1</div>
    <div class="stat-val">{stats['o']}%</div>
    <div class="stat-detail">{stats['oC']}正确 / {stats['oW']}错误</div>
  </div>
  <div class="stat-card a6">
    <div class="stat-label">6杀全中率</div>
    <div class="stat-val">{stats.get('all6Pct', 'N/A')}%</div>
    <div class="stat-detail">{stats.get('all6', 0)}/100期</div>
  </div>
</div>

<!-- kill2 stats -->
<div class="section-title"><span class="dot"></span>kill2 独立准确率（近100期）</div>
<div class="stats-row">
  <div class="stat-card" style="border-top-color:#0f3460">
    <div class="stat-label">百位 kill2</div>
    <div class="stat-val" style="color:#0f3460">{stats.get('h2', 'N/A')}%</div>
    <div class="stat-detail">{stats.get('h2C', 0)}正确 / {stats.get('h2W', 0)}错误</div>
  </div>
  <div class="stat-card" style="border-top-color:#533483">
    <div class="stat-label">十位 kill2</div>
    <div class="stat-val" style="color:#533483">{stats.get('t2', 'N/A')}%</div>
    <div class="stat-detail">{stats.get('t2C', 0)}正确 / {stats.get('t2W', 0)}错误</div>
  </div>
  <div class="stat-card" style="border-top-color:#16a085">
    <div class="stat-label">个位 kill2</div>
    <div class="stat-val" style="color:#16a085">{stats.get('o2', 'N/A')}%</div>
    <div class="stat-detail">{stats.get('o2C', 0)}正确 / {stats.get('o2W', 0)}错误</div>
  </div>
</div>

<!-- Backtest Table: 100期 6杀明细 -->
<div class="section-title"><span class="dot"></span>近100期回测明细（6杀码 · 近期→远期）</div>
<div class="legend">
  <div class="legend-item"><span class="legend-dot ok"></span> 6杀全对</div>
  <div class="legend-item"><span class="legend-dot fail"></span> 有杀码错误</div>
</div>
<div class="table-wrap">
  <div class="table-scroll">
    <table>
      <thead>
        <tr>
          <th>期号</th><th>日期</th><th>开奖号</th>
          <th>百位杀</th><th>百位结果</th>
          <th>十位杀</th><th>十位结果</th>
          <th>个位杀</th><th>个位结果</th>
          <th>6杀</th>
        </tr>
      </thead>
      <tbody id="backtestBody"></tbody>
    </table>
  </div>
</div>

<!-- Strategy -->
<div class="section-title"><span class="dot"></span>策略架构（V9 六杀引擎）</div>
<div class="info-card">
  <h3>🔬 V9 六杀引擎</h3>
  <p><strong>每位置双杀码：</strong>kill1（V8条件决策树）+ kill2（独立算术公式），6杀全中为命中</p>
  <p><strong>kill2公式：</strong>百位=(b-span+9)%10 · 十位=(s-mid+5)%10 · 个位=(g²+|b-g|)%10</p>
  <p><strong>重叠处理：</strong>kill2==kill1时自动+1偏移，保证2个杀码不重复</p>
</div>
<div class="info-card">
  <h3>📋 策略详情</h3>
  <p><strong>百位 kill1：</strong>10条件决策树 — <strong>{stats['h']}%</strong> | kill2: (b-span+9)%10 — <strong>{stats.get('h2', 'N/A')}%</strong></p>
  <p><strong>十位 kill1：</strong>V8a增强公式 — <strong>{stats['t']}%</strong> | kill2: (s-mid+5)%10 — <strong>{stats.get('t2', 'N/A')}%</strong></p>
  <p><strong>个位 kill1：</strong>12条件决策树+自适应备份 — <strong>{stats['o']}%</strong> | kill2: (g²+|b-g|)%10 — <strong>{stats.get('o2', 'N/A')}%</strong></p>
  <div class="warn">
    ⚠️ <strong>重要提示：</strong>彩票本质是随机游戏。本算法基于历史统计规律，当前100期3杀综合准确率<strong>{stats['overall']}%</strong>，6杀全中率<strong>{stats.get('all6Pct', 'N/A')}%</strong>。数学理论上杀一码极限≈90%，6杀全中理论上限≈66%。但无法保证未来准确率，请理性参考。
  </div>
</div>

<div class="disclaimer">
  数据来源：福彩3D历史开奖数据 | V9六杀引擎 | 严格无未来信息 | 仅供研究参考
</div>

</div>

<script>
const DATA = {json_str};

function buildTable() {{
  const tbody = document.getElementById('backtestBody');
  let html = '';
  let cumH = 0, cumT = 0, cumO = 0, cum6 = 0;

  DATA.daily.forEach((r, i) => {{
    if (r.hOK) cumH++;
    if (r.tOK) cumT++;
    if (r.oOK) cumO++;
    const a6 = r.all6OK || false;
    if (a6) cum6++;

    const rowClass = a6 ? '' : 'row-fail';
    // 百位: kill1和kill2都对才算对
    const hAllOk = r.hOK && (r.h2OK !== false);
    const tAllOk = r.tOK && (r.t2OK !== false);
    const oAllOk = r.oOK && (r.o2OK !== false);
    const hClass = hAllOk ? 'cell-ok' : 'cell-fail';
    const tClass = tAllOk ? 'cell-ok' : 'cell-fail';
    const oClass = oAllOk ? 'cell-ok' : 'cell-fail';
    const a6Icon = a6 ? '✅' : '❌';

    html += `<tr class="${{rowClass}}">
      <td>${{r.issue}}</td>
      <td>${{r.date}}</td>
      <td class="cell-actual"><strong>${{r.actual}}</strong></td>
      <td class="cell-kill">${{r.hK}},${{r.hK2}}</td>
      <td class="${{hClass}}">${{hAllOk ? '✓' : '✗'}}</td>
      <td class="cell-kill">${{r.tK}},${{r.tK2}}</td>
      <td class="${{tClass}}">${{tAllOk ? '✓' : '✗'}}</td>
      <td class="cell-kill">${{r.oK}},${{r.oK2}}</td>
      <td class="${{oClass}}">${{oAllOk ? '✓' : '✗'}}</td>
      <td>${{a6Icon}}</td>
    </tr>`;

    if ((i+1) % 25 === 0 && i < DATA.daily.length - 1) {{
      html += `<tr class="summary-row">
        <td colspan="10">↑ 以上${{i+1}}期：3杀 ${{(cumH+cumT+cumO)}}/300 | 6杀全中 ${{cum6}}/${{i+1}} = ${{(cum6/(i+1)*100).toFixed(1)}}%</td>
      </tr>`;
    }}
  }});

  tbody.innerHTML = html;
}}

buildTable();
</script>

</body>
</html>'''

with open('D:/百十个/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("index.html 生成完成 (100期6杀制)")
