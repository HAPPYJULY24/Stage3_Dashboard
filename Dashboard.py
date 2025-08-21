import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from utils import fetch_prices, build_portfolio
from utils import send_alert


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

def check_and_alert(holdings_df, threshold=100):
    """
    检查涨幅超过 threshold 的币种，并发送警报
    holdings_df: 持仓表，包含 symbol, amount, buy_price
    threshold: 警报阈值（百分比）
    """
    # 拿到 OKX 最新价格
    price_df = fetch_prices()  # instId, last
    price_map = dict(zip(price_df["instId"], price_df["last"]))

    for _, row in holdings_df.iterrows():
        symbol = row["symbol"]
        amount = row["amount"]
        buy_price = row["buy_price"]

        current_price = price_map.get(symbol)
        if current_price is None:
            continue  # API 没有返回这个币种，跳过

        cost = amount * buy_price
        value = amount * current_price
        profit = value - cost
        gain_pct = (value / cost - 1) * 100

        if gain_pct >= threshold:
            msg = (
                f"🚨 Dust Hunters Alert 🚨\n"
                f"币种：{symbol}\n"
                f"涨幅：+{gain_pct:.2f}%\n"
                f"当前价值：${value:.2f}\n"
                f"收益：+{profit:.2f}"
            )
            send_alert(msg)

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
