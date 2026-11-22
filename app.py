import textwrap
import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="ETF 持股輪動 LAB", page_icon="📊", layout="wide")

def render_html(html_str: str):
    st.markdown(textwrap.dedent(html_str).strip(), unsafe_allow_html=True)

# 高對比儀表板樣式（手機淺色/深色模式皆清楚可讀）
render_html("""
<style>
    .block-container { padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1120px; }
    .lab-header {
        display: flex; flex-wrap: wrap; align-items: center; gap: 10px;
        margin-bottom: 0.5rem;
    }
    .lab-title { font-size: 1.55rem; font-weight: 800; letter-spacing: -0.5px; color: #F8FAFC; }
    .lab-sub { font-size: 0.95rem; color: #CBD5E1; border-left: 2px solid #64748B; padding-left: 10px; }
    .lab-badge {
        font-size: 0.78rem; font-weight: 700; padding: 2px 8px;
        border-radius: 6px; border: 1px solid #64748B; color: #E2E8F0; background: #1E293B;
    }
    .pool-card {
        background-color: #111827;
        color: #F8FAFC;
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 15px 14px 13px 14px;
        margin-bottom: 12px;
    }
    .pool-name {
        text-align: center; font-size: 1.12rem; font-weight: 700;
        color: #F8FAFC; margin-bottom: 3px;
    }
    .pool-sub {
        text-align: center; font-size: 0.77rem; color: #CBD5E1; margin-bottom: 6px;
        min-height: 2.1em;
    }
    .stat-line {
        display: flex; justify-content: space-between; align-items: center;
        font-size: 0.90rem; margin: 5px 0; color: #E2E8F0;
    }
    .stat-val { font-weight: 700; color: #FFFFFF; }
    .pp-pos { color: #4ADE80; font-weight: 700; }
    .pp-neg { color: #F87171; font-weight: 700; }
    .pp-zero { color: #CBD5E1; font-weight: 700; }
    .mix-box {
        margin-top: 9px; padding: 9px 10px;
        background: #0F172A; border: 1px solid #1E293B; border-radius: 10px;
    }
    .mix-title {
        font-size: 0.78rem; font-weight: 700; color: #E2E8F0; margin-bottom: 6px;
        display: flex; justify-content: space-between;
    }
    .mix-row-label {
        font-size: 0.73rem; color: #CBD5E1; margin-bottom: 3px;
        display: flex; justify-content: space-between;
    }
    .mix-bar {
        display: flex; height: 11px; width: 100%; border-radius: 6px;
        overflow: hidden; background: #1E293B; margin-bottom: 6px;
    }
    .bar-1x { background: #38BDF8; height: 100%; }
    .bar-2x { background: #F59E0B; height: 100%; }
    .bar-none { background: #334155; height: 100%; }
    .mix-legend {
        font-size: 0.72rem; color: #CBD5E1; line-height: 1.4; margin-top: 4px;
    }
    .dot-1x { display:inline-block; width:8px; height:8px; border-radius:50%; background:#38BDF8; margin-right:4px; }
    .dot-2x { display:inline-block; width:8px; height:8px; border-radius:50%; background:#F59E0B; margin-right:4px; }
    .z-block { margin-top: 9px; padding-top: 8px; border-top: 1px solid #1E293B; }
    .z-row {
        display: flex; align-items: center; justify-content: space-between;
        gap: 6px; font-size: 0.83rem; margin: 5px 0; color: #E2E8F0;
    }
    .z-track {
        position: relative; flex: 1; height: 6px; background: #334155;
        border-radius: 999px; margin: 0 4px;
    }
    .z-center {
        position: absolute; left: 50%; top: -3px; width: 2px; height: 12px;
        background: #94A3B8; transform: translateX(-50%);
    }
    .z-dot {
        position: absolute; top: 50%; width: 11px; height: 11px;
        border-radius: 50%; transform: translate(-50%, -50%);
        border: 1.5px solid #0F172A;
    }
    .summary-bar {
        display: flex; flex-direction: column; align-items: stretch;
        background-color: #111827; color: #F8FAFC;
        border: 1px solid #334155; border-radius: 14px;
        padding: 15px 18px; margin-top: 8px; gap: 10px;
    }
    .sum-top {
        display: flex; flex-wrap: wrap; justify-content: space-around;
        align-items: center; gap: 12px;
    }
    .sum-item { font-size: 1.02rem; font-weight: 700; color: #E2E8F0; }
    .sum-trim { color: #F87171; font-size: 1.22rem; font-weight: 800; }
    .sum-add  { color: #4ADE80; font-size: 1.22rem; font-weight: 800; }
    .sum-cash { color: #FFFFFF; font-size: 1.22rem; font-weight: 800; }
    .trigger-banner-on {
        background: rgba(239, 68, 68, 0.14); border: 1px solid #EF4444;
        color: #FECACA; padding: 9px 12px; border-radius: 10px;
        font-size: 0.90rem; font-weight: 700;
    }
    .trigger-banner-off {
        background: rgba(34, 197, 94, 0.12); border: 1px solid #22C55E;
        color: #BBF7D0; padding: 9px 12px; border-radius: 10px;
        font-size: 0.90rem; font-weight: 700;
    }
    .guide-box {
        font-size: 0.84rem; color: #CBD5E1; border-top: 1px solid #1E293B;
        padding-top: 9px; line-height: 1.6;
    }
</style>
""")

