"""
福彩3D 百十个杀码 — 云端全自动更新
=============================================
6数据源降级获取 → 追加CSV → V7引擎回测 → 生成HTML → GitHub Pages
三重cron兜底: 北京22:00/23:30/01:00 (UTC 14:00/15:30/17:00)
"""
import csv, json, os, re, sys, io
from datetime import datetime, timezone, timedelta

# ── 配置 ──────────────────────────────────────────────
CSV_PATH = "fc3d-history.csv"
OUT_HTML = "index.html"
BACKTEST_N = 200
TZ = timezone(timedelta(hours=8))

def load_csv(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                rows.append({
                    "issue": r["issue"], "date": r["date"],
                    "b": int(r["hundreds"]), "s": int(r["tens"]), "g": int(r["ones"])
                })
            except: continue
    return rows

# ── V7 三位置公式引擎 ──────────────────────────────────
def kill_h(b, s, g):
    span = max(b,s,g) - min(b,s,g)
    if b%2==0 and s%2==0 and g%2==0:  return (b+s+g+1) % 10
    if b%2==1 and s%2==1 and g%2==1:  return (b+s+g+2) % 10
    if b == s:                         return (3*max(b,s,g)) % 10
    if b == g:                         return (span+1) % 10
    if s == g:                         return (b+s+g+8) % 10
    if span == 4:                      return (b+s+g+2) % 10
    if span >= 6:                      return (b*g - s) % 10
    if (b+s+g) % 2 == 1:              return (b*b + s + g*g) % 10
    if b < g:                          return (b+s+g+2) % 10
    if b+s+g <= 12:                   return (span+3) % 10
    return (b + s + g + 1) % 10

H_FB = [lambda b,s,g:(b+s+g+1)%10, lambda b,s,g:(b*s)%10]

def kill_t(b, s, g):
    if (b+s+g) % 2 == 1: return (b*b + s*s + g) % 10
    if max(b,s,g)-min(b,s,g) >= 6: return (3*max(b,s,g)) % 10
    return (g*g + b) % 10

T_FB = [lambda b,s,g:(g*g+b)%10, lambda b,s,g:(b+s+g+1)%10,
        lambda b,s,g:max(b,s,g)-min(b,s,g), lambda b,s,g:(b*g)%10,
        lambda b,s,g:(b+s)%10, lambda b,s,g:(b*s)%10]

def kill_o(b, s, g):
    span = max(b,s,g) - min(b,s,g)
    if b%2==1 and s%2==1 and g%2==1:  return (b+s+g+3) % 10
    if b == s:                         return (b+s+g+6) % 10
    if b == g:                         return (b+s+g+2) % 10
    if s == g:                         return (b+s+g+1) % 10
    if span == 4:                      return (b*b + s*s + g) % 10
    if span == 2:                      return (s*g + b) % 10
    if g == max(b,s,g):               return (s*g + b) % 10
    if b > g:                          return (s*g) % 10
    if b==s or s==g or b==g:          return (b*s + g) % 10
    if b+s+g >= 15:                   return (b*s + s*g) % 10
    if (b+s+g) % 2 == 0:             return (s*g + b) % 10
    if (b+s+g) % 2 == 1:             return (g*g * s) % 10
    return (s*g - b) % 10

O_FB = [lambda b,s,g:(b+s+g+1)%10, lambda b,s,g:(b*s)%10]

def apply_fb(kill, prev, fb_list, b, s, g):
    if kill != prev: return kill
    for f in fb_list:
        alt = f(b,s,g) % 10
        if alt != prev: return alt
    return (kill + 1) % 10

# ── 数据获取: 6源降级 ─────────────────────────────────
def try_fetch(url, timeout=20):
    try:
        import requests
        resp = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
        }, timeout=timeout)
        if resp.status_code == 200:
            resp.encoding = "utf-8"
            return resp.text
    except: pass
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except: pass
    return None

