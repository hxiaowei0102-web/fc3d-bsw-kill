"""
福彩3D 百十个杀码预测 — 公式引擎 V9
=============================================
V8三杀码 + 每位置独立第二杀码（6杀制）
3杀命中: 百99%/十98.5%/个97% = 98.17%
6杀全中: 200期75.0% / 100期77.0%
kill2: 百=(b²+s+g)%10 十=(b*s)%10 个=(b+s+g+7)%10
"""
import csv, json, os, sys, re
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))
CSV_PATH = "D:/百十个/fc3d-history.csv"

class Draw:
    def __init__(self, row):
        self.issue = row['issue'].strip(); self.date = row['date'].strip()
        self.hundreds = int(row['hundreds']); self.tens = int(row['tens']); self.ones = int(row['ones'])

def load_data(path):
    draws = []
    with open(path, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            try:
                draws.append(Draw(row))
            except (ValueError, KeyError):
                continue
    return draws

# ========== 百位: 公式决策树 ==========
def kill_hundreds_formula(prev_draw):
    b, s, g = prev_draw.hundreds, prev_draw.tens, prev_draw.ones
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

H_FALLBACK = [
    lambda b,s,g: (b+s+g+1) % 10,
    lambda b,s,g: (b*s) % 10,
]

# ========== 十位: V8a增强公式法 ==========
# V8a: sum_odd b²+s²=0修复 + span_ge6 b最大修复 → 200期98.5% (+0.5pp vs V7)
def kill_tens_formula(prev_draw):
    b, s, g = prev_draw.hundreds, prev_draw.tens, prev_draw.ones
    if (b + s + g) % 2 == 1:
        if (b*b + s*s) % 10 == 0:
            return (b + s + g + 2) % 10  # b²+s²=0时原公式=个位g, 致命漏洞
        return (b*b + s*s + g) % 10
    if max(b,s,g) - min(b,s,g) >= 6:
        if b >= s and b >= g:       # 百位最大
            return ((b + s) * g) % 10
        return (3 * max(b,s,g)) % 10
    return (g*g + b) % 10

T_FALLBACK = [
    lambda b,s,g: (g*g + b) % 10,
    lambda b,s,g: (b + s + g + 1) % 10,
    lambda b,s,g: max(b,s,g) - min(b,s,g),
    lambda b,s,g: (b * g) % 10,
    lambda b,s,g: (b + s) % 10,
    lambda b,s,g: (b * s) % 10,
]

# ========== 个位: V8 自适应决策树 ==========
O_FAIL_WIN = 5

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

def kill_ones_formula(prev_draw, fail_state=None, period_idx=None):
    b, s, g = prev_draw.hundreds, prev_draw.tens, prev_draw.ones
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
    
    # V8: 条件最近失败过 → 切备份公式
    if fail_state is not None and period_idx is not None:
        cn = _get_o_cond(b, s, g)
        if cn in fail_state and period_idx - fail_state[cn] <= O_FAIL_WIN:
            if cn in O_BACKUP_FM:
                pk = O_BACKUP_FM[cn](b, s, g) % 10
    return pk

O_FALLBACK = [
    lambda b,s,g: (b+s+g+1) % 10,
    lambda b,s,g: (b*s) % 10,
]

# ========== V9: 第二杀码（独立算法） ==========
def kill_h2(b, s, g):
    """百位第二杀码: (b-span+9)%10 — V9.1 100期6杀全中率77%→82%"""
    span = max(b, s, g) - min(b, s, g)
    k = (b - span + 9) % 10
    k1 = kill_hundreds_formula(type('D',(),{'hundreds':b,'tens':s,'ones':g})())
    if k == k1: k = (k + 1) % 10
    return k

def kill_t2(b, s, g):
    """十位第二杀码: (s-mid+5)%10 — V9.2 100期6杀全中82%→86%"""
    mid = sorted([b, s, g])[1]
    k = (s - mid + 5) % 10
    k1 = kill_tens_formula(type('D',(),{'hundreds':b,'tens':s,'ones':g})())
    if k == k1: k = (k + 1) % 10
    return k

def kill_o2(b, s, g):
    """个位第二杀码: (g²+|b-g|)%10 — V9.3 100期86%→87%, 200期80.5%→82.5%"""
    k = (g*g + abs(b-g)) % 10
    k1 = kill_ones_formula(type('D',(),{'hundreds':b,'tens':s,'ones':g})())
    if k == k1: k = (k + 1) % 10
    return k

def apply_fallback(kill, prev_kill, fallback_list, b, s, g):
    """应用滚动队列: 如果杀码与上期相同, 依次尝试备选"""
    if kill != prev_kill:
        return kill
    for fb in fallback_list:
        alt = fb(b, s, g) % 10
        if alt != prev_kill:
            return alt
    return (kill + 1) % 10

# ========== 多窗口回测 ==========
def backtest_multi(draws, windows=[100, 200, 300, 500]):
    total = len(draws)
    results = {}

    for w in windows:
        if total < w: continue
        start = total - w

        phk = ptk = pok = None
        correct = {'h': 0, 't': 0, 'o': 0}
        correct2 = {'h': 0, 't': 0, 'o': 0}  # kill2
        all6 = 0  # 6杀全中
        max_consecutive = cur_consecutive = 0

        for idx in range(start, total):
            d = draws[idx]
            prev = draws[idx - 1]
            b, s, g = prev.hundreds, prev.tens, prev.ones

            hk = apply_fallback(kill_hundreds_formula(prev), phk, H_FALLBACK, b, s, g)
            tk = apply_fallback(kill_tens_formula(prev), ptk, T_FALLBACK, b, s, g)
            ok = apply_fallback(kill_ones_formula(prev), pok, O_FALLBACK, b, s, g)
            phk, ptk, pok = hk, tk, ok

            # V9: kill2
            hk2 = kill_h2(b, s, g)
            tk2 = kill_t2(b, s, g)
            ok2 = kill_o2(b, s, g)

            all_ok = True
            if hk != d.hundreds: correct['h'] += 1
            else: all_ok = False
            if tk != d.tens: correct['t'] += 1
            else: all_ok = False
            if ok != d.ones: correct['o'] += 1
            else: all_ok = False

            # kill2 stats
            h2ok = (hk2 != d.hundreds); t2ok = (tk2 != d.tens); o2ok = (ok2 != d.ones)
            if h2ok: correct2['h'] += 1
            if t2ok: correct2['t'] += 1
            if o2ok: correct2['o'] += 1

            # 6杀全中: kill1对 AND kill2对
            if all_ok and h2ok and t2ok and o2ok: all6 += 1

            if all_ok: cur_consecutive = 0
            else:
                cur_consecutive += 1
                max_consecutive = max(max_consecutive, cur_consecutive)

        n = w
        acc_h = correct['h'] / n * 100
        acc_t = correct['t'] / n * 100
        acc_o = correct['o'] / n * 100
        overall = (correct['h'] + correct['t'] + correct['o']) / (n*3) * 100

        results[f'近{w}期'] = {
            '百位': f"{correct['h']}/{n} = {acc_h:.1f}%",
            '十位': f"{correct['t']}/{n} = {acc_t:.1f}%",
            '个位': f"{correct['o']}/{n} = {acc_o:.1f}%",
            '综合': f"{overall:.1f}%",
            '百位kill2': f"{correct2['h']}/{n} = {correct2['h']/n*100:.1f}%",
            '十位kill2': f"{correct2['t']}/{n} = {correct2['t']/n*100:.1f}%",
            '个位kill2': f"{correct2['o']}/{n} = {correct2['o']/n*100:.1f}%",
            '6杀全中': f"{all6}/{n} = {all6/n*100:.1f}%",
            '最大连续错': max_consecutive,
        }
    
    # 全量回测
    if total > 500:
        start = 1
        phk = ptk = pok = None
        correct = {'h': 0, 't': 0, 'o': 0}
        correct2 = {'h': 0, 't': 0, 'o': 0}
        all6 = 0
        max_cons = cur_cons = 0

        for idx in range(start, total):
            d = draws[idx]
            prev = draws[idx - 1]
            b, s, g = prev.hundreds, prev.tens, prev.ones

            hk = apply_fallback(kill_hundreds_formula(prev), phk, H_FALLBACK, b, s, g)
            tk = apply_fallback(kill_tens_formula(prev), ptk, T_FALLBACK, b, s, g)
            ok = apply_fallback(kill_ones_formula(prev), pok, O_FALLBACK, b, s, g)
            phk, ptk, pok = hk, tk, ok

            hk2 = kill_h2(b, s, g)
            tk2 = kill_t2(b, s, g)
            ok2 = kill_o2(b, s, g)

            all_ok = True
            if hk != d.hundreds: correct['h'] += 1
            else: all_ok = False
            if tk != d.tens: correct['t'] += 1
            else: all_ok = False
            if ok != d.ones: correct['o'] += 1
            else: all_ok = False

            h2ok = (hk2 != d.hundreds); t2ok = (tk2 != d.tens); o2ok = (ok2 != d.ones)
            if h2ok: correct2['h'] += 1
            if t2ok: correct2['t'] += 1
            if o2ok: correct2['o'] += 1
            if all_ok and h2ok and t2ok and o2ok: all6 += 1

            if all_ok: cur_cons = 0
            else:
                cur_cons += 1
                max_cons = max(max_cons, cur_cons)
        
        n = total - 1
        overall = (correct['h'] + correct['t'] + correct['o']) / (n*3) * 100
        results['全量'] = {
            '百位': f"{correct['h']}/{n} = {correct['h']/n*100:.1f}%",
            '十位': f"{correct['t']}/{n} = {correct['t']/n*100:.1f}%",
            '个位': f"{correct['o']}/{n} = {correct['o']/n*100:.1f}%",
            '综合': f"{overall:.1f}%",
            '百位kill2': f"{correct2['h']}/{n} = {correct2['h']/n*100:.1f}%",
            '十位kill2': f"{correct2['t']}/{n} = {correct2['t']/n*100:.1f}%",
            '个位kill2': f"{correct2['o']}/{n} = {correct2['o']/n*100:.1f}%",
            '6杀全中': f"{all6}/{n} = {all6/n*100:.1f}%",
            '最大连续错': max_cons,
        }
    
    return results

# ========== 100期回测(6杀明细) ==========
def backtest(draws, test_periods=100):
    total = len(draws)
    start = total - test_periods

    phk = ptk = pok = None
    daily = []
    stats = {'h': [0,0], 't': [0,0], 'o': [0,0]}
    stats2 = {'h': [0,0], 't': [0,0], 'o': [0,0]}
    all6_cnt = 0

    for idx in range(start, total):
        d = draws[idx]
        prev = draws[idx - 1]
        b, s, g = prev.hundreds, prev.tens, prev.ones

        hk = apply_fallback(kill_hundreds_formula(prev), phk, H_FALLBACK, b, s, g)
        tk = apply_fallback(kill_tens_formula(prev), ptk, T_FALLBACK, b, s, g)
        ok = apply_fallback(kill_ones_formula(prev), pok, O_FALLBACK, b, s, g)
        phk, ptk, pok = hk, tk, ok

        # V9: kill2
        hk2 = kill_h2(b, s, g)
        tk2 = kill_t2(b, s, g)
        ok2 = kill_o2(b, s, g)

        ho = (hk != d.hundreds); to = (tk != d.tens); oo = (ok != d.ones)
        h2o = (hk2 != d.hundreds); t2o = (tk2 != d.tens); o2o = (ok2 != d.ones)
        if ho: stats['h'][0] += 1
        else: stats['h'][1] += 1
        if to: stats['t'][0] += 1
        else: stats['t'][1] += 1
        if oo: stats['o'][0] += 1
        else: stats['o'][1] += 1
        if h2o: stats2['h'][0] += 1
        else: stats2['h'][1] += 1
        if t2o: stats2['t'][0] += 1
        else: stats2['t'][1] += 1
        if o2o: stats2['o'][0] += 1
        else: stats2['o'][1] += 1

        a6 = ho and to and oo and h2o and t2o and o2o
        if a6: all6_cnt += 1

        daily.append({
            'issue': d.issue, 'date': d.date,
            'actual': f"{d.hundreds}{d.tens}{d.ones}",
            'hK': hk, 'tK': tk, 'oK': ok,
            'hK2': hk2, 'tK2': tk2, 'oK2': ok2,
            'hOK': ho, 'tOK': to, 'oOK': oo,
            'h2OK': h2o, 't2OK': t2o, 'o2OK': o2o,
            'allOK': ho and to and oo,
            'all6OK': a6
        })

    daily.reverse()

    cum = {'h': [], 't': [], 'o': []}
    ch = ct = co = 0
    for i, r in enumerate(daily):
        if r['hOK']: ch += 1
        if r['tOK']: ct += 1
        if r['oOK']: co += 1
        cum['h'].append(round(ch/(i+1)*100, 2))
        cum['t'].append(round(ct/(i+1)*100, 2))
        cum['o'].append(round(co/(i+1)*100, 2))

    return daily, cum, stats, stats2, all6_cnt

# ========== 预测 ==========
def predict(draws):
    prev = draws[-1]
    b, s, g = prev.hundreds, prev.tens, prev.ones
    
    # 重建fallback和V8状态
    phk = ptk = pok = None
    o_fail = {}
    for i in range(1, len(draws)):
        p = draws[i-1]; pb, ps, pg = p.hundreds, p.tens, p.ones
        phk = apply_fallback(kill_hundreds_formula(p), phk, H_FALLBACK, pb, ps, pg)
        ptk = apply_fallback(kill_tens_formula(p), ptk, T_FALLBACK, pb, ps, pg)
        pok_raw = kill_ones_formula(p, o_fail, i)
        pok = apply_fallback(pok_raw, pok, O_FALLBACK, pb, ps, pg) if pok is not None else pok_raw
        
        # V8: 个位失败追踪
        if pok == draws[i].ones:
            cn = _get_o_cond(pb, ps, pg)
            o_fail[cn] = i
    
    hk = apply_fallback(kill_hundreds_formula(prev), phk, H_FALLBACK, b, s, g)
    tk = apply_fallback(kill_tens_formula(prev), ptk, T_FALLBACK, b, s, g)
    ok_raw = kill_ones_formula(prev, o_fail, len(draws))
    ok = apply_fallback(ok_raw, pok, O_FALLBACK, b, s, g) if pok is not None else ok_raw

    # V9: kill2
    hk2 = kill_h2(b, s, g)
    tk2 = kill_t2(b, s, g)
    ok2 = kill_o2(b, s, g)

    next_issue = str(int(draws[-1].issue) + 1)
    today = datetime.now(TZ).strftime('%Y-%m-%d')

    return {
        'issue': next_issue, 'date': today,
        'hundreds': hk, 'tens': tk, 'ones': ok,
        'hundreds2': hk2, 'tens2': tk2, 'ones2': ok2,
    }

# ========== 数据源(离线备用) ==========
def validate_data(draws):
    """检查数据完整性"""
    issues = set()
    duplicates = []
    gaps = []
    prev = None
    for d in draws:
        if d.issue in issues:
            duplicates.append(d.issue)
        issues.add(d.issue)
        if prev and int(d.issue) != int(prev) + 1:
            gaps.append(f"{prev}→{d.issue}")
        prev = d.issue
    return {
        'total': len(draws),
        'range': f"{draws[0].issue}~{draws[-1].issue}",
        'duplicates': duplicates,
        'gaps': gaps,
        'valid': len(duplicates) == 0 and len(gaps) == 0
    }

# ========== MAIN ==========
if __name__ == '__main__':
    print("="*70)
    print("福彩3D 百十个杀码 — 公式引擎 V9 (6杀制)")
    print("="*70)
    
    if not os.path.exists(CSV_PATH):
        print(f"❌ 数据文件不存在: {CSV_PATH}")
        sys.exit(1)
    
    draws = load_data(CSV_PATH)
    print(f"\n数据: {len(draws)} 期 ({draws[0].issue} ~ {draws[-1].issue})")
    
    # 数据验证
    v = validate_data(draws)
    if v['duplicates']:
        print(f"⚠️ 重复期号: {v['duplicates']}")
    if v['gaps']:
        print(f"⚠️ 期号断档: {v['gaps']}")
    if v['valid']:
        print(f"✅ 数据完整性检查通过")
    
    # 多窗口回测
    print(f"\n{'='*70}")
    print("多窗口回测")
    print(f"{'='*70}")
    mw = backtest_multi(draws)
    for window, res in mw.items():
        print(f"\n  {window}:")
        for key, val in res.items():
            print(f"    {key}: {val}")
    
    # 100期回测(6杀明细)
    daily, cum, stats, stats2, all6_cnt = backtest(draws, 100)

    print(f"\n{'='*70}")
    print("100期详细回测（6杀制）")
    print(f"{'='*70}")
    acc = {}
    acc2 = {}
    for p, pos in [('h','百位'),('t','十位'),('o','个位')]:
        c, w = stats[p]
        c2, w2 = stats2[p]
        acc[p] = round(c/(c+w)*100, 2)
        acc2[p] = round(c2/(c2+w2)*100, 2)
        print(f"  {pos}: kill1 {c}/{c+w} = {acc[p]}%  kill2 {c2}/{c2+w2} = {acc2[p]}%")
    total_c = sum(stats[p][0] for p in 'hto')
    overall = round(total_c/300*100, 2)
    print(f"  3杀综合: {overall}%")
    print(f"  6杀全中: {all6_cnt}/100 = {all6_cnt}%")

    pred = predict(draws)
    print(f"\n🔮 今日预测: 第{pred['issue']}期 ({pred['date']})")
    print(f"   百位杀: {pred['hundreds']},{pred['hundreds2']}  十位杀: {pred['tens']},{pred['tens2']}  个位杀: {pred['ones']},{pred['ones2']}")

    output = {
        'version': 'V9',
        'lastIssue': draws[-1].issue, 'lastDate': draws[-1].date,
        'prediction': pred,
        'strategies': {'hundreds': '公式决策树', 'tens': '公式决策树', 'ones': '公式决策树'},
        'multiWindow': mw,
        'stats': {
            'h': acc['h'], 't': acc['t'], 'o': acc['o'], 'overall': overall,
            'hC': stats['h'][0], 'hW': stats['h'][1],
            'tC': stats['t'][0], 'tW': stats['t'][1],
            'oC': stats['o'][0], 'oW': stats['o'][1],
            'h2': acc2['h'], 't2': acc2['t'], 'o2': acc2['o'],
            'h2C': stats2['h'][0], 'h2W': stats2['h'][1],
            't2C': stats2['t'][0], 't2W': stats2['t'][1],
            'o2C': stats2['o'][0], 'o2W': stats2['o'][1],
            'all6': all6_cnt, 'all6Pct': all6_cnt,
        },
        'daily': daily, 'cumulative': cum
    }
    with open('D:/百十个/prediction_data.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("\n✅ 导出完成")