# 鎖定最佳化配置：45% 台股 / 45% 美股 / 10% 費半
POOL_TARGET = {"TW": 0.45, "US": 0.45, "SEMI": 0.10}

def calc_z_and_score(close_series, w_week, w_month):
    close = close_series.dropna().copy()
    close.index = close.index.tz_localize(None)
    latest_price = float(close.iloc[-1])
    latest_date = close.index[-1].strftime("%Y-%m-%d")

    weekly = close.resample("W-FRI").last().dropna().tail(20)
    z_20w = float((latest_price - weekly.mean()) / weekly.std(ddof=1))

    monthly = close.groupby(close.index.to_period("M")).last().dropna().tail(20)
    z_20m = float((latest_price - monthly.mean()) / monthly.std(ddof=1))

    score = w_week * z_20w + w_month * z_20m
    return latest_price, latest_date, z_20w, z_20m, score

@st.cache_data(ttl=600)
def fetch_market_data():
    def _fetch_pool(sym_1x, w_week, w_month, fallback_us=None):
        df = yf.Ticker(sym_1x).history(period="3y", auto_adjust=True)
        close = df["Close"].dropna()
        real_price = float(close.iloc[-1])
        real_date = close.index[-1].strftime("%Y-%m-%d")
        max_1d_chg = float(close.pct_change().abs().tail(10).max())
        is_anomaly = max_1d_chg > 0.15

        if is_anomaly and fallback_us:
            us_p = yf.Ticker(fallback_us).history(period="3y", auto_adjust=True)["Close"]
            fx = yf.Ticker("TWD=X").history(period="3y")["Close"]
            us_p.index = us_p.index.tz_localize(None).normalize()
            fx.index = fx.index.tz_localize(None).normalize()
            synth_twd = (us_p * fx.reindex(us_p.index).ffill()).dropna()
            _, _, z_20w, z_20m, score = calc_z_and_score(synth_twd, w_week, w_month)
            return {
                "price": real_price, "date": real_date, "z_20w": z_20w, "z_20m": z_20m,
                "score": score, "is_locked": False, "used_fallback": True,
                "max_1d_chg": max_1d_chg, "fallback_name": fallback_us
            }

        _, _, z_20w, z_20m, score = calc_z_and_score(close, w_week, w_month)
        return {
            "price": real_price, "date": real_date, "z_20w": z_20w, "z_20m": z_20m,
            "score": score, "is_locked": is_anomaly, "used_fallback": False,
            "max_1d_chg": max_1d_chg, "fallback_name": None
        }

    def _latest(ticker):
        return float(yf.Ticker(ticker).history(period="5d", auto_adjust=True)["Close"].dropna().iloc[-1])

    return {
        "TW": _fetch_pool("0050.TW", 0.65, 0.35),
        "US": _fetch_pool("00662.TW", 0.50, 0.50, fallback_us="QQQ"),
        "SEMI": _fetch_pool("00830.TW", 0.50, 0.50, fallback_us="^SOX"),
        "p_631": _latest("00631L.TW"),
        "p_670": _latest("00670L.TW"),
    }

