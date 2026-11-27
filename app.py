import textwrap
import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="ETF 持股輪動 LAB", page_icon="📊", layout="wide")

def render_html(html_str: str):
    st.markdown(textwrap.dedent(html_str).strip(), unsafe_allow_html=True)

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

POOL_TARGET = {"TW": 0.45, "US": 0.45, "SEMI": 0.10}
MAX_STEP = 0.10  # 每次調整變化上限 10%，降低執行心理壓力並增加試錯餘裕

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

def get_raw_target_2x(score, z_20w):
    if pd.isna(score) or pd.isna(z_20w):
        return 0.50, "資料暖機區 (理想 1.5x)"
    if score >= 2.4:
        return 0.50, "極度過熱降溫 (理想 1.5x)"
    elif score >= 0.4:
        if z_20w < -1.0:
            return 0.50, "多頭急殺煞車 (理想 1.5x)"
        return 1.00, "強勢多頭主升段 (理想 2.0x)"
    elif score <= -0.4:
        if z_20w > 0.2:
            return 0.50, "底部週線V轉反攻 (理想 1.5x)"
        return 0.00, "空頭主跌防禦區 (理想 1.0x)"
    else:
        return 0.50, "多空緩衝過渡區 (理想 1.5x)"

def apply_step_cap(raw_targets, max_step=0.10):
    """每次目標變化上限 10%（漸進式分批調整，避免一次大幅換倉的心理壓力）"""
    stepped = []
    cur = None
    for raw in raw_targets:
        if cur is None:
            cur = float(raw)
        else:
            diff = float(raw) - cur
            if abs(diff) <= max_step + 1e-9:
                cur = float(raw)
            else:
                cur = round(cur + np.sign(diff) * max_step, 2)
        stepped.append(cur)
    return stepped

def build_5y_weekly_turns(ticker, w_week, w_month, is_leveraged_pool=True):
    # 抓取 7 年日線資料，確保 5 年前起點已具備完整 20 週與 20 月統計暖機
    hist = yf.Ticker(ticker).history(period="7y", auto_adjust=True)["Close"].dropna()
    hist.index = hist.index.tz_localize(None)
    w_s = hist.resample("W-FRI").last().dropna()
    m_s = hist.resample("ME").last().dropna()

    w_df = pd.DataFrame({"px": w_s})
    w_df["ma20w"] = w_df["px"].rolling(20).mean()
    w_df["z20w"] = (w_df["px"] - w_df["ma20w"]) / w_df["px"].rolling(20).std(ddof=1)
    m_z20 = (m_s - m_s.rolling(20, min_periods=6).mean()) / m_s.rolling(20, min_periods=6).std(ddof=1)
    w_df["z20m"] = m_z20.reindex(w_df.index, method="ffill")
    w_df["score"] = w_week * w_df["z20w"] + w_month * w_df["z20m"]

    if is_leveraged_pool:
        raw_list = [get_raw_target_2x(s, zw)[0] for s, zw in zip(w_df["score"], w_df["z20w"])]
        w_df["raw_t2x"] = raw_list
        w_df["t2x"] = apply_step_cap(raw_list, MAX_STEP)
    else:
        # 費半 00830 為 1x 原型動能溫度計，同樣套用單次最多調整 10% 檔位步進
        raw_list = [0.5 if s >= 2.4 else (0.0 if s <= -0.4 else 1.0) for s in w_df["score"]]
        w_df["raw_t2x"] = raw_list
        w_df["t2x"] = apply_step_cap(raw_list, MAX_STEP)

    cutoff = w_df.index[-1] - pd.Timedelta(days=365 * 5)
    w_5y = w_df[w_df.index >= cutoff].copy()
    w_5y["prev_t2x"] = w_5y["t2x"].shift(1)
    turns = w_5y[(w_5y["prev_t2x"].notna()) & ((w_5y["t2x"] - w_5y["prev_t2x"]).abs() > 1e-6)].copy()

    latest_dt = w_5y.index[-1]
    latest_px = float(w_5y["px"].iloc[-1])
    cum_rets, ann_rets = [], []
    for dt, r in turns.iterrows():
        days = max(1, (latest_dt - dt).days)
        p0 = float(r["px"])
        cum_r = (latest_px / p0 - 1.0) * 100.0
        cum_rets.append(f"{cum_r:+.1f}%")
        if days >= 21 and p0 > 0 and latest_px > 0:
            cagr = ((latest_px / p0) ** (365.25 / days) - 1.0) * 100.0
            ann_rets.append(f"{cagr:+.1f}% (年化)")
        else:
            ann_rets.append("未滿3週（看累積）")

    turns["cum_ret"] = cum_rets
    turns["ann_ret"] = ann_rets
    return w_5y, turns

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

    qqq_5y, qqq_turns = build_5y_weekly_turns("QQQ", 0.50, 0.50, is_leveraged_pool=True)
    tw_5y, tw_turns   = build_5y_weekly_turns("0050.TW", 0.65, 0.35, is_leveraged_pool=True)
    se_5y, se_turns   = build_5y_weekly_turns("00830.TW", 0.50, 0.50, is_leveraged_pool=False)

    return {
        "TW": _fetch_pool("0050.TW", 0.65, 0.35),
        "US": _fetch_pool("00662.TW", 0.50, 0.50, fallback_us="QQQ"),
        "SEMI": _fetch_pool("00830.TW", 0.50, 0.50, fallback_us="^SOX"),
        "p_631": _latest("00631L.TW"),
        "p_670": _latest("00670L.TW"),
        "turns_map": {
            "美股 QQQ (對應 00662/00670L)": ("QQQ", qqq_5y, qqq_turns, "USD", True),
            "台股 0050 (對應 0050/00631L)": ("0050.TW", tw_5y, tw_turns, "TWD", True),
            "費半 00830 (原型動能)": ("00830.TW", se_5y, se_turns, "TWD", False),
        }
    }

