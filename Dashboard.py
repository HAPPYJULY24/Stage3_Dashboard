import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from utils import fetch_prices, build_portfolio


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
portfolio = pd.merge(holdings, prices, left_on="symbol", right_on="instId", how="left")
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

# ========== 持仓分布 ==========
st.subheader("持仓分布")
pie_data = portfolio.groupby("symbol")["current_value"].sum().reset_index()
fig_pie = px.pie(pie_data, values="current_value", names="symbol", hole=0.4)
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
    st.table(top_gainers[["symbol", "pnl_percent"]].round(2))

with col2:
    st.markdown("**📉 跌幅 Top 3**")
    st.table(top_losers[["symbol", "pnl_percent"]].round(2))