def get_target_2x_ratio(score, z_20w):
    if score >= 2.4:
        return 0.50, "極度過熱降溫 (目標 1.5x)"
    elif score >= 0.4:
        if z_20w < -1.0:
            return 0.50, "多頭急殺煞車 (目標 1.5x)"
        return 1.00, "強勢多頭主升段 (目標 2.0x)"
    elif score <= -0.4:
        if z_20w > 0.2:
            return 0.50, "底部週線V轉反攻 (目標 1.5x)"
        return 0.00, "空頭主跌防禦區 (目標 1.0x)"
    else:
        return 0.50, "多空緩衝過渡區 (目標 1.5x)"

def gauge_svg(pct_0_to_100, color="#34D399"):
    pct = max(0.0, min(100.0, pct_0_to_100))
    arc_len = 157.08
    dash = (pct / 100.0) * arc_len
    return (
        f'<svg viewBox="0 0 140 76" style="width:100%;max-height:86px;display:block;margin:0 auto;">'
        f'<path d="M 20 66 A 50 50 0 0 1 120 66" fill="none" stroke="#334155" stroke-width="11" stroke-linecap="round"/>'
        f'<path d="M 20 66 A 50 50 0 0 1 120 66" fill="none" stroke="{color}" stroke-width="11" stroke-linecap="round" stroke-dasharray="{dash:.1f} {arc_len:.1f}"/>'
        f'<text x="70" y="52" text-anchor="middle" fill="#FFFFFF" font-size="22" font-weight="800">{pct:.1f}%</text>'
        f'<text x="20" y="74" text-anchor="middle" fill="#94A3B8" font-size="9">0%</text>'
        f'<text x="120" y="74" text-anchor="middle" fill="#94A3B8" font-size="9">100%</text>'
        f'</svg>'
    )

def mix_visual_html(header_text, cur_1x_pct, cur_2x_pct, tgt_1x_pct, tgt_2x_pct, note_text):
    c1 = max(0.0, min(100.0, cur_1x_pct))
    c2 = max(0.0, min(100.0 - c1, cur_2x_pct))
    cn = max(0.0, 100.0 - c1 - c2)

    t1 = max(0.0, min(100.0, tgt_1x_pct))
    t2 = max(0.0, min(100.0 - t1, tgt_2x_pct))
    tn = max(0.0, 100.0 - t1 - t2)

    return (
        f'<div class="mix-box">'
        f'<div class="mix-title"><span>{header_text}</span></div>'
        f'<div class="mix-row-label"><span>現況</span><span>原型 {c1:.0f}% / 正二 {c2:.0f}%</span></div>'
        f'<div class="mix-bar">'
        f'<div class="bar-1x" style="width:{c1:.1f}%;"></div>'
        f'<div class="bar-2x" style="width:{c2:.1f}%;"></div>'
        f'<div class="bar-none" style="width:{cn:.1f}%;"></div>'
        f'</div>'
        f'<div class="mix-row-label"><span>目標</span><span>原型 {t1:.0f}% / 正二 {t2:.0f}%</span></div>'
        f'<div class="mix-bar">'
        f'<div class="bar-1x" style="width:{t1:.1f}%;"></div>'
        f'<div class="bar-2x" style="width:{t2:.1f}%;"></div>'
        f'<div class="bar-none" style="width:{tn:.1f}%;"></div>'
        f'</div>'
        f'<div class="mix-legend">'
        f'<span class="dot-1x"></span>原型 ETF &nbsp;&nbsp;'
        f'<span class="dot-2x"></span>槓桿型 (2x)<br>'
        f'{note_text}'
        f'</div>'
        f'</div>'
    )