def step_toward(current_ratio, ideal_ratio, max_step=0.10):
    """計算本週單次上限 10% 的漸進調整目標"""
    diff = ideal_ratio - current_ratio
    if abs(diff) <= max_step + 1e-9:
        return round(ideal_ratio, 4)
    return round(current_ratio + np.sign(diff) * max_step, 4)

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
        f'<div class="mix-row-label"><span>本週目標（上限±10%）</span><span>原型 {t1:.0f}% / 正二 {t2:.0f}%</span></div>'
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

col_t, col_b = st.columns([4, 1])
with col_t:
    render_html("""
    <div class="lab-header">
        <span class="lab-title">ETF 持股輪動 LAB</span>
        <span class="lab-sub">20 週／20 月位階 · 單次上限 ±10%</span>
        <span class="lab-badge">45 / 45 / 10 積極檔</span>
    </div>
    """)
with col_b:
    if st.button("🔄 更新報價", use_container_width=True):
        st.cache_data.clear()

with st.spinner("正在抓取五檔最新還原權息報價與近五年周線轉折..."):
    data = fetch_market_data()

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

# 理想目標 vs. 本週漸進目標（每次變化上限 10%）
tw_ideal_2x, tw_status = get_raw_target_2x(data["TW"]["score"], data["TW"]["z_20w"])
us_ideal_2x, us_status = get_raw_target_2x(data["US"]["score"], data["US"]["z_20w"])

tw_pool_tot = max(1.0, tw_v1 + tw_v2)
tw_cur_2x_ratio = (tw_v2 / tw_pool_tot) if (tw_v1 + tw_v2) > 0 else 0.0
tw_step_2x = step_toward(tw_cur_2x_ratio, tw_ideal_2x, MAX_STEP)

tw_c2_in = tw_cur_2x_ratio * 100.0
tw_c1_in = 100.0 - tw_c2_in
tw_t2_in = tw_step_2x * 100.0
tw_t1_in = 100.0 - tw_t2_in

us_pool_tot = max(1.0, us_v1 + us_v2)
us_cur_2x_ratio = (us_v2 / us_pool_tot) if (us_v1 + us_v2) > 0 else 0.0
us_step_2x = step_toward(us_cur_2x_ratio, us_ideal_2x, MAX_STEP)

us_c2_in = us_cur_2x_ratio * 100.0
us_c1_in = 100.0 - us_c2_in
us_t2_in = us_step_2x * 100.0
us_t1_in = 100.0 - us_t2_in

tot_1x_val = tw_v1 + us_v1 + se_v1
tot_2x_val = tw_v2 + us_v2
all_c1_pct = (tot_1x_val / grand_tot * 100.0) if grand_tot > 0 else 0.0
all_c2_pct = (tot_2x_val / grand_tot * 100.0) if grand_tot > 0 else 0.0

all_t2_pct = (POOL_TARGET["TW"] * tw_step_2x + POOL_TARGET["US"] * us_step_2x) * 100.0
all_t1_pct = max(0.0, 100.0 - cash_pct - all_t2_pct)

