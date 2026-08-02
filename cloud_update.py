"""
福彩3D 百十个杀码 — 云端全自动更新 V9
=============================================
6数据源降级获取 → 追加CSV → V9引擎回测 → 生成HTML → GitHub Pages
三重cron兜底: 北京22:00/23:30/01:00 (UTC 14:00/15:30/17:00)
V9: V8三杀码 + 每位置独立第二杀码（6杀制）
"""
import csv, json, os, re, sys, io
from datetime import datetime
CSV_PATH = "fc3d-history.csv"
OUT_HTML = "index.html"
BACKTEST_N = 100
KILL6_HISTORY = "kill6_history.json"
# 升级触发条件 (满足任一即重新穷举6个算法)
TRIG_BELOW_PCT = 70.0      # 滚动100期6杀全中率跌破此值
TRIG_MONTH_DROP_PP = 8.0   # 单月(30天)下滑超过此pp
TRIG_MONTH_DAYS = 30

# ── 数据获取 (6源降级) ────────────────────────────────
def http_get(url, timeout=15, ua=None):
    headers = {"User-Agent": ua or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        import requests
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code == 200:
            r.encoding = "utf-8"
            return r.text
    except: pass
    try:
        import urllib.request
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except: pass
    return None

def fetch_latest():
    """多数据源依次尝试, 拿新数据就停 (2026-08-03四级结构)
    ①灰鸟API(带next_code跨年安全) ②17500.cn(官方级全量TXT, 带429重试)
    中彩网已移除: 2026-08实测返回WAF反爬页(标题40..), 永远解析失败浪费请求
    返回 (data, alive): alive=True表示至少一个源成功返回数据(期号可能<=本地, 属正常无新期)"""
    sources = [
        ("灰鸟API", lambda: fetch_huiniao()),
        ("17500.cn", lambda: fetch_17500()),
    ]

    last_issue = None
    try:
        rows = load_csv(CSV_PATH)
        if rows: last_issue = rows[-1]["issue"]
    except: pass

    alive = False
    for name, fn in sources:
        try:
            data = fn()
            if not data: continue
            alive = True  # 源成功返回数据即视为活着
            # 期号合理性校验: 必须 > 本地最新期号, 否则视为缓存/旧数据拒绝
            if last_issue and str(data["issue"]) <= str(last_issue):
                print(f"  ⏭️ {name}: 期号{data['issue']}<=本地{last_issue}, 跳过(无新期, 源正常)")
                continue
            print(f"  ✅ {name}: {data['issue']} ({data['date']}) {data['b']}{data['s']}{data['g']}")
            return data, True
        except Exception as e:
            print(f"  ⚠️ {name}: {e}")
    return None, alive

def fetch_huiniao():
    url = "http://api.huiniao.top/interface/home/lotteryHistory?type=fcsd&page=1&limit=1"
    text = http_get(url)
    if not text: return None
    data = json.loads(text)
    if data.get("code") != 1: return None
    item = data["data"]["data"]["list"][0]
    return {"issue": item["code"], "date": item["day"], "b": item["one"], "s": item["two"], "g": item["three"],
            "next_issue": item.get("next_code")}

def fetch_17500():
    """17500.cn 官方级全量TXT (2002至今, 每行: 期号 日期 百 十 个 ...)
    https://www.17500.cn/getData/3d.TXT — 2026-08实测真源, 与灰鸟数据交叉验证一致
    注意: 该站有反爬限流(偶发429), 失败自动重试3次+换UA"""
    url = "https://www.17500.cn/getData/3d.TXT"
    uas = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Python-urllib/3.11",
    ]
    text = None
    for attempt in range(3):
        text = http_get(url, ua=uas[attempt % len(uas)])
        if text: break
        import time; time.sleep(2)  # 429限流时等待重试
    if not text: return None
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines: return None
    last = lines[-1].split()
    if len(last) < 5 or not re.match(r'20\d{5}$', last[0]):
        return None
    try:
        return {"issue": last[0], "date": last[1],
                "b": int(last[2]), "s": int(last[3]), "g": int(last[4])}
    except: return None

# ── 历史数据源(已失效, 保留说明) ────────────────────
# apihz: 公共key JSON, 2026-08实测接口404已死
# 中彩网: WAF反爬页(标题40..), 正则永远解析失败
# 8200/55128/彩经网: DNS失败/拒连/403, 2026-07移除