def z_slider_html(label, z_val):
    pos = max(0.0, min(100.0, (z_val + 3.0) / 6.0 * 100.0))
    if z_val >= 1.5:
        c, z_cls = "#F87171", "pp-neg"
    elif z_val >= 0.4:
        c, z_cls = "#34D399", "pp-pos"
    elif z_val <= -1.0:
        c, z_cls = "#60A5FA", "pp-pos"
    else:
        c, z_cls = "#FBBF24", "pp-zero"
    return (
        f'<div class="z-row">'
        f'<span style="min-width:38px;">{label}</span>'
        f'<span style="font-size:0.74rem;color:#94A3B8;">-3σ</span>'
        f'<div class="z-track"><div class="z-center"></div><div class="z-dot" style="left:{pos:.1f}%;background:{c};"></div></div>'
        f'<span style="font-size:0.74rem;color:#94A3B8;">+3σ</span>'
        f'<span class="{z_cls}" style="min-width:52px;text-align:right;">{z_val:+.2f}σ</span>'
        f'</div>'
    )

def fmt_pp(diff_pp):
    if abs(diff_pp) < 0.05:
        return '<span class="pp-zero">0.0 pp</span>'
    if diff_pp > 0:
        return f'<span class="pp-pos">+{diff_pp:.1f} pp</span>'
    return f'<span class="pp-neg">{diff_pp:.1f} pp</span>'

# ================= 頂部標題列 =================
col_t, col_b = st.columns([4, 1])
with col_t:
    render_html("""
    <div class="lab-header">
        <span class="lab-title">ETF 持股輪動 LAB</span>
        <span class="lab-sub">20 週／20 月位階</span>
        <span class="lab-badge">45 / 45 / 10 積極檔</span>
    </div>
    """)
with col_b:
    if st.button("🔄 更新報價", use_container_width=True):
        st.cache_data.clear()

with st.spinner("正在抓取五檔最新還原權息報價..."):
    data = fetch_market_data()

# ================= 持股與資金輸入區 =================
with st.expander("📝 輸入／修改目前持股與資金（預設為範例數據，可依實際庫存調整）", expanded=False):
    c1, c2, c3, c4 = st.columns(4)
    s_0050 = c1.number_input("0050 股數", min_value=0, value=1000, step=100)
    s_631  = c2.number_input("00631L 股數", min_value=0, value=1000, step=100)
    s_662  = c3.number_input("00662 股數", min_value=0, value=2000, step=100)
    s_670  = c4.number_input("00670L 股數", min_value=0, value=500, step=100)
    c5, c6, c7, c8 = st.columns(4)
    s_830    = c5.number_input("00830 股數", min_value=0, value=1000, step=100)
    cash_bal = c6.number_input("可用／新投入資金 (元)", min_value=0, value=20000, step=1000)
    ext_debt = c7.number_input("外部借款 (元)", min_value=0, value=0, step=10000)
    _        = c8.empty()

# ================= 計算各池現況與建議配置 =================
tw_p1, tw_p2 = data["TW"]["price"], data["p_631"]
us_p1, us_p2 = data["US"]["price"], data["p_670"]
se_p1        = data["SEMI"]["price"]

tw_v1, tw_v2 = s_0050 * tw_p1, s_631 * tw_p2
us_v1, us_v2 = s_662 * us_p1, s_670 * us_p2
se_v1        = s_830 * se_p1

invest_tot = tw_v1 + tw_v2 + us_v1 + us_v2 + se_v1
grand_tot  = invest_tot + cash_bal
cash_pct   = (cash_bal / grand_tot * 100.0) if grand_tot > 0 else 0.0

tw_cur_pct   = ((tw_v1 + tw_v2) / grand_tot * 100.0) if grand_tot > 0 else 0.0
us_cur_pct   = ((us_v1 + us_v2) / grand_tot * 100.0) if grand_tot > 0 else 0.0
semi_cur_pct = (se_v1 / grand_tot * 100.0) if grand_tot > 0 else 0.0