total_exp = (tw_v1 + us_v1 + se_v1) + 2.0 * (tw_v2 + us_v2)
net_asset = max(1.0, grand_tot - ext_debt)
real_lev  = total_exp / net_asset

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
            f"本週步進：{tw_c2_in:.1f}% → <b>{tw_t2_in:.1f}%</b>（終極理想 {tw_ideal_2x*100:.0f}%）"
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
            f"本週步進：{us_c2_in:.1f}% → <b>{us_t2_in:.1f}%</b>（終極理想 {us_ideal_2x*100:.0f}%）"
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
            f"本週全組合正二：{all_c2_pct:.1f}% → <b>{all_t2_pct:.1f}%</b>"
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

triggered_reasons = []
if abs(tw_cur_2x_ratio - tw_ideal_2x) > 0.01 and (tw_v1 + tw_v2) > 0:
    triggered_reasons.append(f"台股正二距離理想目標差 {abs(tw_c2_in - tw_ideal_2x*100):.1f}%（本週漸進調 ±10%）")
if abs(us_cur_2x_ratio - us_ideal_2x) > 0.01 and (us_v1 + us_v2) > 0:
    triggered_reasons.append(f"美股正二距離理想目標差 {abs(us_c2_in - us_ideal_2x*100):.1f}%（本週漸進調 ±10%）")
for n, c, s in pool_map:
    if abs(c - s) > 10.0 and invest_tot > 0:
        triggered_reasons.append(f"{n}整體占比偏離 {abs(c - s):.1f}%（>10%）")

if triggered_reasons:
    status_banner = (
        f'<div class="trigger-banner-on">'
        f'🔔 【今日狀態：啟動漸進式調整（單次上限 ±10%）】{" ｜ ".join(triggered_reasons)}'
        f'</div>'
    )
