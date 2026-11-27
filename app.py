import textwrap
import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="ETF 持股輪動 LAB · 方案 A", page_icon="📊", layout="wide")

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
        border-radius: 6px; border: 1px solid #38BDF8; color: #BAE6FD; background: #0C4A6E;
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
    .bar-bond { background: #34D399; height: 100%; }
    .bar-none { background: #334155; height: 100%; }
    .mix-legend {
        font-size: 0.72rem; color: #CBD5E1; line-height: 1.4; margin-top: 4px;
    }
    .dot-1x { display:inline-block; width:8px; height:8px; border-radius:50%; background:#38BDF8; margin-right:4px; }
    .dot-2x { display:inline-block; width:8px; height:8px; border-radius:50%; background:#F59E0B; margin-right:4px; }
    .dot-bond { display:inline-block; width:8px; height:8px; border-radius:50%; background:#34D399; margin-right:4px; }
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
    .sum-cash { color: #34D399; font-size: 1.22rem; font-weight: 800; }
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

POOL_TARGET = {"TW": 0.40, "US": 0.40, "BOND": 0.20}
MAX_STEP_2X = 0.10
BOND_STEP = 0.05
BOND_CAP = 0.20
BOND_FLOOR = 0.05

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

def build_5y_weekly_turns(ticker, w_week, w_month):
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

    raw_list = [get_raw_target_2x(s, zw)[0] for s, zw in zip(w_df["score"], w_df["z20w"])]
    w_df["raw_t2x"] = raw_list
    w_df["t2x"] = apply_step_cap(raw_list, MAX_STEP_2X)

    cur_bw = 0.20
    bw_list = []
    act_list = []
    for s in w_df["score"]:
        if pd.notna(s) and s >= 1.5 and cur_bw < BOND_CAP - 1e-6:
            cur_bw = min(BOND_CAP, round(cur_bw + BOND_STEP, 4))
            act_list.append("HARVEST_5")
        elif pd.notna(s) and s <= -1.0 and cur_bw > BOND_FLOOR + 1e-6:
            cur_bw = max(BOND_FLOOR, round(cur_bw - BOND_STEP, 4))
            act_list.append("DIP_5")
        else:
            act_list.append("NONE")
        bw_list.append(cur_bw)
    w_df["bond_w"] = bw_list
    w_df["bond_act"] = act_list

    cutoff = w_df.index[-1] - pd.Timedelta(days=365 * 5)
    w_5y = w_df[w_df.index >= cutoff].copy()
    w_5y["prev_t2x"] = w_5y["t2x"].shift(1)
    turns = w_5y[(w_5y["prev_t2x"].notna()) & ((w_5y["t2x"] - w_5y["prev_t2x"]).abs() > 1e-6)].copy()

    start_dt = w_5y.index[0]
    start_px = float(w_5y["px"].iloc[0])

    five_yr_rets, curr_yr_ann_rets = [], []
    for dt, r in turns.iterrows():
        p_node = float(r["px"])
        days_from_start = max(1, (dt - start_dt).days)

        if start_px > 0 and p_node > 0:
            cum_ret = (p_node / start_px - 1.0) * 100.0
            val_100w = 100.0 * (p_node / start_px)
            five_yr_rets.append(f"{cum_ret:+.1f}% (100萬→{val_100w:.1f}萬)")

            if days_from_start >= 21:
                ann_ret = ((p_node / start_px) ** (365.25 / days_from_start) - 1.0) * 100.0
                ann_ret = max(-99.0, min(500.0, ann_ret))
                curr_yr_ann_rets.append(f"{ann_ret:+.1f}% ({days_from_start}天年化)")
            else:
                curr_yr_ann_rets.append(f"{cum_ret:+.1f}% ({days_from_start}天累計)")
        else:
            five_yr_rets.append("N/A")
            curr_yr_ann_rets.append("N/A")

    turns["five_yr_ret"] = five_yr_rets
    turns["curr_yr_ann"] = curr_yr_ann_rets
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

    def _latest(ticker, default_px=0.0):
        try:
            s = yf.Ticker(ticker).history(period="5d", auto_adjust=True)["Close"].dropna()
            if len(s) > 0:
                return float(s.iloc[-1])
        except Exception:
            pass
        return default_px

    qqq_5y, qqq_turns = build_5y_weekly_turns("QQQ", 0.50, 0.50)
    tw_5y, tw_turns   = build_5y_weekly_turns("0050.TW", 0.65, 0.35)

    return {
        "TW": _fetch_pool("0050.TW", 0.65, 0.35),
        "US": _fetch_pool("00662.TW", 0.50, 0.50, fallback_us="QQQ"),
        "p_685l": _latest("00685L.TW"),
        "p_670l": _latest("00670L.TW"),
        "p_865b": _latest("00865B.TW"),
        "turns_map": {
            "美股 QQQ (對應 00662/00670L)": ("QQQ", qqq_5y, qqq_turns, "USD"),
            "台股 0050 (對應 0050/00685L)": ("0050.TW", tw_5y, tw_turns, "TWD"),
        }
    }

def step_toward(current_ratio, ideal_ratio, max_step=0.10):
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

def mix_visual_html(header_text, cur_1x_pct, cur_2x_pct, tgt_1x_pct, tgt_2x_pct, note_text, cur_bond_pct=0.0, tgt_bond_pct=0.0, show_bond=False):
    c1 = max(0.0, min(100.0, cur_1x_pct))
    c2 = max(0.0, min(100.0 - c1, cur_2x_pct))
    cb = max(0.0, min(100.0 - c1 - c2, cur_bond_pct))
    cn = max(0.0, 100.0 - c1 - c2 - cb)

    t1 = max(0.0, min(100.0, tgt_1x_pct))
    t2 = max(0.0, min(100.0 - t1, tgt_2x_pct))
    tb = max(0.0, min(100.0 - t1 - t2, tgt_bond_pct))
    tn = max(0.0, 100.0 - t1 - t2 - tb)

    if show_bond:
        cur_lbl = f"原型 {c1:.0f}% / 正二 {c2:.0f}% / 短債 {cb:.0f}%"
        tgt_lbl = f"原型 {t1:.0f}% / 正二 {t2:.0f}% / 短債 {tb:.0f}%"
        legend_extra = ' &nbsp;&nbsp;<span class="dot-bond"></span>00865B 短債'
    else:
        cur_lbl = f"原型 {c1:.0f}% / 正二 {c2:.0f}%"
        tgt_lbl = f"原型 {t1:.0f}% / 正二 {t2:.0f}%"
        legend_extra = ""

    return (
        f'<div class="mix-box">'
        f'<div class="mix-title"><span>{header_text}</span></div>'
        f'<div class="mix-row-label"><span>現況</span><span>{cur_lbl}</span></div>'
        f'<div class="mix-bar">'
        f'<div class="bar-1x" style="width:{c1:.1f}%;"></div>'
        f'<div class="bar-2x" style="width:{c2:.1f}%;"></div>'
        f'<div class="bar-bond" style="width:{cb:.1f}%;"></div>'
        f'<div class="bar-none" style="width:{cn:.1f}%;"></div>'
        f'</div>'
        f'<div class="mix-row-label"><span>本週目標</span><span>{tgt_lbl}</span></div>'
        f'<div class="mix-bar">'
        f'<div class="bar-1x" style="width:{t1:.1f}%;"></div>'
        f'<div class="bar-2x" style="width:{t2:.1f}%;"></div>'
        f'<div class="bar-bond" style="width:{tb:.1f}%;"></div>'
        f'<div class="bar-none" style="width:{tn:.1f}%;"></div>'
        f'</div>'
        f'<div class="mix-legend">'
        f'<span class="dot-1x"></span>原型 ETF &nbsp;&nbsp;'
        f'<span class="dot-2x"></span>槓桿 (2x){legend_extra}<br>'
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
        <span class="lab-sub">雙週期共振 · 單次上限 ±10%</span>
        <span class="lab-badge">方案 A：40 / 40 / 20(00865B上限)</span>
    </div>
    """)
with col_b:
    if st.button("🔄 更新報價", use_container_width=True):
        st.cache_data.clear()

with st.spinner("正在抓取五檔最新還原權息報價與近五年周線轉折..."):
    data = fetch_market_data()

with st.expander("📝 輸入／修改目前五檔持股與資金（預設為範例庫存，請依實際股數調整）", expanded=False):
    c1, c2, c3, c4 = st.columns(4)
    s_0050 = c1.number_input("0050 股數", min_value=0, value=1000, step=100)
    s_685l = c2.number_input("00685L 股數 (台股正2)", min_value=0, value=2000, step=100)
    s_662  = c3.number_input("00662 股數", min_value=0, value=2000, step=100)
    s_670l = c4.number_input("00670L 股數 (美股正2)", min_value=0, value=500, step=100)
    c5, c6, c7, c8 = st.columns(4)
    s_865b   = c5.number_input("00865B 股數 (短債緩衝池)", min_value=0, value=2000, step=100)
    cash_bal = c6.number_input("額外可用現金 (元)", min_value=0, value=10000, step=1000)
    ext_debt = c7.number_input("外部借款 (元)", min_value=0, value=0, step=10000)
    _        = c8.empty()

tw_p1, tw_p2 = data["TW"]["price"], data["p_685l"]
us_p1, us_p2 = data["US"]["price"], data["p_670l"]
bond_p       = data["p_865b"]

tw_v1, tw_v2 = s_0050 * tw_p1, s_685l * tw_p2
us_v1, us_v2 = s_662 * us_p1, s_670l * us_p2
bond_v       = s_865b * bond_p

invest_tot = tw_v1 + tw_v2 + us_v1 + us_v2 + bond_v
grand_tot  = invest_tot + cash_bal
cash_pct   = (cash_bal / grand_tot * 100.0) if grand_tot > 0 else 0.0

tw_cur_pct   = ((tw_v1 + tw_v2) / grand_tot * 100.0) if grand_tot > 0 else 0.0
us_cur_pct   = ((us_v1 + us_v2) / grand_tot * 100.0) if grand_tot > 0 else 0.0
bond_cur_pct = (bond_v / grand_tot * 100.0) if grand_tot > 0 else 0.0

tw_sug_pct   = POOL_TARGET["TW"] * 100.0
us_sug_pct   = POOL_TARGET["US"] * 100.0
bond_sug_pct = POOL_TARGET["BOND"] * 100.0

tw_ideal_2x, tw_status = get_raw_target_2x(data["TW"]["score"], data["TW"]["z_20w"])
us_ideal_2x, us_status = get_raw_target_2x(data["US"]["score"], data["US"]["z_20w"])

tw_pool_tot = max(1.0, tw_v1 + tw_v2)
tw_cur_2x_ratio = (tw_v2 / tw_pool_tot) if (tw_v1 + tw_v2) > 0 else 0.0
tw_step_2x = step_toward(tw_cur_2x_ratio, tw_ideal_2x, MAX_STEP_2X)

tw_c2_in = tw_cur_2x_ratio * 100.0
tw_c1_in = 100.0 - tw_c2_in
tw_t2_in = tw_step_2x * 100.0
tw_t1_in = 100.0 - tw_t2_in

us_pool_tot = max(1.0, us_v1 + us_v2)
us_cur_2x_ratio = (us_v2 / us_pool_tot) if (us_v1 + us_v2) > 0 else 0.0
us_step_2x = step_toward(us_cur_2x_ratio, us_ideal_2x, MAX_STEP_2X)

us_c2_in = us_cur_2x_ratio * 100.0
us_c1_in = 100.0 - us_c2_in
us_t2_in = us_step_2x * 100.0
us_t1_in = 100.0 - us_t2_in

tw_score = data["TW"]["score"]
us_score = data["US"]["score"]
cur_bond_ratio = (bond_v / grand_tot) if grand_tot > 0 else 0.0

plan_a_mode = "HOLD"
plan_a_step_ratio = 0.0
if (tw_score >= 1.5 or us_score >= 1.5) and cur_bond_ratio < BOND_CAP - 1e-4:
    plan_a_mode = "HARVEST_TO_865B"
    plan_a_step_ratio = min(BOND_STEP, BOND_CAP - cur_bond_ratio)
elif (tw_score <= -1.0 or us_score <= -1.0) and cur_bond_ratio > BOND_FLOOR + 1e-4:
    plan_a_mode = "DIP_BUY_PROTOTYPE"
    plan_a_step_ratio = min(BOND_STEP, cur_bond_ratio - BOND_FLOOR)

tgt_bond_ratio = (
    cur_bond_ratio + plan_a_step_ratio if plan_a_mode == "HARVEST_TO_865B"
    else (cur_bond_ratio - plan_a_step_ratio if plan_a_mode == "DIP_BUY_PROTOTYPE" else cur_bond_ratio)
)

tot_1x_val = tw_v1 + us_v1
tot_2x_val = tw_v2 + us_v2
all_c1_pct = (tot_1x_val / grand_tot * 100.0) if grand_tot > 0 else 0.0
all_c2_pct = (tot_2x_val / grand_tot * 100.0) if grand_tot > 0 else 0.0
all_cb_pct = bond_cur_pct

all_tb_pct = tgt_bond_ratio * 100.0
all_t2_pct = (POOL_TARGET["TW"] * tw_step_2x + POOL_TARGET["US"] * us_step_2x) * 100.0
all_t1_pct = max(0.0, 100.0 - cash_pct - all_tb_pct - all_t2_pct)

total_exp = (tw_v1 + us_v1) + 2.0 * (tw_v2 + us_v2)
net_asset = max(1.0, grand_tot - ext_debt)
real_lev  = total_exp / net_asset

cards = [
    {
        "title": "台股核心池 (40%)",
        "sub": f"0050 ({tw_p1:.2f}) / 00685L ({tw_p2:.2f}) · S={tw_score:+.2f}",
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
        "title": "美股核心池 (40%)",
        "sub": f"00662 ({us_p1:.2f}) / 00670L ({us_p2:.2f}) · S={us_score:+.2f}",
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
        "title": "短債緩衝池 (上限20%)",
        "sub": f"00865B ({bond_p:.2f}) · 已用 {bond_cur_pct:.1f}% / 20%",
        "cur": min(100.0, (bond_cur_pct / 20.0) * 100.0), "sug": bond_sug_pct,
        "zw": tw_score, "zm": us_score,
        "color": "#34D399" if bond_cur_pct <= 20.5 else "#F87171",
        "mix": mix_visual_html(
            "00865B 水位（占總資產）",
            0.0, 0.0, 0.0, 0.0,
            f"本週短債目標：{bond_cur_pct:.1f}% → <b>{all_tb_pct:.1f}%</b>（上限 20%）",
            cur_bond_pct=bond_cur_pct, tgt_bond_pct=all_tb_pct, show_bond=True
        )
    },
    {
        "title": "全組合 總曝險與配置",
        "sub": f"總資產 NT$ {grand_tot:,.0f} · 真實槓桿 {real_lev:.2f}x",
        "cur": min(100.0, (real_lev / 2.5) * 100.0), "sug": 64.0,
        "zw": data["TW"]["z_20w"], "zm": data["US"]["z_20w"],
        "color": "#34D399" if real_lev <= 2.0 else "#F87171",
        "mix": mix_visual_html(
            "全組合 原型 / 正二 / 短債",
            all_c1_pct, all_c2_pct, all_t1_pct, all_t2_pct,
            f"正二全組合：{all_c2_pct:.1f}% → <b>{all_t2_pct:.1f}%</b>",
            cur_bond_pct=all_cb_pct, tgt_bond_pct=all_tb_pct, show_bond=True
        )
    }
]

cols = st.columns(4)
for idx, c in enumerate(cards):
    diff_pp = c["sug"] - c["cur"]
    cur_display = f"{bond_cur_pct:.1f}%" if idx == 2 else f"{c['cur']:.1f}%"
    diff_display = fmt_pp(bond_sug_pct - bond_cur_pct) if idx == 2 else fmt_pp(diff_pp)
    card_html = (
        f'<div class="pool-card">'
        f'<div class="pool-name">{c["title"]}</div>'
        f'<div class="pool-sub">{c["sub"]}</div>'
        f'{gauge_svg(c["cur"], c["color"])}'
        f'<div class="stat-line"><span>目前持有</span><span class="stat-val">{cur_display}</span></div>'
        f'<div class="stat-line"><span>目標上限</span><span><strong class="stat-val">{c["sug"]:.1f}%</strong> &nbsp;{diff_display}</span></div>'
        f'{c["mix"]}'
        f'<div class="z-block">'
        f'{z_slider_html("週/台", c["zw"])}'
        f'{z_slider_html("月/美", c["zm"])}'
        f'</div>'
        f'</div>'
    )
    with cols[idx]:
        render_html(card_html)

diffs = [tw_sug_pct - tw_cur_pct, us_sug_pct - us_cur_pct, bond_sug_pct - bond_cur_pct]
add_pp  = sum(max(0.0, d) for d in diffs)
trim_pp = sum(max(0.0, -d) for d in diffs)

pool_map = [
    ("台股核心池 (40%)", tw_cur_pct, tw_sug_pct),
    ("美股核心池 (40%)", us_cur_pct, us_sug_pct),
    ("00865B 短債池 (20%)", bond_cur_pct, bond_sug_pct),
]
over_pools  = [f"{n}（超標 {c - s:.1f}%）" for n, c, s in pool_map if c - s > 0.5]
under_pools = [f"{n}（距離上限 {s - c:.1f}%）" for n, c, s in pool_map if s - c > 0.5]
over_text   = "、".join(over_pools) if over_pools else "目前無超標部位"
under_text  = "、".join(under_pools) if under_pools else "目前已達目標水位"

triggered_reasons = []
if plan_a_mode == "HARVEST_TO_865B":
    triggered_reasons.append(f"多頭高檔收割：正二轉 +{plan_a_step_ratio*100:.1f}% 至 00865B（上限 20%）")
elif plan_a_mode == "DIP_BUY_PROTOTYPE":
    triggered_reasons.append(f"低檔積分訊號：動用 {plan_a_step_ratio*100:.1f}% 00865B 補買 0050/00662 原型")

if abs(tw_cur_2x_ratio - tw_ideal_2x) > 0.01 and (tw_v1 + tw_v2) > 0:
    triggered_reasons.append(f"台股池內正二步進調整（單次上限 ±10%）")
if abs(us_cur_2x_ratio - us_ideal_2x) > 0.01 and (us_v1 + us_v2) > 0:
    triggered_reasons.append(f"美股池內正二步進調整（單次上限 ±10%）")

if triggered_reasons:
    status_banner = (
        f'<div class="trigger-banner-on">'
        f'🔔 【方案 A 今日狀態：已觸發步進調整】{" ｜ ".join(triggered_reasons)}'
        f'</div>'
    )
else:
    status_banner = (
        f'<div class="trigger-banner-off">'
        f'🟢 【方案 A 今日狀態：維持現狀】池內正二與 00865B 緩衝池皆無需動作 → 安心蓋牌過生活！'
        f'</div>'
    )

render_html(f"""
<div class="summary-bar">
    <div class="sum-top">
        <div class="sum-item">偏離超標合計 <span class="sum-trim">{trim_pp:.1f}%</span></div>
        <div class="sum-item">|</div>
        <div class="sum-item">距離上限空間 <span class="sum-add">{add_pp:.1f}%</span></div>
        <div class="sum-item">|</div>
        <div class="sum-item">00865B + 現金緩衝 <span class="sum-cash">{bond_cur_pct + cash_pct:.1f}%</span></div>
    </div>
    {status_banner}
    <div class="guide-box">
        <div>📉 <b>高於目標（偏重）</b>：{over_text}</div>
        <div>📈 <b>低於目標（餘裕）</b>：{under_text}</div>
        <div style="margin-top:6px; color:#E2E8F0;"><b>📌 方案 A 執行規則（雙週期共振 ＋ 00865B 每次 5% 收割／低檔補原型、上限 20%）</b></div>
        <div>1️⃣ <b>多頭收割（每次 5%、最多 20%）</b>：當台股或美股綜合積分 <b>S ≥ +1.5</b> 且 00865B 未滿 20%，每次從正二獲利轉 <b>5%</b> 進 00865B 鎖利。</div>
        <div>2️⃣ <b>低檔補原型（每次 5%、保留 5% 底倉）</b>：當積分 <b>S ≤ -1.0</b> 時，每次動用 <b>5%</b> 的 00865B 買進 <b>0050 / 00662 原型</b>（避免空頭續跌段承受正二耗損；等積分轉強再由雙週期引擎自動轉正二）。</div>
        <div>3️⃣ <b>池內輪動上限 ±10%</b>：台股池 (40%) 與美股池 (40%) 內部原型與正二互換，每週單次調整上限 <b>10%</b>，降低人性壓力並保留試錯餘裕。</div>
        <div style="color:#94A3B8; margin-top:4px;">
            💡 <b>紀律提醒</b>：生活緊急預備金與投資／槓桿資金獨立切分；照條件執行、不猜高低點，調完就安心蓋牌過生活。
        </div>
    </div>
</div>
""")

with st.expander("📋 查看方案 A 本週精確買賣股數建議", expanded=True):
    if plan_a_mode == "HARVEST_TO_865B" and grand_tot > 0 and bond_p > 0:
        move_amt = plan_a_step_ratio * grand_tot
        buy_865b_sh = int(move_amt // bond_p)
        st.warning(
            f"💰 **【多頭收割 5% → 00865B】**（積分高檔且 00865B 目前 {bond_cur_pct:.1f}% < 20%）：\n"
            f"- 建議將約 **NT$ {move_amt:,.0f}**（總資產 {plan_a_step_ratio*100:.1f}%）正二獲利轉入短債 → **買進 00865B 約 {buy_865b_sh:,} 股**。"
        )
    elif plan_a_mode == "DIP_BUY_PROTOTYPE" and grand_tot > 0 and bond_p > 0:
        move_amt = plan_a_step_ratio * grand_tot
        sell_865b_sh = int(move_amt // bond_p)
        buy_50_sh = int((move_amt * 0.5) // tw_p1) if tw_p1 > 0 else 0
        buy_662_sh = int((move_amt * 0.5) // us_p1) if us_p1 > 0 else 0
        st.info(
            f"🛡️ **【低檔補原型 5% ← 00865B】**（積分 S ≤ -1.0，優先買原型、不急著空頭接正二）：\n"
            f"- **賣出 00865B 約 {sell_865b_sh:,} 股**（約 NT$ {move_amt:,.0f}），平均轉入：**買進 0050 約 {buy_50_sh:,} 股 ＋ 買進 00662 約 {buy_662_sh:,} 股**。"
        )
    else:
        st.success(f"✅ **【00865B 短債緩衝池】**：目前占總資產 **{bond_cur_pct:.1f}%**（上限 20%），本週無需執行收割或動用短債。")

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

    _pool_action("台股核心池 (0050/00685L)", s_0050, tw_p1, tw_v1, s_685l, tw_p2, tw_v2, tw_step_2x, tw_ideal_2x)
    _pool_action("美股核心池 (00662/00670L)", s_662, us_p1, us_v1, s_670l, us_p2, us_v2, us_step_2x, us_ideal_2x)

# ================= 過去五年周線輪轉互動式趨勢圖 =================
with st.expander("📈 過去五年周線輪轉 Trend Chart 與轉折點報酬明細（含 00865B 5% 策略點位）", expanded=True):
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

    sym_code, q5y, turns, ccy = data["turns_map"][selected_target]
    px_prefix = "$" if ccy == "USD" else "NT$"

    fig = go.Figure()

    shapes = []
    if len(q5y) > 1:
        seg_start = q5y.index[0]
        seg_val = q5y["t2x"].iloc[0]
        for i in range(1, len(q5y)):
            cur_val = q5y["t2x"].iloc[i]
            if abs(cur_val - seg_val) > 1e-6 or i == len(q5y) - 1:
                seg_end = q5y.index[i]
                if seg_val >= 0.70:
                    fill_c = "rgba(16, 185, 129, 0.14)"
                elif seg_val <= 0.30:
                    fill_c = "rgba(59, 130, 246, 0.18)"
                else:
                    fill_c = "rgba(245, 158, 11, 0.11)"
                shapes.append(dict(
                    type="rect", xref="x", yref="paper",
                    x0=seg_start, x1=seg_end, y0=0, y1=1,
                    fillcolor=fill_c, line=dict(width=0), layer="below"
                ))
                seg_start = seg_end
                seg_val = cur_val

    hover_custom = np.stack([
        q5y["z20w"].map(lambda v: f"{v:+.2f}" if pd.notna(v) else "N/A"),
        q5y["z20m"].map(lambda v: f"{v:+.2f}" if pd.notna(v) else "N/A"),
        q5y["score"].map(lambda v: f"{v:+.2f}" if pd.notna(v) else "N/A"),
        q5y["t2x"].map(lambda v: f"原型 {(1-v)*100:.0f}% / 正二 {v*100:.0f}%"),
        q5y["bond_w"].map(lambda v: f"{v*100:.0f}%")
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
            "正二步進: <b>%{customdata[3]}</b> ｜ 00865B 水位: <b>%{customdata[4]}</b>"
            "<extra></extra>"
        )
    ))
    fig.add_trace(go.Scatter(
        x=q5y.index, y=q5y["ma20w"],
        mode="lines", name="20W MA (20週均線)",
        line=dict(color="#94A3B8", width=1.2, dash="dash"),
        hovertemplate="20週均線: " + px_prefix + "%{y:.2f}<extra></extra>"
    ))

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
                sub_t["five_yr_ret"],
                sub_t["curr_yr_ann"],
            ], axis=-1)
            fig.add_trace(go.Scatter(
                x=sub_t.index, y=sub_t["px"],
                mode="markers", name=label_grp,
                marker=dict(color=m_col, symbol=m_sym, size=9, line=dict(color="#FFFFFF", width=1.0)),
                customdata=t_custom,
                hovertemplate=(
                    "<b>【正二轉折】%{x|%Y-%m-%d}</b><br>"
                    "轉折價: " + px_prefix + "%{y:.2f} ｜ 積分 S: %{customdata[0]}<br>"
                    "目標變化: <b>%{customdata[1]} → %{customdata[2]}</b><br>"
                    "五年累積(100萬起): %{customdata[3]} ｜ 年化: %{customdata[4]}"
                    "<extra></extra>"
                )
            ))

    # 00865B 收割：藍色（#3B82F6）；00865B 補原型：亮黃色（#FACC15）
    b_harvest = q5y[q5y["bond_act"] == "HARVEST_5"]
    b_dip = q5y[q5y["bond_act"] == "DIP_5"]

    if len(b_harvest) > 0:
        fig.add_trace(go.Scatter(
            x=b_harvest.index, y=b_harvest["px"],
            mode="markers", name="00865B 收割 (+5% 轉短債)",
            marker=dict(color="#3B82F6", symbol="diamond", size=9, line=dict(color="#FFFFFF", width=1.0)),
            customdata=b_harvest["bond_w"].map(lambda v: f"{v*100:.0f}%"),
            hovertemplate=(
                "<b>【00865B 收割 +5%】%{x|%Y-%m-%d}</b><br>"
                "當週股價: " + px_prefix + "%{y:.2f} ｜ 短債水位升至 <b>%{customdata}</b>"
                "<extra></extra>"
            )
        ))

    if len(b_dip) > 0:
        fig.add_trace(go.Scatter(
            x=b_dip.index, y=b_dip["px"],
            mode="markers", name="00865B 補原型 (-5% 動用短債)",
            marker=dict(color="#FACC15", symbol="diamond", size=9, line=dict(color="#0F172A", width=1.0)),
            customdata=b_dip["bond_w"].map(lambda v: f"{v*100:.0f}%"),
            hovertemplate=(
                "<b>【00865B 補原型 -5%】%{x|%Y-%m-%d}</b><br>"
                "當週股價: " + px_prefix + "%{y:.2f} ｜ 短債水位降至 <b>%{customdata}</b>"
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
            text=f"{sym_code} — 5-Year Weekly Trend, ±10% Step & 00865B (±5%)",
            font=dict(size=15, color="#F8FAFC"), x=0.5, xanchor="center"
        ),
        paper_bgcolor="#111827",
        plot_bgcolor="#0F172A",
        font=dict(color="#CBD5E1"),
        height=490,
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
            prev_lbl = f"{r['prev_t2x']*100:.0f}% 2x"
            curr_lbl = f"{r['t2x']*100:.0f}% 2x"
            if delta_pct < 0:
                action_hint = f"減碼正二 10% → 轉入原型（終極理想 {r['raw_t2x']*100:.0f}% 2x）"
            else:
                action_hint = f"加碼正二 10% ← 原型轉入（終極理想 {r['raw_t2x']*100:.0f}% 2x）"

            rows_disp.append({
                "轉折日期": dt.strftime("%Y-%m-%d"),
                "週收盤價": f"{px_prefix}{r['px']:.2f}",
                "綜合積分 S": f"{r['score']:+.2f}",
                "單次目標變化 (±10%)": f"{prev_lbl} → {curr_lbl}",
                "五年累積報酬": r["five_yr_ret"],
                "當年年化報酬": r["curr_yr_ann"],
                "對應操作方向": action_hint,
            })
        st.dataframe(pd.DataFrame(rows_disp), use_container_width=True, hide_index=True)
        st.caption(f"註：以五年圖第一天（{q5y.index[0].strftime('%Y-%m-%d')}，收盤價 {px_prefix}{q5y['px'].iloc[0]:.2f}）投入 100 萬為起點計算至各轉折點；藍色菱形為 00865B 收割 +5%（上限 20%），亮黃色菱形為 00865B 補原型 -5%（保留 5% 底倉）。")
    else:
        st.info("近五年內未發生目標切換。")

st.caption("🛡️ 紀律提醒：生活緊急預備金與投資／槓桿資金獨立切分；照條件執行、不猜高低點，調完就安心蓋牌過生活。")