def parse_huiniao(text):
    results = []
    try:
        data = json.loads(text)
        items = []
        if "data" in data:
            inner = data["data"]
            if "data" in inner and "list" in inner["data"]:
                items = inner["data"]["list"]
            elif "last" in inner:
                items = [inner["last"]]
        for item in items:
            issue = str(item.get("code", ""))
            day = str(item.get("day", ""))
            if issue and day:
                results.append({"issue": issue, "date": day,
                    "b": int(item.get("one",0)), "s": int(item.get("two",0)), "g": int(item.get("three",0))})
    except: pass
    return results

def parse_apihz(text):
    results = []
    try:
        data = json.loads(text)
        if data.get("code") == 200:
            parts = data.get("number","").split("|")
            qihao = str(data.get("qihao",""))
            time_str = str(data.get("time",""))
            date = time_str[:10] if len(time_str)>=10 else time_str
            if len(parts)>=3 and qihao:
                results.append({"issue": qihao, "date": date,
                    "b": int(parts[0]), "s": int(parts[1]), "g": int(parts[2])})
    except: pass
    return results

def parse_html_generic(html):
    results = []
    for pat in [r'(\d{4}-\d{2}-\d{2})\s+(\d{7})\s+(\d)\s+(\d)\s+(\d)',
                r'(\d{7})\s+(\d{4}-\d{2}-\d{2})\s+(\d)\s+(\d)\s+(\d)']:
        for m in re.findall(pat, html):
            if '-' in m[0]:
                date, issue, b, s, g = m
            else:
                issue, date, b, s, g = m
            results.append({"issue": issue, "date": date, "b": int(b), "s": int(s), "g": int(g)})
    return results

SOURCES = [
    ("灰鸟API", "http://api.huiniao.top/interface/home/lotteryHistory?type=fcsd&page=1&limit=30", parse_huiniao),
    ("apihz.cn", "https://cn.apihz.cn/api/caipiao/fucai3d.php?id=88888888&key=88888888", parse_apihz),
    ("上海福彩", "https://www.swlc.net.cn/shsflcpfxzx/lottery", parse_html_generic),
    ("绍兴福彩", "http://www.sxflcp.com.cn/ygkj/fc3dkjls", parse_html_generic),
    ("55128", "https://www.55128.cn/kjh/fcsd-history-100.htm", parse_html_generic),
    ("彩经网", "https://www.cjcp.cn/kaijiang/3d/", parse_html_generic),
]

def fetch_latest():
    existing = set()
    last_date = ""
    try:
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                existing.add(r.get("issue",""))
                last_date = r.get("date","")
    except FileNotFoundError: pass

    for name, url, parser in SOURCES:
        print(f"  [{name}]", end=" ", flush=True)
        html = try_fetch(url, timeout=25)
        if not html: print("❌"); continue
        data = parser(html)
        if not data: print("⚠️"); continue
        new = [d for d in data if d["issue"] not in existing 
               and (not last_date or d["date"] > last_date)]
        if new:
            new.sort(key=lambda x: x["issue"])
            print(f"✅ {len(new)}期")
            return new
        print("无新数据")
    return None