else:
    status_banner = (
        f'<div class="trigger-banner-off">'
        f'🟢 【今日狀態：已貼合目標配置】所有池內正二與整體占比皆在容許範圍內 → 不需換股，安心蓋牌過生活！'
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
        <div style="margin-top:6px; color:#E2E8F0;"><b>📌 漸進式輪轉規則（單次變化上限 10%，順應人性、分批試錯）</b></div>
        <div>1️⃣ <b>單次最多調整 10%</b>：即使訊號從 100% 轉為 0% 防禦，每週最多只移動 <b>10%</b> 倉位（分多週逐步到位），避免一次砍在低點或追在高點的心理抗拒。</div>
        <div>2️⃣ <b>三大池比例失衡（>10%）</b>：未達 10% 偏離前，可優先用新資金／可用現金往落後池子買進，減少賣股摩擦。</div>
        <div style="color:#94A3B8; margin-top:4px;">
            💡 <b>紀律提醒</b>：照事前訂好的條件執行、不猜高低點；調整完畢就安心蓋牌過生活，並確保生活緊急預備金與投資／槓桿資金分開。
        </div>
    </div>
</div>
""")

with st.expander("📋 查看本週精確買賣股數建議（單次最多調整 10% 步進目標）", expanded=True):
    def _pool_action(name, s1, p1, v1, s2, p2, v2, step_2x, ideal_2x):
        ptot = v1 + v2
        cur2 = (v2 / ptot) if ptot > 0 else 0.0
        gap = abs(cur2 - ideal_2x)
        if gap > 0.01 and ptot > 0:
            ds1 = int((ptot * (1 - step_2x) - v1) // p1)
            ds2 = int((ptot * step_2x - v2) // p2)
            a1 = f"買進 {ds1:,} 股" if ds1 >= 0 else f"賣出 {abs(ds1):,} 股"
            a2 = f"買進 {ds2:,} 股" if ds2 >= 0 else f"賣出 {abs(ds2):,} 股"
            st.warning(
                f"🔔 **{name}**（現況正二 {cur2*100:.1f}% → 本週步進目標 **{step_2x*100:.1f}%**，終極理想 {ideal_2x*100:.0f}%）：\n"
                f"- 原型 {a1} ｜ 正二 {a2}"
            )
        else:
            st.success(f"✅ **{name}（已貼合目標 {ideal_2x*100:.0f}%）**：維持現狀不需換股")

    _pool_action("台股核心池 (0050/00631L)", s_0050, tw_p1, tw_v1, s_631, tw_p2, tw_v2, tw_step_2x, tw_ideal_2x)
    _pool_action("美股核心池 (00662/00670L)", s_662, us_p1, us_v1, s_670, us_p2, us_v2, us_step_2x, us_ideal_2x)
    st.info(f"⚡ **費半衛星池 (00830)**：現價 {se_p1:.2f}，目前占比 {semi_cur_pct:.1f}%（目標 {semi_sug_pct:.1f}%），綜合積分 S = {data['SEMI']['score']:+.2f}")

# ================= 過去五年周線輪轉互動式趨勢圖（支援縮放 ＋ 游標顯示完整策略資訊） =================
with st.expander("📈 過去五年周線輪轉 Trend Chart 與轉折點年化報酬明細（單次上限 ±10%）", expanded=True):
    col_sel1, col_sel2 = st.columns([3, 2])
    with col_sel1:
        selected_target = st.radio(
            "選擇要查看的標的近五年周線轉折：",
            list(data["turns_map"].keys()),
            horizontal=True
        )
    with col_sel2:
        zoom_range = st.selectbox(
            "快速縮放檢視區間（也可直接在圖表上框選／滾輪縮放／拖曳下方時間軸）：",
            ["近 5 年完整走勢", "近 3 年走勢", "近 1 年走勢", "近 6 個月走勢"],
            index=0
        )

    sym_code, q5y, turns, ccy, is_lev = data["turns_map"][selected_target]
    px_prefix = "$" if ccy == "USD" else "NT$"

    fig = go.Figure()

    # 繪製背景區間色塊（依漸進目標正二比例著色）
    shapes = []
    if len(q5y) > 1:
        seg_start = q5y.index[0]
        seg_val = q5y["t2x"].iloc[0]
        for i in range(1, len(q5y)):
            cur_val = q5y["t2x"].iloc[i]
            if abs(cur_val - seg_val) > 1e-6 or i == len(q5y) - 1:
                seg_end = q5y.index[i]
                if seg_val >= 0.70:
                    fill_c = "rgba(16, 185, 129, 0.14)"   # 偏多積極區 (70%~100%)
                elif seg_val <= 0.30:
                    fill_c = "rgba(59, 130, 246, 0.18)"   # 偏空防禦區 (0%~30%)
                else:
                    fill_c = "rgba(245, 158, 11, 0.11)"   # 中性緩衝區 (40%~60%)
                shapes.append(dict(
                    type="rect", xref="x", yref="paper",
                    x0=seg_start, x1=seg_end, y0=0, y1=1,
                    fillcolor=fill_c, line=dict(width=0), layer="below"
                ))
                seg_start = seg_end
                seg_val = cur_val

    # 準備每一週游標懸停（Hover）的完整策略資訊
    hover_custom = np.stack([
        q5y["z20w"].map(lambda v: f"{v:+.2f}" if pd.notna(v) else "N/A"),
        q5y["z20m"].map(lambda v: f"{v:+.2f}" if pd.notna(v) else "N/A"),
        q5y["score"].map(lambda v: f"{v:+.2f}" if pd.notna(v) else "N/A"),
        q5y["t2x"].map(lambda v: f"原型 {(1-v)*100:.0f}% / 正二 {v*100:.0f}%" if is_lev else f"衛星檔位 {v*100:.0f}%"),
        q5y["raw_t2x"].map(lambda v: f"正二 {v*100:.0f}%" if is_lev else f"理想檔位 {v*100:.0f}%")
    ], axis=-1)

    fig.add_trace(go.Scatter(
        x=q5y.index, y=q5y["px"],
        mode="lines", name="Weekly Close (週收盤)",
        line=dict(color="#F8FAFC", width=2.1),
        customdata=hover_custom,
        hovertemplate=(
            "<b>%{x|%Y-%m-%d}</b><br>"
            "週收盤價: " + px_prefix + "%{y:.2f}<br>"
            "20週 Z值: %{customdata[0]} ｜ 20月 Z值: %{customdata[1]}<br>"
            "綜合積分 S: <b>%{customdata[2]}</b><br>"
            "當期步進目標: <b>%{customdata[3]}</b>（終極理想: %{customdata[4]}）"
            "<extra></extra>"
        )
    ))
    fig.add_trace(go.Scatter(
        x=q5y.index, y=q5y["ma20w"],
        mode="lines", name="20W MA (20週均線)",
        line=dict(color="#94A3B8", width=1.2, dash="dash"),
        hovertemplate="20週均線: " + px_prefix + "%{y:.2f}<extra></extra>"
    ))

    # 標示單次 ±10% 調整轉折點（調升正二 vs. 調降正二）
    up_turns = turns[turns["t2x"] > turns["prev_t2x"]]
    dn_turns = turns[turns["t2x"] < turns["prev_t2x"]]

    for label_grp, sub_t, m_col, m_sym in [
        ("調升正二 (+10%)", up_turns, "#22C55E", "triangle-up"),
        ("調降正二 (-10%)", dn_turns, "#EF4444", "triangle-down"),
    ]:
        if len(sub_t) > 0:
            t_custom = np.stack([
                sub_t["score"].map(lambda v: f"{v:+.2f}"),
                sub_t["prev_t2x"].map(lambda v: f"{v*100:.0f}%"),
                sub_t["t2x"].map(lambda v: f"{v*100:.0f}%"),
                sub_t["cum_ret"],
                sub_t["ann_ret"],
            ], axis=-1)
            fig.add_trace(go.Scatter(
                x=sub_t.index, y=sub_t["px"],
                mode="markers", name=label_grp,
                marker=dict(color=m_col, symbol=m_sym, size=9, line=dict(color="#FFFFFF", width=1.0)),
                customdata=t_custom,
                hovertemplate=(
                    "<b>【轉折點】%{x|%Y-%m-%d}</b><br>"
                    "轉折價: " + px_prefix + "%{y:.2f} ｜ 積分 S: %{customdata[0]}<br>"
                    "目標變化: <b>%{customdata[1]} → %{customdata[2]}</b><br>"
                    "至今累積: %{customdata[3]} ｜ 年化: %{customdata[4]}"
                    "<extra></extra>"
                )
            ))

    end_dt = q5y.index[-1]
    if zoom_range == "近 3 年走勢":
        start_dt = end_dt - pd.Timedelta(days=365 * 3)
    elif zoom_range == "近 1 年走勢":
        start_dt = end_dt - pd.Timedelta(days=365)
    elif zoom_range == "近 6 個月走勢":
        start_dt = end_dt - pd.Timedelta(days=182)
    else:
        start_dt = q5y.index[0]

    fig.update_layout(
        title=dict(
            text=f"{sym_code} — 5-Year Weekly Trend & ±10% Step Rotation (Hover & Zoom)",
            font=dict(size=15, color="#F8FAFC"), x=0.5, xanchor="center"
        ),
        paper_bgcolor="#111827",
        plot_bgcolor="#0F172A",
        font=dict(color="#CBD5E1"),
        height=480,
        margin=dict(l=45, r=20, t=54, b=35),
        shapes=shapes,
        hovermode="x unified",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0.0,
            bgcolor="rgba(30,41,59,0.75)", font=dict(size=11)
        ),
        xaxis=dict(
            range=[start_dt, end_dt],
            gridcolor="rgba(51,65,85,0.5)",
            rangeslider=dict(visible=True, thickness=0.07, bgcolor="#1E293B"),
            type="date"
        ),
        yaxis=dict(
            title=f"Price ({ccy})",
            gridcolor="rgba(51,65,85,0.5)",
            fixedrange=False
        )
    )

    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True, "displayModeBar": True})

    if len(turns) > 0:
        turns_sorted = turns.sort_index(ascending=False)
        rows_disp = []
        for dt, r in turns_sorted.iterrows():
            delta_pct = (r["t2x"] - r["prev_t2x"]) * 100.0
            if is_lev:
                prev_lbl = f"{r['prev_t2x']*100:.0f}% 2x"
                curr_lbl = f"{r['t2x']*100:.0f}% 2x"
                if delta_pct < 0:
                    action_hint = f"減碼正二 10% → 轉入原型（終極理想 {r['raw_t2x']*100:.0f}% 2x）"
                else:
                    action_hint = f"加碼正二 10% ← 原型轉入（終極理想 {r['raw_t2x']*100:.0f}% 2x）"
            else:
                prev_lbl = f"檔位 {r['prev_t2x']*100:.0f}%"
                curr_lbl = f"檔位 {r['t2x']*100:.0f}%"
                action_hint = f"單次調整 10% 檔位（理想檔位 {r['raw_t2x']*100:.0f}%）"

            rows_disp.append({
                "轉折日期": dt.strftime("%Y-%m-%d"),
                "週收盤價": f"{px_prefix}{r['px']:.2f}",
                "綜合積分 S": f"{r['score']:+.2f}",
                "單次目標變化 (±10%)": f"{prev_lbl} → {curr_lbl}",
                "至今累積報酬": r["cum_ret"],
                "折合年化報酬": r["ann_ret"],
                "對應操作方向": action_hint,
            })
        st.dataframe(pd.DataFrame(rows_disp), use_container_width=True, hide_index=True)
        st.caption("註：圖表涵蓋過去 5 年周線資料，游標移動至任意週次皆可檢視當週股價、Z值積分、當期目標比例與年化報酬。")
    else:
        st.info("近五年內未發生目標切換。")

st.caption("🛡️ 紀律提醒：條件觸發照表操課、不猜高低點；調整完畢即可安心蓋牌過生活，並確保生活緊急預備金與投資／槓桿資金獨立切分。")
