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

# ── V8 个位: 自适应故障切换 ──────────────────────────