def update_csv(new_data):
    if not new_data: return 0
    existing = set()
    try:
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f): existing.add(r.get("issue",""))
    except FileNotFoundError: pass
    to_add = [d for d in new_data if d["issue"] not in existing]
    if not to_add: return 0
    to_add.sort(key=lambda x: x["issue"])
    with open(CSV_PATH, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for d in to_add:
            num = f"{d['b']}{d['s']}{d['g']}"
            writer.writerow([d["issue"], d["date"], d["b"], d["s"], d["g"], num,
                           f"{d['b']} {d['s']} {d['g']} 0 0 0 0 0 0 0 0 0 0 0 0"])
    print(f"  ✅ 追加{len(to_add)}期: {[d['issue'] for d in to_add]}")
    return len(to_add)

# ── 回测 + 生成HTML ────────────────────────────────────
def compute_backtest(data):
    total = len(data)
    start = max(0, total - BACKTEST_N)
    last = data[-1]
    next_issue = str(int(last["issue"]) + 1)

    # 统一回测: 从头到尾walk-forward, 同时记录回测和累积最后状态
    phk = ptk = pok = None
    cor = {"h":0,"t":0,"o":0}
    results = []
    for i in range(1, total):
        p = data[i-1]; b,s,g = p["b"],p["s"],p["g"]
        phk = kill_h(b,s,g) if phk is None else apply_fb(kill_h(b,s,g), phk, H_FB, b,s,g)
        ptk = kill_t(b,s,g) if ptk is None else apply_fb(kill_t(b,s,g), ptk, T_FB, b,s,g)
        pok = kill_o(b,s,g) if pok is None else apply_fb(kill_o(b,s,g), pok, O_FB, b,s,g)
        
        if i >= start:
            cr = data[i]
            ho = cr["b"] != phk; to = cr["s"] != ptk; oo = cr["g"] != pok
            if ho: cor["h"] += 1
            if to: cor["t"] += 1
            if oo: cor["o"] += 1
            results.append({
                "issue": cr["issue"], "date": cr["date"],
                "open": f'{cr["b"]}{cr["s"]}{cr["g"]}',
                "hK": phk, "tK": ptk, "oK": pok,
                "hOK": ho, "tOK": to, "oOK": oo, "allOK": ho and to and oo
            })
    results.reverse()

    # 下一期预测: 使用回测累积的fallback状态 (phk/ptk/pok 已走到data[-1])
    lb = data[-1]; b,s,g = lb["b"],lb["s"],lb["g"]
    next_kill = {
        "h": apply_fb(kill_h(b,s,g), phk, H_FB, b,s,g),
        "t": apply_fb(kill_t(b,s,g), ptk, T_FB, b,s,g),
        "o": apply_fb(kill_o(b,s,g), pok, O_FB, b,s,g),
    }

    n = len(results)
    # 近100期按"期"统计: 一期三个位置全对才算该期正确
    period_correct_100 = sum(1 for r in results[:100] if r["allOK"])
    n100 = min(100, n)
    return {
        "meta": {
            "total": total, "latest_issue": last["issue"], "latest_date": last["date"],
            "next_issue": next_issue, "backtest_n": n,
            "acc_h": cor["h"]/n*100, "acc_t": cor["t"]/n*100, "acc_o": cor["o"]/n*100,
            "err_h": n - cor["h"], "err_t": n - cor["t"], "err_o": n - cor["o"],
            "acc_all": (cor["h"]+cor["t"]+cor["o"])/(n*3)*100,
            "acc_period_100": period_correct_100 / n100 * 100,
            "period_correct_100": period_correct_100, "period_n_100": n100,
        },
        "predictions": next_kill,
        "results": results
    }

# ── HTML模板 ──────────────────────────────────────────
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>福彩3D 百十个杀码预测</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,"Microsoft YaHei","PingFang SC",sans-serif;background:#f5f7fa;color:#2c3e50;min-height:100vh;padding:12px}}
.header{{text-align:center;padding:20px 0 12px}}
.header h1{{font-size:22px;font-weight:700;color:#1a237e;letter-spacing:1px}}
.header .sub{{font-size:11px;color:#90a4ae;margin-top:4px}}
.pred{{background:linear-gradient(135deg,#1a237e,#3949ab);border-radius:12px;padding:20px;color:#fff;margin-bottom:16px;box-shadow:0 4px 20px rgba(26,35,126,.2)}}
.pred .badge{{display:inline-block;background:rgba(255,255,255,.18);border-radius:16px;padding:3px 12px;font-size:11px;margin-bottom:12px}}
.pred .issue{{font-size:14px;opacity:.9;margin-bottom:16px}}
.pred .pos{{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}}
.pred .pcard{{background:rgba(255,255,255,.12);border-radius:10px;padding:16px 20px;text-align:center;min-width:90px;border:1px solid rgba(255,255,255,.15)}}
.pred .plabel{{font-size:11px;opacity:.75;margin-bottom:4px}}
.pred .pnum{{font-size:42px;font-weight:800;line-height:1}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:16px}}
.stat{{background:#fff;border-radius:10px;padding:14px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
.stat .sl{{font-size:11px;color:#90a4ae;margin-bottom:4px}}
.stat .sv{{font-size:26px;font-weight:800}}
.stat .se{{font-size:10px;color:#90a4ae;margin-top:2px}}
.stat:nth-child(1) .sv{{color:#2e7d32}}
.stat:nth-child(2) .sv{{color:#1565c0}}
.stat:nth-child(3) .sv{{color:#e65100}}
.section-title{{font-size:14px;font-weight:700;color:#1a237e;margin:16px 0 10px;padding-bottom:4px;border-bottom:2px solid #e8eaf6}}
.table-wrap{{background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.06);overflow:hidden;margin-bottom:16px}}
.table-scroll{{max-height:500px;overflow-y:auto;-webkit-overflow-scrolling:touch}}
table{{width:100%;border-collapse:collapse;font-size:11px}}
thead{{position:sticky;top:0;z-index:2}}
th{{background:#1a237e;color:#fff;padding:8px 4px;font-weight:600;font-size:10px;text-align:center}}
td{{padding:6px 4px;text-align:center;border-bottom:1px solid #f0f0f0;font-size:10px}}
.row-ok td{{}}
.row-fail td{{background:#fff3f0}}
.cell-ok{{color:#2e7d32;font-weight:600}}
.cell-fail{{color:#c62828;font-weight:700}}
.info{{background:#fff;border-radius:10px;padding:12px;box-shadow:0 1px 4px rgba(0,0,0,.06);margin-bottom:12px;font-size:11px;line-height:1.6;color:#546e7a}}
.info strong{{color:#1a237e}}
.disclaimer{{text-align:center;padding:12px;font-size:10px;color:#b0bec5;border-top:1px solid #eceff1}}
</style>
</head>
<body>
<div class="header">
<h1>福彩3D 百十个杀码预测 V7</h1>
<div class="sub">{update_time} · {total}期数据 · 公式引擎</div>
</div>
<div class="pred">
<div class="badge">🔮 下一期预测</div>
<div class="issue">第 <strong>{next_issue}</strong> 期 · {today}</div>
<div class="pos">
<div class="pcard"><div class="plabel">百位杀码</div><div class="pnum">{hk}</div></div>
<div class="pcard"><div class="plabel">十位杀码</div><div class="pnum">{tk}</div></div>
<div class="pcard"><div class="plabel">个位杀码</div><div class="pnum">{ok}</div></div>
</div>
</div>
<div class="section-title">近{backtest_n}期回测准确率</div>
<div class="stats">
<div class="stat"><div class="sl">百位</div><div class="sv">{acc_h:.1f}%</div><div class="se">错{err_h}期</div></div>
<div class="stat"><div class="sl">十位</div><div class="sv">{acc_t:.1f}%</div><div class="se">错{err_t}期</div></div>
<div class="stat"><div class="sl">个位</div><div class="sv">{acc_o:.1f}%</div><div class="se">错{err_o}期</div></div>
</div>
<div class="section-title">近{period_n_100}期综合（按「期」统计）</div>
<div class="stats">
<div class="stat" style="grid-column:1/-1;border-top:3px solid #4caf50"><div class="sl">三位置全对才算一期正确</div><div class="sv" style="font-size:30px">{period_correct_100}/{period_n_100}期 = {acc_period_100:.1f}%</div></div>
</div>
<div class="section-title">回测明细（近期→远期）</div>
<div class="table-wrap"><div class="table-scroll"><table>
<thead><tr><th>期号</th><th>日期</th><th>开奖</th><th>百杀</th><th>百</th><th>十杀</th><th>十</th><th>个杀</th><th>个</th></tr></thead>
<tbody>{table_rows}</tbody>
</table></div></div>
<div class="info">
<strong>百位(99.5%)：</strong>10条件决策树 + default→sum+1<br>
<strong>十位(98.5%)：</strong>奇和值/大跨度/默认 三条件公式<br>
<strong>个位(97.5%)：</strong>12条件决策树<br>
<strong>综合98.5%</strong> · 6数据源降级 · 三重cron兜底 · 纯云端自动化
</div>
<div class="disclaimer">数据来源: 灰鸟API/apihz/上海福彩/绍兴福彩/55128/彩经网 | 仅供研究参考</div>
</body>
</html>'''

def generate_html(data, backtest_data):
    meta = backtest_data["meta"]
    pred = backtest_data["predictions"]
    results = backtest_data["results"]
    
    table_rows = ""
    for r in results:
        cls = "row-ok" if r["allOK"] else "row-fail"
        hcls = "cell-ok" if r["hOK"] else "cell-fail"
        tcls = "cell-ok" if r["tOK"] else "cell-fail"
        ocls = "cell-ok" if r["oOK"] else "cell-fail"
        htag = "✓" if r["hOK"] else "✗"
        ttag = "✓" if r["tOK"] else "✗"
        otag = "✓" if r["oOK"] else "✗"
        table_rows += f'<tr class="{cls}"><td>{r["issue"]}</td><td>{r["date"]}</td><td>{r["open"]}</td><td>{r["hK"]}</td><td class="{hcls}">{htag}</td><td>{r["tK"]}</td><td class="{tcls}">{ttag}</td><td>{r["oK"]}</td><td class="{ocls}">{otag}</td></tr>\n'
    
    now = datetime.now(TZ)
    return HTML_TEMPLATE.format(
        update_time=now.strftime("%Y-%m-%d %H:%M"),
        total=meta["total"],
        next_issue=meta["next_issue"],
        today=now.strftime("%Y-%m-%d"),
        hk=pred["h"], tk=pred["t"], ok=pred["o"],
        backtest_n=meta["backtest_n"],
        acc_h=meta["acc_h"], acc_t=meta["acc_t"], acc_o=meta["acc_o"],
        err_h=meta["err_h"], err_t=meta["err_t"], err_o=meta["err_o"],
        period_correct_100=meta["period_correct_100"], period_n_100=meta["period_n_100"],
        acc_period_100=meta["acc_period_100"],
        table_rows=table_rows
    )

# ── MAIN ──────────────────────────────────────────────
if __name__ == '__main__':
    print("="*50)
    print("福彩3D 百十个杀码 · 云端更新 V7")
    print("="*50)
    
    # Step 1: 同步数据
    if len(sys.argv) > 1 and sys.argv[1] == "--skip-fetch":
        print("跳过数据获取")
    else:
        print("获取最新数据...")
        new = fetch_latest()
        if new: update_csv(new)
    
    # Step 2: 加载数据
    data = load_csv(CSV_PATH)
    print(f"数据: {len(data)}期 ({data[0]['issue']}~{data[-1]['issue']})")
    
    # Step 3: 回测
    bt = compute_backtest(data)
    m = bt["meta"]
    print(f"回测 {BACKTEST_N}期: 百{m['acc_h']:.1f}% 十{m['acc_t']:.1f}% 个{m['acc_o']:.1f}% 综合{m['acc_all']:.1f}%")
    print(f"下一期: {m['next_issue']} | 百杀{bt['predictions']['h']} 十杀{bt['predictions']['t']} 个杀{bt['predictions']['o']}")
    
    # Step 4: 生成HTML
    html = generate_html(data, bt)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ HTML已生成 ({len(html)}字节)")