tw_sug_pct   = POOL_TARGET["TW"] * 100.0
us_sug_pct   = POOL_TARGET["US"] * 100.0
semi_sug_pct = POOL_TARGET["SEMI"] * 100.0

tw_2x_target, tw_status = get_target_2x_ratio(data["TW"]["score"], data["TW"]["z_20w"])
us_2x_target, us_status = get_target_2x_ratio(data["US"]["score"], data["US"]["z_20w"])

# 池內原型 vs. 正二比例
tw_pool_tot = max(1.0, tw_v1 + tw_v2)
tw_c2_in = (tw_v2 / tw_pool_tot) * 100.0
tw_c1_in = 100.0 - tw_c2_in
tw_t2_in = tw_2x_target * 100.0
tw_t1_in = 100.0 - tw_t2_in

us_pool_tot = max(1.0, us_v1 + us_v2)
us_c2_in = (us_v2 / us_pool_tot) * 100.0
us_c1_in = 100.0 - us_c2_in
us_t2_in = us_2x_target * 100.0
us_t1_in = 100.0 - us_t2_in

# 全組合原型 vs. 槓桿型（2x）占比
tot_1x_val = tw_v1 + us_v1 + se_v1
tot_2x_val = tw_v2 + us_v2
all_c1_pct = (tot_1x_val / grand_tot * 100.0) if grand_tot > 0 else 0.0
all_c2_pct = (tot_2x_val / grand_tot * 100.0) if grand_tot > 0 else 0.0

all_t2_pct = (POOL_TARGET["TW"] * tw_2x_target + POOL_TARGET["US"] * us_2x_target) * 100.0
all_t1_pct = max(0.0, 100.0 - cash_pct - all_t2_pct)

# 總曝險（原型市值 + 正二市值 * 2）÷ 扣除外部借款後淨資產
total_exp = (tw_v1 + us_v1 + se_v1) + 2.0 * (tw_v2 + us_v2)
net_asset = max(1.0, grand_tot - ext_debt)
real_lev  = total_exp / net_asset

# ================= 四張儀表板卡片 =================
cards = [
    {
        "title": "台股核心池",
        "sub": f"0050 ({tw_p1:.2f}) / 00631L ({tw_p2:.2f}) · S={data['TW']['score']:+.2f}",
        "cur": tw_cur_pct, "sug": tw_sug_pct,
        "zw": data["TW"]["z_20w"], "zm": data["TW"]["z_20m"],
        "color": "#34D399" if abs(tw_cur_pct - tw_sug_pct) <= 10 else "#FBBF24",
        "mix": mix_visual_html(
            "池內 原型 vs. 正二",
            tw_c1_in, tw_c2_in, tw_t1_in, tw_t2_in,
            f"正二調整：{tw_c2_in:.1f}% → <b>{tw_t2_in:.0f}%</b>（差 {tw_t2_in - tw_c2_in:+.1f} pp）"
        )
    },
    {
        "title": "美股核心池",
        "sub": f"00662 ({us_p1:.2f}) / 00670L ({us_p2:.2f}) · S={data['US']['score']:+.2f}",
        "cur": us_cur_pct, "sug": us_sug_pct,
        "zw": data["US"]["z_20w"], "zm": data["US"]["z_20m"],
        "color": "#60A5FA" if data["US"]["used_fallback"] else "#34D399",
        "mix": mix_visual_html(
            "池內 原型 vs. 正二",
            us_c1_in, us_c2_in, us_t1_in, us_t2_in,
            f"正二調整：{us_c2_in:.1f}% → <b>{us_t2_in:.0f}%</b>（差 {us_t2_in - us_c2_in:+.1f} pp）"
        )
    },
    {
        "title": "費半衛星池",
        "sub": f"00830 ({se_p1:.2f}) · S={data['SEMI']['score']:+.2f}",
        "cur": semi_cur_pct, "sug": semi_sug_pct,
        "zw": data["SEMI"]["z_20w"], "zm": data["SEMI"]["z_20m"],
        "color": "#34D399" if abs(semi_cur_pct - semi_sug_pct) <= 10 else "#F87171",
        "mix": mix_visual_html(
            "衛星池 結構（純 1x）",
            100.0 if se_v1 > 0 else 0.0, 0.0, 100.0, 0.0,
            "00830 維持 <b>1x 原型</b>，作動能溫度計"
        )
    },
    {
        "title": "全組合 原型/正二",
        "sub": f"總市值 NT$ {grand_tot:,.0f} · 真實槓桿 {real_lev:.2f}x",
        "cur": min(100.0, (real_lev / 2.5) * 100.0), "sug": 68.0,
        "zw": data["TW"]["score"], "zm": data["US"]["score"],
        "color": "#34D399" if real_lev <= 2.0 else "#F87171",
        "mix": mix_visual_html(
            "全組合 原型 vs. 正二",
            all_c1_pct, all_c2_pct, all_t1_pct, all_t2_pct,
            f"正二全組合：{all_c2_pct:.1f}% → <b>{all_t2_pct:.1f}%</b>"
        )
    }
]

