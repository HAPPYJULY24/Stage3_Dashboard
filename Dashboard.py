import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import sys
import os
from .utils import fetch_prices, build_portfolio
from utils import send_alert

# 获取 Dust Hunters 根目录（Dashboard.py 的上两级目录）
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

print(">>> sys.path:", sys.path[:3])  # 调试用，确认路径已加入

# ========== 基础设置 ==========
st.set_page_config(page_title="Crypto Dashboard", layout="wide")
st.title("🚀 Crypto Portfolio Dashboard")

# ========== 读取 Google Sheet ==========
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRuGnzrAYvgUgaFSpz42NXbcC7RdjJjzwGw60klafFOLioQbf4S0zAu8RsnRdlYih8L8y9q37z0vpze/pub?output=csv"

@st.cache_data
def load_data():
    df = pd.read_csv(SHEET_URL)
    return df

try:
    holdings = load_data()
except Exception as e:
    st.error("❌ 无法读取 Google Sheet，请检查链接或网络。")
    st.stop()

prices = fetch_prices()
portfolio = build_portfolio(holdings, prices)

# ========== 数据预处理 ==========
holdings = pd.read_csv(SHEET_URL)
holdings["amount"] = pd.to_numeric(holdings["amount"], errors="coerce")
holdings["buy_price"] = pd.to_numeric(holdings["buy_price"], errors="coerce")

# 合并最新价格
portfolio = pd.merge(holdings, prices, left_on="symbol", right_on="symbol", how="left")
portfolio["last"] = portfolio["last"].fillna(portfolio["buy_price"])  # 如果价格缺失，用买入价代替
portfolio["current_value"] = portfolio["amount"] * portfolio["last"]

# ========== 核心指标 ==========
st.header("📊 投资组合总览")
total_cost = (portfolio["buy_price"] * portfolio["amount"]).sum()
current_value = portfolio["current_value"].sum()
pnl_value = current_value - total_cost
pnl_percent = (pnl_value / total_cost * 100) if total_cost > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 总投入", f"${total_cost:,.2f}")
col2.metric("📈 当前价值", f"${current_value:,.2f}")
col3.metric("⚡ 总盈亏金额", f"${pnl_value:,.2f}")
col4.metric("🔥 总盈亏百分比", f"{pnl_percent:.2f}%")

st.markdown("---")

# ---- 持仓分布饼图（基于当前价值） ----
st.subheader("📌 持仓分布（按当前市值）")
pie_data = portfolio.groupby("symbol")["current_value"].sum().reset_index()
fig_pie = px.pie(pie_data, names="symbol", values="current_value", hole=0.4, title="Portfolio Allocation")
st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")

# ========== 涨跌幅 Top 3 ==========
st.subheader("📊 涨跌幅 Top 3")
portfolio["pnl_percent"] = (portfolio["last"] - portfolio["buy_price"]) / portfolio["buy_price"] * 100

top_gainers = portfolio.sort_values("pnl_percent", ascending=False).head(3)
top_losers = portfolio.sort_values("pnl_percent", ascending=True).head(3)

col1, col2 = st.columns(2)
with col1:
    st.markdown("**🚀 涨幅 Top 3**")
    st.table(top_gainers[["symbol", "pnl_percent", "current_value"]].round(2))

with col2:
    st.markdown("**📉 跌幅 Top 3**")
    st.table(top_losers[["symbol", "pnl_percent", "current_value"]].round(2))


# ========== 新增全局指标 ==========

st.markdown("---")
st.header("🌍 全局总览")

# 1. 组合价值曲线 (Net Worth Over Time)
st.subheader("💹 组合价值曲线")
# 如果你有历史数据，可以替换这里
net_worth = pd.DataFrame({
    "date": pd.date_range(end=pd.Timestamp.today(), periods=7),
    "value": [current_value * (1 + i*0.01) for i in range(7)]  # 占位数据：每天+1%
})
fig_networth = px.line(net_worth, x="date", y="value", title="Net Worth Over Time")
st.plotly_chart(fig_networth, use_container_width=True)


# 2. 24h 盈亏曲线
st.subheader("⏱️ 过去24h 盈亏曲线")

# 识别空投：buy_price = 0
portfolio["is_airdrop"] = portfolio["buy_price"].astype(float) == 0

if "change24h_percent" in prices.columns:  
    # 普通币种：用成本计算 24h PnL
    portfolio["pnl_24h"] = portfolio.apply(
        lambda row: row["current_value"] * row["change24h_percent"] / 100 
        if not row["is_airdrop"] else row["current_value"],  # 空投直接取当前价值作为 PnL
        axis=1
    )

    # ✅ 用户选择是否包含空投
    show_airdrops = st.checkbox("显示空投币种 🎁", value=False)

    if not show_airdrops:
        portfolio = portfolio[~portfolio["is_airdrop"]]  # 去掉空投

    # 按 symbol 汇总
    df_24h = portfolio.groupby("symbol")[["pnl_24h", "is_airdrop"]].sum().reset_index()

    # 颜色：亏损浅红，盈利绿色
    df_24h["color"] = df_24h["pnl_24h"].apply(lambda x: "lightcoral" if x < 0 else "lightgreen")

    # 柱状图
    fig_24h = px.bar(
        df_24h,
        x="symbol",
        y="pnl_24h",
        color="color",
        color_discrete_map="identity",
        title="24h PnL by Asset"
    )

    # 如果用户选择显示空投，加标记
    if show_airdrops:
        airdrops = df_24h[df_24h["is_airdrop"] > 0]
        for _, row in airdrops.iterrows():
            fig_24h.add_annotation(
                x=row["symbol"],
                y=row["pnl_24h"],
                text="🎁 空投",
                showarrow=True,
                arrowhead=2,
                font=dict(color="black", size=12, family="Arial")
            )

    st.plotly_chart(fig_24h, use_container_width=True)

else:
    st.info("⚠️ 24h 涨跌数据未提供，需在 fetch_prices() 中加入。")




# 3. 最大回撤 + 稳定币占比
st.subheader("⚠️ 风险提示")
# 最大回撤 (用上面 net_worth 占位曲线计算)
cum_max = net_worth["value"].cummax()
drawdown = (net_worth["value"] - cum_max) / cum_max
max_drawdown = drawdown.min()

stablecoins = ["USDT", "USDC", "BUSD", "DAI", "TUSD"]
stable_value = portfolio[portfolio["symbol"].isin(stablecoins)]["current_value"].sum()
stable_ratio = stable_value / current_value * 100 if current_value > 0 else 0

col1, col2 = st.columns(2)
col1.metric("📉 最大回撤", f"{max_drawdown:.2%}")
col2.metric("💵 稳定币占比", f"{stable_ratio:.2f}%")


# 4. 贡献度图表
st.subheader("📊 币种盈亏贡献")
portfolio["pnl"] = (portfolio["last"] - portfolio["buy_price"]) * portfolio["amount"]
contrib = portfolio.groupby("symbol")["pnl"].sum().reset_index()
fig_contrib = px.bar(contrib, x="symbol", y="pnl", title="PnL Contribution by Asset")
st.plotly_chart(fig_contrib, use_container_width=True)
