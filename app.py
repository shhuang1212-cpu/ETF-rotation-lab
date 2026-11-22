import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# 頁面設定（針對手機螢幕優化為置中版面）
st.set_page_config(page_title="ETF 存股輪轉 LAB", page_icon="🚀", layout="centered")

# 高對比卡片樣式（無論手機是淺色或深色模式，數字與標題都清楚好讀）
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 3rem; }
    [data-testid="stMetric"] {
        background-color: #F8FAFC !important;
        padding: 12px 14px !important;
        border-radius: 12px !important;
        border: 1px solid #CBD5E1 !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    [data-testid="stMetricLabel"] p {
        color: #475569 !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetricValue"] div {
        color: #0F172A !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

# 鎖定最佳化參數：45 / 45 / 10（100% 積極檔）
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
    """抓取五檔最新報價與三大池積分（快取 10 分鐘，改股數時免重抓）"""
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
    warning = ""
    if score >= 2.4:
        return 0.50, "🔴 極度過熱降溫 (目標 1.5x)", warning
    elif score >= 0.4:
        if z_20w < -1.0:
            return 0.50, "🟠 多頭急殺煞車 (目標 1.5x)", "⚠️ 已觸發急殺煞車！"
        if z_20w < -0.75:
            warning = "🟡 黃燈預警：20週Z值已跌破 -0.75，留意短線波動"
        return 1.00, "🟢 強勢多頭主升段 (目標 2.0x)", warning
    elif score <= -0.4:
        if z_20w > 0.2:
            return 0.50, "🟣 底部週線V轉反攻 (目標 1.5x)", warning
        return 0.00, "🔵 空頭主跌防禦區 (目標 1.0x)", "🛡️ 防禦模式：避開空頭波動耗損"
    else:
        return 0.50, "⚪ 多空緩衝過渡區 (目標 1.5x)", warning

# ================= 頂部標題與更新按鈕 =================
st.title("🚀 ETF 存股輪轉 LAB")
st.caption("45% 台股 ＋ 45% 美股 ＋ 10% 費半 ｜ 100% 積極檔")

if st.button("🔄 重新抓取最新報價", use_container_width=True):
    st.cache_data.clear()

with st.spinner("正在從雲端抓取五檔還原權息報價..."):
    data = fetch_market_data()

# ================= 使用者庫存輸入區 =================
with st.expander("📝 點此輸入／修改你的目前持股與資金", expanded=True):
    c1, c2 = st.columns(2)
    s_0050 = c1.number_input("0050 股數", min_value=0, value=1000, step=100)
    s_631  = c2.number_input("00631L 股數", min_value=0, value=1000, step=100)
    s_662  = c1.number_input("00662 股數", min_value=0, value=2000, step=100)
    s_670  = c2.number_input("00670L 股數", min_value=0, value=500, step=100)
    s_830  = c1.number_input("00830 股數", min_value=0, value=1000, step=100)
    new_cash = c2.number_input("本次新資金 (元)", min_value=0, value=20000, step=1000)
    ext_debt = st.number_input("投資外部借款 (信貸/質押，沒有填 0)", min_value=0, value=0, step=10000)

# ================= 核心池計算顯示函式 =================
def render_core_pool(title, sym_1x, sym_2x, info, p2, shares_1x, shares_2x, add_cash):
    st.divider()
    st.subheader(title)
    p1 = info["price"]
    st.caption(f"報價日期：{info['date']} ｜ {sym_1x}: {p1:.2f} ｜ {sym_2x}: {p2:.2f}")

    if info["used_fallback"]:
        st.info(f"🔄 偵測到 {sym_1x} 分割斷層 ({info['max_1d_chg']*100:.1f}%)，已自動改用 [{info['fallback_name']}×匯率] 計算真實積分")

    m1, m2, m3 = st.columns(3)
    m1.metric("20週 Z值", f"{info['z_20w']:+.2f}")
    m2.metric("20月 Z值", f"{info['z_20m']:+.2f}")
    m3.metric("綜合積分 S", f"{info['score']:+.2f}")

    target_2x, status_text, warning = get_target_2x_ratio(info["score"], info["z_20w"])
    st.markdown(f"**市場狀態**：{status_text}")
    if warning:
        st.warning(warning)

    val_1x = shares_1x * p1
    val_2x = shares_2x * p2
    pool_tot = val_1x + val_2x + add_cash
    cur_2x = val_2x / pool_tot if pool_tot > 0 else 0.0
    dev = abs(cur_2x - target_2x)

    if info["is_locked"]:
        st.error(f"🚨 【防呆鎖倉】偵測到 {sym_1x} 單日價差達 {info['max_1d_chg']*100:.1f}%，已暫停換股建議。")
        return pool_tot, val_1x, val_2x

    st.write(f"💼 池內總資產：**NT$ {pool_tot:,.0f}** ｜ 正二占比：**{cur_2x*100:.1f}%**（目標 {target_2x*100:.0f}%，偏離 {dev*100:.1f}%）")

    if dev > 0.10 and pool_tot > 0:
        diff_s1 = int((pool_tot * (1 - target_2x) - val_1x) // p1)
        diff_s2 = int((pool_tot * target_2x - val_2x) // p2)
        act1 = f"買進 **{diff_s1:,}** 股" if diff_s1 >= 0 else f"賣出 **{abs(diff_s1):,}** 股"
        act2 = f"買進 **{diff_s2:,}** 股" if diff_s2 >= 0 else f"賣出 **{abs(diff_s2):,}** 股"
        st.error(f"🔔 **觸發再平衡 (>10%) 建議動作：**\n- {sym_1x}：{act1}\n- {sym_2x}：{act2}")
    else:
        msg = "✅ **未偏離 >10%，維持現狀不需換股！**"
        if add_cash > 0:
            b1 = int((add_cash * (1 - target_2x)) // p1)
            b2 = int((add_cash * target_2x) // p2)
            msg += f"\n- 💵 本次新資金 NT$ {add_cash:,.0f} 建議買進：{sym_1x} **{b1:,}** 股 ＋ {sym_2x} **{b2:,}** 股"
        st.success(msg)

    return pool_tot, val_1x, val_2x

# 1. 台股池 & 2. 美股池
tw_tot, tw_1x, tw_2x = render_core_pool(
    "🇹🇼 台股核心池 (目標 45%｜65%週/35%月)", "0050", "00631L",
    data["TW"], data["p_631"], s_0050, s_631, new_cash * POOL_TARGET["TW"]
)
us_tot, us_1x, us_2x = render_core_pool(
    "🇺🇸 美股核心池 (目標 45%｜50%週/50%月)", "00662", "00670L",
    data["US"], data["p_670"], s_662, s_670, new_cash * POOL_TARGET["US"]
)

# 3. 費半衛星池
st.divider()
st.subheader("⚡ 費半衛星池 (目標 10%｜00830 原型)")
se_info = data["SEMI"]
p_se = se_info["price"]
se_add = new_cash * POOL_TARGET["SEMI"]
se_val = s_830 * p_se
se_tot = se_val + se_add
st.caption(f"報價日期：{se_info['date']} ｜ 00830 現價：{p_se:.2f}")

c1, c2, c3 = st.columns(3)
c1.metric("20週 Z值", f"{se_info['z_20w']:+.2f}")
c2.metric("20月 Z值", f"{se_info['z_20m']:+.2f}")
c3.metric("綜合積分 S", f"{se_info['score']:+.2f}")

s_se, zw_se = se_info["score"], se_info["z_20w"]
if s_se >= 2.4:
    st.warning("🔴 費半極度過熱：暫緩追高，新資金可先轉存核心池或現金")
elif s_se <= -0.4:
    st.info("🟣 底部週線翻正：分批補倉時機" if zw_se > 0.2 else "🔵 空頭修正中：維持原型抱緊，嚴控比例")
else:
    st.success("🟢 正常區間：依紀律定期定額買進")

if se_add > 0 and s_se < 2.4:
    st.write(f"💼 池內總資產：**NT$ {se_tot:,.0f}** ｜ 💵 新資金 NT$ {se_add:,.0f} 建議買進 00830 **{int(se_add // p_se):,}** 股")

# ================= 整體資產與真實槓桿總覽 =================
st.divider()
st.subheader("🌐 五檔整體資產與風控總覽")
grand_tot = tw_tot + us_tot + se_tot
sh_tw = tw_tot / grand_tot if grand_tot > 0 else 0
sh_us = us_tot / grand_tot if grand_tot > 0 else 0
sh_se = se_tot / grand_tot if grand_tot > 0 else 0
total_exp = (tw_1x + us_1x + se_val) + 2.0 * (tw_2x + us_2x)
net_asset = grand_tot - ext_debt
real_lev = total_exp / net_asset if net_asset > 0 else 0.0

g1, g2 = st.columns(2)
g1.metric("五檔總投資市值", f"NT$ {grand_tot:,.0f}")
g2.metric("整體真實槓桿倍率", f"{real_lev:.2f}x")

st.write(f"📊 **目前三池占比**：台股 `{sh_tw*100:.1f}%` (目標45%) ｜ 美股 `{sh_us*100:.1f}%` (目標45%) ｜ 費半 `{sh_se*100:.1f}%` (目標10%)")

max_dev = max(abs(sh_tw - 0.45), abs(sh_us - 0.45), abs(sh_se - 0.10))
if max_dev > 0.10:
    st.warning("🔔 跨池占比已偏離目標逾 10%，下次新資金建議優先補足占比偏低的池子！")
else:
    st.success("✅ 三池整體比例健康（皆在 10% 容許範圍內）")

st.caption("🛡️ 紀律提醒：條件觸發照表操課、不猜低點；請務必將生活緊急預備金與投資部位完全獨立切分。")