cols = st.columns(4)
for idx, c in enumerate(cards):
    diff_pp = c["sug"] - c["cur"]
    card_html = (
        f'<div class="pool-card">'
        f'<div class="pool-name">{c["title"]}</div>'
        f'<div class="pool-sub">{c["sub"]}</div>'
        f'{gauge_svg(c["cur"], c["color"])}'
        f'<div class="stat-line"><span>目前持有</span><span class="stat-val">{c["cur"]:.1f}%</span></div>'
        f'<div class="stat-line"><span>建議配置</span><span><strong class="stat-val">{c["sug"]:.1f}%</strong> &nbsp;{fmt_pp(diff_pp)}</span></div>'
        f'{c["mix"]}'
        f'<div class="z-block">'
        f'{z_slider_html("20 週", c["zw"])}'
        f'{z_slider_html("20 月", c["zm"])}'
        f'</div>'
        f'</div>'
    )
    with cols[idx]:
        render_html(card_html)

# ================= 底部白話摘要列 ＋ 自動判斷「何時真正觸發調整」 =================
diffs = [tw_sug_pct - tw_cur_pct, us_sug_pct - us_cur_pct, semi_sug_pct - semi_cur_pct]
add_pp  = sum(max(0.0, d) for d in diffs)
trim_pp = sum(max(0.0, -d) for d in diffs)

pool_map = [
    ("台股核心池", tw_cur_pct, tw_sug_pct),
    ("美股核心池", us_cur_pct, us_sug_pct),
    ("費半衛星池", semi_cur_pct, semi_sug_pct),
]
over_pools  = [f"{n}（超標 {c - s:.1f}%）" for n, c, s in pool_map if c - s > 0.5]
under_pools = [f"{n}（落後 {s - c:.1f}%）" for n, c, s in pool_map if s - c > 0.5]
over_text   = "、".join(over_pools) if over_pools else "目前無明顯超標池"
under_text  = "、".join(under_pools) if under_pools else "目前無明顯落後池"

# 檢查兩大觸發調整條件（偏離 > 10% 才算真正觸發）
triggered_reasons = []
if abs(tw_c2_in - tw_t2_in) > 10.0 and (tw_v1 + tw_v2) > 0:
    triggered_reasons.append(f"台股池正二偏離 {abs(tw_c2_in - tw_t2_in):.1f}%（>10%）")
if abs(us_c2_in - us_t2_in) > 10.0 and (us_v1 + us_v2) > 0:
    triggered_reasons.append(f"美股池正二偏離 {abs(us_c2_in - us_t2_in):.1f}%（>10%）")
for n, c, s in pool_map:
    if abs(c - s) > 10.0 and invest_tot > 0:
        triggered_reasons.append(f"{n}整體占比偏離 {abs(c - s):.1f}%（>10%）")

if triggered_reasons:
    status_banner = (
        f'<div class="trigger-banner-on">'
        f'🔔 【今日狀態：已觸發調整條件】{" ｜ ".join(triggered_reasons)} → 請依下方股數清單執行再平衡。'
        f'</div>'
    )
