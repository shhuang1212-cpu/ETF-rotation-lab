import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="ETF 持股輪動 LAB", page_icon="📊", layout="wide")

# 高對比儀表板樣式（手機淺色/深色模式皆清楚可讀）
st.markdown("""
<style>
    .block-container { padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1120px; }
    .lab-header {
        display: flex; flex-wrap: wrap; align-items: center; gap: 10px;
        margin-bottom: 1rem;
    }
    .lab-title { font-size: 1.65rem; font-weight: 800; letter-spacing: -0.5px; }
    .lab-sub { font-size: 1rem; opacity: 0.75; border-left: 2px solid #94A3B8; padding-left: 10px; }
    .lab-badge {
        font-size: 0.78rem; font-weight: 700; padding: 2px 8px;
        border-radius: 6px; border: 1px solid #64748B; opacity: 0.85;
    }
    .pool-card {
        background-color: #111827;
        color: #F8FAFC;
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 16px 16px 14px 16px;
        margin-bottom: 12px;
    }
    .pool-name {
        text-align: center; font-size: 1.15rem; font-weight: 700;
        color: #F1F5F9; margin-bottom: 6px;
    }
    .pool-sub {
        text-align: center; font-size: 0.78rem; color: #94A3B8; margin-bottom: 8px;
    }
    .stat-row {
        display: flex; justify-content: space-between; align-items: center;
        font-size: 0.92rem; margin: 5px 0; color: #E2E8F0;
    }
    .stat-val { font-weight: 700; color: #FFFFFF; }
    .pp-pos { color: #4ADE80; font-weight: 700; }
    .pp-neg { color: #F87171; font-weight: 700; }
    .pp-zero { color: #94A3B8; font-weight: 700; }
    .z-block { margin-top: 10px; padding-top: 8px; border-top: 1px solid #1E293B; }
    .z-row {
        display: flex; align-items: center; justify-content: space-between;
        gap: 8px; font-size: 0.85rem; margin: 6px 0; color: #CBD5E1;
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
        display: flex; flex-wrap: wrap; justify-content: space-around; align-items: center;
        background-color: #111827; color: #F8FAFC;
        border: 1px solid #334155; border-radius: 14px;
        padding: 14px 18px; margin-top: 10px; gap: 12px;
    }
    .sum-item { font-size: 1.05rem; font-weight: 700; color: #E2E8F0; }
    .sum-trim { color: #F87171; font-size: 1.25rem; font-weight: 800; }
    .sum-add  { color: #4ADE80; font-size: 1.25rem; font-weight: 800; }
    .sum-cash { color: #F8FAFC; font-size: 1.25rem; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

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
    # 半圓弧長度約 157（半徑 50，pi * 50 = 157.08）
    arc_len = 157.08
    dash = (pct / 100.0) * arc_len
    return f"""
    <svg viewBox="0 0 140 78" style="width:100%;max-height:92px;display:block;margin:0 auto;">
        <path d="M 20 68 A 50 50 0 0 1 120 68" fill="none" stroke="#334155" stroke-width="11" stroke-linecap="round"/>
        <path d="M 20 68 A 50 50 0 0 1 120 68" fill="none" stroke="{color}" stroke-width="11" stroke-linecap="round"
              stroke-dasharray="{dash:.1f} {arc_len:.1f}"/>
        <text x="70" y="54" text-anchor="middle" fill="#FFFFFF" font-size="22" font-weight="800">{pct:.1f}%</text>
        <text x="20" y="76" text-anchor="middle" fill="#94A3B8" font-size="9">0%</text>
        <text x="120" y="76" text-anchor="middle" fill="#94A3B8" font-size="9">100%</text>
    </svg>
    """

def z_slider_html(label, z_val):
    # 將 -3σ ~ +3σ 映射到 0% ~ 100%
    pos = max(0.0, min(100.0, (z_val + 3.0) / 6.0 * 100.0))
    if z_val >= 1.5:
        c, z_cls = "#F87171", "pp-neg"
    elif z_val >= 0.4:
        c, z_cls = "#34D399", "pp-pos"
    elif z_val <= -1.0:
        c, z_cls = "#60A5FA", "pp-pos"
    else:
        c, z_cls = "#FBBF24", "pp-zero"
    return f"""
    <div class="z-row">
        <span style="min-width:38px;">{label}</span>
        <span style="font-size:0.75rem;color:#94A3B8;">-3σ</span>
        <div class="z-track">
            <div class="z-center"></div>
            <div class="z-dot" style="left:{pos:.1f}%;background:{c};"></div>
        </div>
        <span style="font-size:0.75rem;color:#94A3B8;">+3σ</span>
        <span class="{z_cls}" style="min-width:52px;text-align:right;">{z_val:+.2f}σ</span>
    </div>
    """

def fmt_pp(diff_pp):
    if abs(diff_pp) < 0.05:
        return '<span class="pp-zero">0.0 pp</span>'
    if diff_pp > 0:
        return f'<span class="pp-pos">+{diff_pp:.1f} pp</span>'
    return f'<span class="pp-neg">{diff_pp:.1f} pp</span>'

# ================= 頂部標題列 =================
col_t, col_b = st.columns([4, 1])
with col_t:
    st.markdown("""
    <div class="lab-header">
        <span class="lab-title">ETF 持股輪動 LAB</span>
        <span class="lab-sub">20 週／20 月位階</span>
        <span class="lab-badge">45 / 45 / 10 積極檔</span>
    </div>
    """, unsafe_allow_html=True)
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

total_exp = (tw_v1 + us_v1 + se_v1) + 2.0 * (tw_v2 + us_2x_target * 0) + 2.0 * (tw_v2 + us_v2)
net_asset = max(1.0, grand_tot - ext_debt)
real_lev  = total_exp / net_asset

# ================= 四張儀表板卡片（台股 / 美股 / 費半 / 總覽與槓桿） =================
cards = [
    {
        "title": "台股核心池",
        "sub": f"0050 ({tw_p1:.2f}) / 00631L ({tw_p2:.2f}) · S={data['TW']['score']:+.2f}",
        "cur": tw_cur_pct, "sug": tw_sug_pct,
        "zw": data["TW"]["z_20w"], "zm": data["TW"]["z_20m"],
        "color": "#34D399" if abs(tw_cur_pct - tw_sug_pct) <= 10 else "#FBBF24",
        "extra": f"池內正二：{(tw_v2/max(1,tw_v1+tw_v2)*100):.1f}% → 目標 {tw_2x_target*100:.0f}%"
    },
    {
        "title": "美股核心池",
        "sub": f"00662 ({us_p1:.2f}) / 00670L ({us_p2:.2f}) · S={data['US']['score']:+.2f}",
        "cur": us_cur_pct, "sug": us_sug_pct,
        "zw": data["US"]["z_20w"], "zm": data["US"]["z_20m"],
        "color": "#60A5FA" if data["US"]["used_fallback"] else "#34D399",
        "extra": f"池內正二：{(us_v2/max(1,us_v1+us_v2)*100):.1f}% → 目標 {us_2x_target*100:.0f}%"
    },
    {
        "title": "費半衛星池",
        "sub": f"00830 ({se_p1:.2f}) · S={data['SEMI']['score']:+.2f}",
        "cur": semi_cur_pct, "sug": semi_sug_pct,
        "zw": data["SEMI"]["z_20w"], "zm": data["SEMI"]["z_20m"],
        "color": "#34D399" if abs(semi_cur_pct - semi_sug_pct) <= 10 else "#F87171",
        "extra": "純 1x 原型 · 動能溫度計"
    },
    {
        "title": "總資產與槓桿",
        "sub": f"總市值 NT$ {grand_tot:,.0f} · 真實槓桿 {real_lev:.2f}x",
        "cur": min(100.0, (real_lev / 2.5) * 100.0), "sug": 68.0,
        "zw": data["TW"]["score"], "zm": data["US"]["score"],
        "color": "#34D399" if real_lev <= 2.0 else "#F87171",
        "extra": f"台股燈號：{tw_status.split(' ')[0]} ｜ 美股燈號：{us_status.split(' ')[0]}"
    }
]

cols = st.columns(4)
for idx, c in enumerate(cards):
    diff_pp = c["sug"] - c["cur"]
    html = f"""
    <div class="pool-card">
        <div class="pool-name">{c["title"]}</div>
        <div class="pool-sub">{c["sub"]}</div>
        {gauge_svg(c["cur"], c["color"])}
        <div class="stat-row"><span>目前持有</span><span class="stat-val">{c["cur"]:.1f}%</span></div>
        <div class="stat-row"><span>建議配置</span><span><strong class="stat-val">{c["sug"]:.1f}%</strong> &nbsp; {fmt_pp(diff_pp)}</span></div>
        <div class="stat-row" style="font-size:0.78rem;color:#94A3B8;"><span>{c["extra"]}</span></div>
        <div class="z-block">
            {z_slider_html("20 週", c["zw"])}
            {z_slider_html("20 月", c["zm"])}
        </div>
    </div>
    """
    cols[idx].markdown(html, unsafe_allow_html=True)

# ================= 底部摘要列（減碼 pp / 加碼 pp / 現金 %） =================
diffs = [tw_sug_pct - tw_cur_pct, us_sug_pct - us_cur_pct, semi_sug_pct - semi_cur_pct]
add_pp  = sum(max(0.0, d) for d in diffs)
trim_pp = sum(max(0.0, -d) for d in diffs)

st.markdown(f"""
<div class="summary-bar">
    <div class="sum-item">減碼 <span class="sum-trim">{trim_pp:.1f} pp</span></div>
    <div class="sum-item">|</div>
    <div class="sum-item">加碼 <span class="sum-add">{add_pp:.1f} pp</span></div>
    <div class="sum-item">|</div>
    <div class="sum-item">現金 <span class="sum-cash">{cash_pct:.1f}%</span></div>
</div>
""", unsafe_allow_html=True)

# ================= 精確買賣股數執行清單 =================
with st.expander("📋 查看精確買賣股數建議（偏離 >10% 觸發再平衡）", expanded=True):
    def _pool_action(name, s1, p1, v1, s2, p2, v2, t2x, score, zw):
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

    _pool_action("台股核心池 (0050/00631L)", s_0050, tw_p1, tw_v1, s_631, tw_p2, tw_v2, tw_2x_target, data["TW"]["score"], data["TW"]["z_20w"])
    _pool_action("美股核心池 (00662/00670L)", s_662, us_p1, us_v1, s_670, us_p2, us_v2, us_2x_target, data["US"]["score"], data["US"]["z_20w"])
    st.info(f"⚡ **費半衛星池 (00830)**：現價 {se_p1:.2f}，目前占比 {semi_cur_pct:.1f}%（目標 {semi_sug_pct:.1f}%），綜合積分 S = {data['SEMI']['score']:+.2f}")

st.caption("🛡️ 紀律提醒：條件觸發照表操課、不猜低點；調整完畢即可安心蓋牌過生活，並確保緊急預備金與投資資金獨立切分。")