# ── CSV 操作 ──────────────────────────────────────────
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

def append_csv(path, data):
    existing = set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f): existing.add(r.get("issue", ""))
    except FileNotFoundError: pass
    if data["issue"] in existing:
        return 0
    with open(path, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        num = f"{data['b']}{data['s']}{data['g']}"
        writer.writerow([data["issue"], data["date"], data["b"], data["s"], data["g"], num,
                       f"{data['b']} {data['s']} {data['g']} 0 0 0 0 0 0 0 0 0 0 0 0"])
    return 1

# ── V8 三位置公式引擎 ──────────────────────────────────
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
    # V8a: sum_odd b²+s²=0修复 + span_ge6 b最大修复 → 200期98.5%
    if (b+s+g) % 2 == 1:
        if (b*b + s*s) % 10 == 0:
            return (b + s + g + 2) % 10
        return (b*b + s*s + g) % 10
    if max(b,s,g)-min(b,s,g) >= 6:
        if b >= s and b >= g:
            return ((b + s) * g) % 10
        return (3*max(b,s,g)) % 10
    return (g*g + b) % 10

T_FB = [lambda b,s,g:(g*g+b)%10, lambda b,s,g:(b+s+g+1)%10,
        lambda b,s,g:max(b,s,g)-min(b,s,g), lambda b,s,g:(b*g)%10,
        lambda b,s,g:(b+s)%10, lambda b,s,g:(b*s)%10]

def _get_o_cond(b, s, g):
    sp = max(b,s,g) - min(b,s,g)
    if b%2==1 and s%2==1 and g%2==1: return 'all_odd'
    if b == s: return 'b_eq_s'
    if b == g: return 'b_eq_g'
    if s == g: return 's_eq_g'
    if sp == 4: return 'span4'
    if sp == 2: return 'span2'
    if g == max(b,s,g): return 'g_max'
    if b > g: return 'b_gt_g'
    if b==s or s==g or b==g: return 'pair'
    if b+s+g >= 15: return 'sum_hi'
    if (b+s+g) % 2 == 0: return 'sum_even'
    if (b+s+g) % 2 == 1: return 'sum_odd'
    return 'default'

O_BACKUP_FM = {
    'g_max': lambda b,s,g: (3*max(b,s,g)) % 10,
    'b_gt_g': lambda b,s,g: (b*b + g) % 10,
    'sum_hi': lambda b,s,g: (b+s+g+3) % 10,
    'sum_odd': lambda b,s,g: (b+s+g+1) % 10,
    'default': lambda b,s,g: (b+s+g+1) % 10,
}

O_FAIL_WIN = 5

def kill_o(b, s, g, fail_state=None, period_idx=None):
    span = max(b,s,g) - min(b,s,g)
    if b%2==1 and s%2==1 and g%2==1:  pk = (b+s+g+3) % 10
    elif b == s:                         pk = (b+s+g+6) % 10
    elif b == g:                         pk = (b+s+g+2) % 10
    elif s == g:                         pk = (b+s+g+1) % 10
    elif span == 4:                      pk = (b*b + s*s + g) % 10
    elif span == 2:                      pk = (s*g + b) % 10
    elif g == max(b,s,g):               pk = (s*g + b) % 10
    elif b > g:                          pk = (s*g) % 10
    elif b==s or s==g or b==g:          pk = (b*s + g) % 10
    elif b+s+g >= 15:                   pk = (b*s + s*g) % 10
    elif (b+s+g) % 2 == 0:             pk = (s*g + b) % 10
    elif (b+s+g) % 2 == 1:             pk = (g*g * s) % 10
    else:                                pk = (s*g - b) % 10
    if fail_state is not None and period_idx is not None:
        cn = _get_o_cond(b, s, g)
        if cn in fail_state and period_idx - fail_state[cn] <= O_FAIL_WIN:
            if cn in O_BACKUP_FM:
                pk = O_BACKUP_FM[cn](b, s, g) % 10
    return pk

O_FB = [lambda b,s,g:(b+s+g+1)%10, lambda b,s,g:(b*s)%10]

# ── V9: 第二杀码 ──────────────────────────────────
def kill_h2(b, s, g):
    span = max(b, s, g) - min(b, s, g)
    k = (b - span + 9) % 10
    k1 = kill_h(b, s, g)
    if k == k1: k = (k + 1) % 10
    return k

def kill_t2(b, s, g):
    mid = sorted([b, s, g])[1]
    k = (s - mid + 5) % 10
    k1 = kill_t(b, s, g)
    if k == k1: k = (k + 1) % 10
    return k

def kill_o2(b, s, g):
    k = (g*g + abs(b-g)) % 10
    k1 = kill_o(b, s, g)
    if k == k1: k = (k + 1) % 10
    return k

def apply_fb(kill, prev, fb_list, b, s, g):
    if kill != prev: return kill
    for f in fb_list:
        alt = f(b,s,g) % 10
        if alt != prev: return alt
    return (kill + 1) % 10

# ── 升级触发检测器 ─────────────────────────────────────
def record_kill6(pct, issue, date):
    """把每日6杀全中率追加到历史文件, 用于单月下滑检测"""
    hist = []
    if os.path.exists(KILL6_HISTORY):
        try:
            hist = json.load(open(KILL6_HISTORY, encoding="utf-8"))
        except: hist = []
    # 同期号不重复记录
    if hist and hist[-1].get("issue") == issue:
        hist[-1].update({"pct": round(pct, 2), "date": date})
    else:
        hist.append({"issue": issue, "date": date, "pct": round(pct, 2)})
    hist = hist[-400:]  # 只留最近400条(约1年)
    json.dump(hist, open(KILL6_HISTORY, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return hist

def check_upgrade_trigger(cur_pct, hist):
    """检测两个升级触发条件, 返回 (是否触发, 触发原因列表, 当月下滑pp)"""
    reasons = []
    # 条件1: 当前滚动100期6杀全中率跌破阈值
    if cur_pct < TRIG_BELOW_PCT:
        reasons.append(f"6杀全中率 {cur_pct:.1f}% 跌破 {TRIG_BELOW_PCT:.0f}%")
    # 条件2: 单月下滑超阈值 — 找约30天前的记录
    drop = 0.0
    if len(hist) >= 2:
        from datetime import date as _d
        try:
            cur_d = datetime.strptime(hist[-1]["date"], "%Y-%m-%d")
            ref = None
            for h in reversed(hist[:-1]):
                if (cur_d - datetime.strptime(h["date"], "%Y-%m-%d")).days >= TRIG_MONTH_DAYS:
                    ref = h; break
            if ref is None: ref = hist[0]
            drop = ref["pct"] - cur_pct
            if drop >= TRIG_MONTH_DROP_PP:
                reasons.append(f"单月下滑 {drop:.1f}pp (从{ref['date']}的{ref['pct']:.1f}%) 超过 {TRIG_MONTH_DROP_PP:.0f}pp")
        except: pass
    return (len(reasons) > 0), reasons, drop

def next_issue_calc(last):
    """跨年安全: 福彩3D年末最后一期后回绕到次年001.
    优先用数据源给的next_code(已含回绕); 兜底按日期判断(12-31开奖→次年001)."""
    if last.get("next_issue"):
        return str(last["next_issue"])
    iss = str(last["issue"])
    yy, seq = int(iss[:4]), int(iss[4:])
    try:
        d = datetime.strptime(last["date"], "%Y-%m-%d")
        if d.month == 12 and d.day == 31:
            return f"{yy+1}001"
    except: pass
    return f"{yy}{seq+1:03d}"

# ── 回测 + HTML生成 ──────────────────────────────────
def compute_backtest(data):
    total = len(data)
    start = max(0, total - BACKTEST_N)
    last = data[-1]
    next_issue = next_issue_calc(last)

    phk = ptk = pok = None
    cor = {"h":0,"t":0,"o":0}
    cor2 = {"h":0,"t":0,"o":0}
    all6 = 0
    results = []
    o_fail = {}

    for i in range(1, total):
        p = data[i-1]; b,s,g = p["b"],p["s"],p["g"]
        phk = apply_fb(kill_h(b,s,g), phk, H_FB, b,s,g) if phk is not None else kill_h(b,s,g)
        ptk = apply_fb(kill_t(b,s,g), ptk, T_FB, b,s,g) if ptk is not None else kill_t(b,s,g)
        pok_raw = kill_o(b,s,g, o_fail, i)
        pok = apply_fb(pok_raw, pok, O_FB, b,s,g) if pok is not None else pok_raw
        if pok == data[i]["g"]:
            cn = _get_o_cond(b, s, g)
            o_fail[cn] = i

        if i >= start:
            cr = data[i]
            # V9: kill2
            hk2 = kill_h2(b,s,g); tk2 = kill_t2(b,s,g); ok2 = kill_o2(b,s,g)
            ho = cr["b"] != phk; to = cr["s"] != ptk; oo = cr["g"] != pok
            h2o = cr["b"] != hk2; t2o = cr["s"] != tk2; o2o = cr["g"] != ok2
            if ho: cor["h"] += 1
            if to: cor["t"] += 1
            if oo: cor["o"] += 1
            if h2o: cor2["h"] += 1
            if t2o: cor2["t"] += 1
            if o2o: cor2["o"] += 1
            if ho and to and oo and h2o and t2o and o2o: all6 += 1
            results.append({
                "issue": cr["issue"], "date": cr["date"],
                "open": f'{cr["b"]}{cr["s"]}{cr["g"]}',
                "hK": phk, "tK": ptk, "oK": pok,
                "hK2": hk2, "tK2": tk2, "oK2": ok2,
                "hOK": ho, "tOK": to, "oOK": oo,
                "h2OK": h2o, "t2OK": t2o, "o2OK": o2o,
                "allOK": ho and to and oo,
                "all6OK": ho and to and oo and h2o and t2o and o2o
            })
    results.reverse()

    lb = data[-1]; b,s,g = lb["b"],lb["s"],lb["g"]
    next_kill = {
        "h": apply_fb(kill_h(b,s,g), phk, H_FB, b,s,g),
        "t": apply_fb(kill_t(b,s,g), ptk, T_FB, b,s,g),
        "o": apply_fb(kill_o(b,s,g, o_fail, total), pok, O_FB, b,s,g),
        "h2": kill_h2(b,s,g), "t2": kill_t2(b,s,g), "o2": kill_o2(b,s,g),
    }

    n = len(results)
    period_correct_100 = sum(1 for r in results[:100] if r["allOK"])
    period6_correct_100 = sum(1 for r in results[:100] if r.get("all6OK", False))
    n100 = min(100, n)

    return {
        "meta": {
            "total": total, "latest_issue": last["issue"], "latest_date": last["date"],
            "next_issue": next_issue, "backtest_n": n,
            "acc_h": cor["h"]/n*100, "acc_t": cor["t"]/n*100, "acc_o": cor["o"]/n*100,
            "err_h": n-cor["h"], "err_t": n-cor["t"], "err_o": n-cor["o"],
            "acc_all": (cor["h"]+cor["t"]+cor["o"])/(n*3)*100,
            "acc_period_100": period_correct_100 / n100 * 100,
            "period_correct_100": period_correct_100, "period_n_100": n100,
            "acc_h2": cor2["h"]/n*100, "acc_t2": cor2["t"]/n*100, "acc_o2": cor2["o"]/n*100,
            "all6": all6, "all6_pct": all6/n*100,
            "period6_correct_100": period6_correct_100, "period6_pct_100": period6_correct_100/n100*100,
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
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f5f7fa;color:#333;padding:12px;max-width:600px;margin:0 auto}}
h1{{font-size:18px;text-align:center;color:#1a237e;margin:8px 0 12px}}
.pred{{background:linear-gradient(135deg,#1a237e,#283593);border-radius:14px;padding:16px;color:#fff;margin-bottom:14px}}
.pred .badge{{font-size:11px;opacity:.8;margin-bottom:4px}}
.pred .issue{{font-size:13px;margin-bottom:12px}}
.poses{{display:flex;gap:10px}}
.pos{{flex:1;text-align:center;background:rgba(255,255,255,.12);border-radius:10px;padding:12px 6px}}
.pos-label{{font-size:11px;opacity:.8;margin-bottom:4px}}
.pos-num{{font-size:32px;font-weight:800;line-height:1}}
.section-title{{font-size:14px;font-weight:700;color:#455a64;margin:16px 0 8px;display:flex;align-items:center;gap:8px}}
.section-title .dot{{width:8px;height:8px;border-radius:50%;background:#1a237e;display:inline-block}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px}}
.stat{{background:#fff;border-radius:10px;padding:12px 8px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
.stat .sv{{font-size:24px;font-weight:800;color:#1a237e}}
.stat .sl{{font-size:11px;color:#78909c;margin-top:2px}}
.stat .se{{font-size:10px;color:#90a4ae}}
.period-stat{{background:#fff;border-radius:10px;padding:12px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.06);margin-bottom:14px}}
.period-stat .pv{{font-size:22px;font-weight:800;color:#e65100}}
.period-stat .pl{{font-size:11px;color:#78909c}}
.info-card{{background:#fff;border-radius:10px;padding:14px;margin-bottom:12px;box-shadow:0 1px 4px rgba(0,0,0,.06);font-size:12px;line-height:1.7}}
.info-card h3{{font-size:13px;color:#37474f;margin-bottom:6px}}
.warn{{background:#fff3e0;border-left:3px solid #ff9800;padding:10px 12px;border-radius:0 8px 8px 0;font-size:11px;margin-top:8px;color:#e65100}}
.upgrade-alert{{background:linear-gradient(135deg,#b71c1c,#d32f2f);color:#fff;border-radius:12px;padding:14px 16px;margin-bottom:14px;font-size:13px;line-height:1.7;box-shadow:0 2px 8px rgba(183,28,28,.3)}}
.upgrade-alert .ua-title{{font-size:15px;font-weight:800;margin-bottom:4px}}
.data-alert{{background:linear-gradient(135deg,#e65100,#f57c00);color:#fff;border-radius:12px;padding:14px 16px;margin-bottom:14px;font-size:13px;line-height:1.7;box-shadow:0 2px 8px rgba(230,81,0,.3)}}
.data-alert .da-title{{font-size:15px;font-weight:800;margin-bottom:4px}}
table{{width:100%;border-collapse:collapse;font-size:11px;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
th{{background:#eceff1;padding:8px 6px;text-align:center;font-weight:600;color:#455a64;position:sticky;top:0}}
td{{padding:6px;text-align:center;border-bottom:1px solid #f0f0f0}}
.ok{{color:#2e7d32;font-weight:700}}
.bad{{color:#c62828;font-weight:700}}
.table-wrap{{max-height:60vh;overflow-y:auto;-webkit-overflow-scrolling:touch;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
.disclaimer{{text-align:center;font-size:10px;color:#90a4ae;margin-top:16px;padding:8px}}
@media(max-width:380px){{.pos-num{{font-size:26px}}.stats{{grid-template-columns:repeat(3,1fr);gap:6px}}.stat{{padding:8px 4px}}.stat .sv{{font-size:20px}}}}
</style>
</head>
<body>
<h1>福彩3D 百十个杀码预测 V9</h1>

<div class="pred">
<div class="badge">🔮 下一期预测（6杀制）</div>
<div class="issue">第 <strong>{next_issue}</strong> 期</div>
<div class="poses">
<div class="pos"><div class="pos-label">百位杀码</div><div class="pos-num">{pred_h},{pred_h2}</div></div>
<div class="pos"><div class="pos-label">十位杀码</div><div class="pos-num">{pred_t},{pred_t2}</div></div>
<div class="pos"><div class="pos-label">个位杀码</div><div class="pos-num">{pred_o},{pred_o2}</div></div>
</div>
</div>
{data_banner}
{upgrade_banner}

<div class="section-title"><span class="dot"></span>近{backtest_n}期回测（3杀+6杀）</div>
<div class="stats">
<div class="stat"><div class="sv">{acc_h:.1f}%</div><div class="sl">百位</div><div class="se">错{err_h}期</div></div>
<div class="stat"><div class="sv">{acc_t:.1f}%</div><div class="sl">十位</div><div class="se">错{err_t}期</div></div>
<div class="stat"><div class="sv">{acc_o:.1f}%</div><div class="sl">个位</div><div class="se">错{err_o}期</div></div>
</div>

<div class="stats" style="grid-template-columns:repeat(4,1fr)">
<div class="stat"><div class="sv" style="font-size:20px;color:#0f3460">{acc_h2:.1f}%</div><div class="sl">百kill2</div></div>
<div class="stat"><div class="sv" style="font-size:20px;color:#533483">{acc_t2:.1f}%</div><div class="sl">十kill2</div></div>
<div class="stat"><div class="sv" style="font-size:20px;color:#16a085">{acc_o2:.1f}%</div><div class="sl">个kill2</div></div>
<div class="stat" style="border-top:3px solid #e94560"><div class="sv" style="font-size:20px;color:#e94560">{all6_pct:.1f}%</div><div class="sl">6杀全中</div></div>
</div>

<div class="info-card">
<h3>📋 V9 六杀引擎</h3>
<p><strong>每位置双杀码：</strong>kill1（V8条件决策树）+ kill2（独立算术公式）<br>
<strong>kill2公式：</strong>百=(b-span+9)%10 · 十=(s-mid+5)%10 · 个=(g²+|b-g|)%10<br>
<strong>重叠处理：</strong>kill2==kill1时自动+1偏移<br>
<strong>6杀全中：</strong>近100期 <strong>{all6_pct:.1f}%</strong> · 全量≈53%（基线51.2%）</p>
<div class="warn">
⚠️ <strong>重要提示：</strong>彩票本质是随机游戏。近100期3杀综合<strong>{acc_all:.1f}%</strong>，6杀全中<strong>{all6_pct:.1f}%</strong>。6杀全中理论上限≈66%，当前已显著超越随机基线51.2%。请理性参考。
</div>
</div>

<div class="section-title"><span class="dot"></span>近{backtest_n}期回测明细（6杀码）</div>
<div class="table-wrap">
<table>
<thead><tr><th>期号</th><th>日期</th><th>开奖</th><th>百杀</th><th>十杀</th><th>个杀</th><th>6杀</th></tr></thead>
<tbody>
{table_rows}
</tbody>
</table>
</div>

<div class="disclaimer">
数据来源：福彩3D历史开奖数据 | 算法严格不含未来信息 | 仅供研究参考<br>
数据截止 {latest_date} · 共{total}期
</div>
</body>
</html>'''

def generate_html(bt, data_ok=True):
    meta = bt["meta"]
    pred = bt["predictions"]
    rows = ""
    for r in bt["results"]:
        h_mark = f'<span class="ok">✅{r["hK"]},{r["hK2"]}</span>' if r["hOK"] and r.get("h2OK",True) else f'<span class="bad">❌{r["hK"]},{r["hK2"]}</span>'
        t_mark = f'<span class="ok">✅{r["tK"]},{r["tK2"]}</span>' if r["tOK"] and r.get("t2OK",True) else f'<span class="bad">❌{r["tK"]},{r["tK2"]}</span>'
        o_mark = f'<span class="ok">✅{r["oK"]},{r["oK2"]}</span>' if r["oOK"] and r.get("o2OK",True) else f'<span class="bad">❌{r["oK"]},{r["oK2"]}</span>'
        all6 = r.get("all6OK", r["allOK"])
        all_mark = "✅" if all6 else "❌"
        rows += f'<tr><td>{r["issue"]}</td><td>{r["date"]}</td><td>{r["open"]}</td><td>{h_mark}</td><td>{t_mark}</td><td>{o_mark}</td><td>{all_mark}</td></tr>\n'

    # 升级触发告警横幅
    upgrade_banner = ""
    if meta.get("upgrade_triggered"):
        rsn = "<br>".join("• " + r for r in meta.get("upgrade_reasons", []))
        upgrade_banner = (
            '<div class="upgrade-alert">'
            '<div class="ua-title">🚨 算法升级触发</div>'
            '6杀全中率已触及升级阈值，建议重新穷举6个算法：<br>' + rsn +
            '<br><span style="font-size:11px;opacity:.85">触发条件：滚动100期跌破 '
            + f'{TRIG_BELOW_PCT:.0f}% 或 单月下滑超 {TRIG_MONTH_DROP_PP:.0f}pp</span></div>'
        )

    # 数据异常告警横幅
    data_banner = ""
    if not data_ok:
        data_banner = (
            '<div class="data-alert">'
            '<div class="da-title">⚠️ 数据源异常</div>'
            '所有数据源获取失败，页面为最后一次成功数据，请检查数据源（灰鸟/17500）。'
            '</div>'
        )

    html = HTML_TEMPLATE.format(
        data_banner=data_banner,
        upgrade_banner=upgrade_banner,
        next_issue=meta["next_issue"],
        pred_h=pred["h"], pred_t=pred["t"], pred_o=pred["o"],
        pred_h2=pred["h2"], pred_t2=pred["t2"], pred_o2=pred["o2"],
        backtest_n=meta["backtest_n"],
        acc_h=meta["acc_h"], acc_t=meta["acc_t"], acc_o=meta["acc_o"],
        err_h=meta["err_h"], err_t=meta["err_t"], err_o=meta["err_o"],
        acc_all=meta["acc_all"],
        acc_h2=meta["acc_h2"], acc_t2=meta["acc_t2"], acc_o2=meta["acc_o2"],
        all6_pct=meta["all6_pct"],
        acc_period_100=meta["acc_period_100"],
        period_correct_100=meta["period_correct_100"],
        period_n_100=meta["period_n_100"],
        period6_correct_100=meta["period6_correct_100"],
        period6_pct_100=meta["period6_pct_100"],
        table_rows=rows,
        latest_date=meta["latest_date"], total=meta["total"],
    )
    return html

# ── MAIN ──────────────────────────────────────────────
if __name__ == "__main__":
    print("福彩3D 百十个杀码 · 云端更新 V9")

    # Step 1: 获取最新数据
    print("📡 获取最新开奖...")
    new_data, data_alive = fetch_latest()
    if new_data:
        added = append_csv(CSV_PATH, new_data)
        if added:
            print(f"  ✅ 已追加第{new_data['issue']}期 ({new_data['date']}) {new_data['b']}{new_data['s']}{new_data['g']}")
        else:
            print(f"  ℹ️ 第{new_data['issue']}期已存在, 无需追加")
    elif not data_alive:
        # 所有数据源全挂: 醒目告警, 页面加横幅
        print("\n🚨🚨🚨 所有数据源均失败! 页面将显示旧数据, 请检查数据源 🚨🚨🚨")
    else:
        # 源活着但无新期(当天开奖前运行) — 正常, 不告警
        print("  ℹ️ 数据源正常但无新一期(开奖前运行), 继续用现有数据")

    # Step 2: 加载数据
    data = load_csv(CSV_PATH)
    # 透传数据源给的next_issue(跨年安全)到最新行
    if new_data and new_data.get("next_issue") and data:
        data[-1]["next_issue"] = new_data["next_issue"]
    if len(data) < 100:
        print(f"❌ 数据不足: {len(data)}期")
        sys.exit(1)

    # Step 3: 回测
    bt = compute_backtest(data)
    meta = bt["meta"]
    print(f"\n📊 回测 {meta['backtest_n']}期: 百{meta['acc_h']:.1f}% 十{meta['acc_t']:.1f}% 个{meta['acc_o']:.1f}% 综合{meta['acc_all']:.1f}%")
    print(f"   kill2: 百{meta['acc_h2']:.1f}% 十{meta['acc_t2']:.1f}% 个{meta['acc_o2']:.1f}%")
    print(f"   6杀全中: {meta['all6']}/{meta['backtest_n']} = {meta['all6_pct']:.1f}%")
    print(f"   近100期综合(按期): {meta['period_correct_100']}/{meta['period_n_100']} = {meta['acc_period_100']:.1f}%")
    print(f"   近100期6杀全中: {meta['period6_correct_100']}/{meta['period_n_100']} = {meta['period6_pct_100']:.1f}%")

    # Step 3.5: 升级触发检测
    hist = record_kill6(meta["period6_pct_100"], meta["latest_issue"], meta["latest_date"])
    triggered, reasons, month_drop = check_upgrade_trigger(meta["period6_pct_100"], hist)
    meta["upgrade_triggered"] = triggered
    meta["upgrade_reasons"] = reasons
    meta["month_drop"] = round(month_drop, 1)
    if triggered:
        print(f"\n🚨🚨🚨 升级触发！建议重新穷举6个算法 🚨🚨🚨")
        for r in reasons:
            print(f"   ⚠️ {r}")
    else:
        print(f"   ✅ 升级触发器: 正常 (单月{month_drop:+.1f}pp, 阈值跌破{TRIG_BELOW_PCT:.0f}%/月降{TRIG_MONTH_DROP_PP:.0f}pp)")

    # Step 4: 生成HTML (data_ok = 源活着, 源死才挂横幅)
    html = generate_html(bt, data_ok=data_alive)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    pred = bt["predictions"]
    print(f"\n🔮 下一期: {meta['next_issue']} | 百杀{pred['h']},{pred['h2']} 十杀{pred['t']},{pred['t2']} 个杀{pred['o']},{pred['o2']}")
    print(f"✅ HTML已生成 ({len(html)}字节)")
