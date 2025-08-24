import streamlit as st
import pandas as pd
from utils import fetch_prices, build_portfolio   # ✅ 直接复用 utils.py


GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRuGnzrAYvgUgaFSpz42NXbcC7RdjJjzwGw60klafFOLioQbf4S0zAu8RsnRdlYih8L8y9q37z0vpze/pub?output=csv"

st.title("📊 持仓明细")

# 读取持仓数据
holdings = pd.read_csv(GOOGLE_SHEET_URL)
holdings["amount"] = pd.to_numeric(holdings["amount"], errors="coerce")
holdings["buy_price"] = pd.to_numeric(holdings["buy_price"], errors="coerce")

# 拉取价格 & 组合
prices = fetch_prices()
portfolio = build_portfolio(holdings, prices)

# 展示表格
st.dataframe(portfolio[[
    "symbol", "amount", "buy_price", "last",
    "open24h", "cost", "current_value", "pnl_$", "pnl_%"
]])

# Top5
st.subheader("📉 涨跌幅排行榜")
top_gainers = portfolio[portfolio["pnl_%"].notnull()].sort_values("pnl_%", ascending=False).head(5)
top_losers = portfolio[portfolio["pnl_%"].notnull()].sort_values("pnl_%", ascending=True).head(5)

col1, col2 = st.columns(2)
with col1:
    st.bar_chart(top_gainers.set_index("symbol")["pnl_%"])
with col2:
    st.bar_chart(top_losers.set_index("symbol")["pnl_%"])