else:
    status_banner = (
        f'<div class="trigger-banner-off">'
        f'🟢 【今日狀態：未觸發調整條件】所有池內正二與整體占比偏離皆在 10% 容許範圍內 → 不需換股，安心蓋牌過生活！'
        f'</div>'
    )

render_html(f"""
<div class="summary-bar">
    <div class="sum-top">
        <div class="sum-item">比例超標合計 <span class="sum-trim">{trim_pp:.1f}%</span></div>
        <div class="sum-item">|</div>
        <div class="sum-item">比例落後合計 <span class="sum-add">{add_pp:.1f}%</span></div>
        <div class="sum-item">|</div>
        <div class="sum-item">可用現金占比 <span class="sum-cash">{cash_pct:.1f}%</span></div>
    </div>
    {status_banner}
    <div class="guide-box">
        <div>📉 <b>高於目標（偏重）</b>：{over_text}</div>
        <div>📈 <b>低於目標（可補）</b>：{under_text}</div>
        <div style="margin-top:6px; color:#E2E8F0;"><b>📌 何時才算「真正觸發調整」？（兩大硬門檻，未達標不動手）</b></div>
        <div>1️⃣ <b>條件一（池內槓桿輪動）</b>：台股或美股池的「正二實際占比」與「目標正二占比」差距<b>超過 10%</b>（例如目標 0%、現況 20.1%，偏離 20.1% &gt; 10%），才執行原型與正二互換。</div>
        <div>2️⃣ <b>條件二（三大池比例失衡）</b>：台股(45%) / 美股(45%) / 費半(10%) 任一池占總資產比例與目標差距<b>超過 10%</b>；未達 10% 前，<b>只用新資金／可用現金優先買進「低於目標」的池子</b>即可，不必賣股。</div>
        <div style="color:#94A3B8; margin-top:4px;">
            💡 <b>紀律提醒</b>：照事前訂好的條件執行、不猜高低點；調整完畢就安心蓋牌過生活，並確保生活緊急預備金與投資／槓桿資金分開。
        </div>
    </div>
</div>
""")

# ================= 精確買賣股數執行清單 =================
with st.expander("📋 查看精確買賣股數建議（偏離 >10% 觸發再平衡）", expanded=True):
    def _pool_action(name, s1, p1, v1, s2, p2, v2, t2x):
        ptot = v1 + v2
        cur2 = (v2 / ptot) if ptot > 0 else 0.0
        dev = abs(cur2 - t2x)
        if dev > 0.10 and ptot > 0:
            ds1 = int((ptot * (1 - t2x) - v1) // p1)
            ds2 = int((ptot * t2x - v2) // p2)
            a1 = f"買進 {ds1:,} 股" if ds1 >= 0 else f"賣出 {abs(ds1):,} 股"
            a2 = f"買進 {ds2:,} 股" if ds2 >= 0 else f"賣出 {abs(ds2):,} 股"
            st.error(f"🔔 **{name}（偏離 {dev*100:.1f}% > 10%）**：原型 {a1} ｜ 正二 {a2}")
        else:
            st.success(f"✅ **{name}（偏離 {dev*100:.1f}% ≤ 10%）**：維持現狀不需換股")

    _pool_action("台股核心池 (0050/00631L)", s_0050, tw_p1, tw_v1, s_631, tw_p2, tw_v2, tw_2x_target)
    _pool_action("美股核心池 (00662/00670L)", s_662, us_p1, us_v1, s_670, us_p2, us_v2, us_2x_target)
    st.info(f"⚡ **費半衛星池 (00830)**：現價 {se_p1:.2f}，目前占比 {semi_cur_pct:.1f}%（目標 {semi_sug_pct:.1f}%），綜合積分 S = {data['SEMI']['score']:+.2f}")

st.caption("🛡️ 紀律提醒：條件觸發照表操課、不猜低點；調整完畢即可安心蓋牌過生活，並確保緊急預備金與投資資金獨立切分。")
