import streamlit as st
import pandas as pd
import requests
from utils import fetch_prices, build_portfolio


GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRuGnzrAYvgUgaFSpz42NXbcC7RdjJjzwGw60klafFOLioQbf4S0zAu8RsnRdlYih8L8y9q37z0vpze/pub?output=csv"

st.title("📊 持仓明细")

# 读取持仓数据

holdings = pd.read_csv(GOOGLE_SHEET_URL)
holdings["amount"] = pd.to_numeric(holdings["amount"])
holdings["buy_price"] = pd.to_numeric(holdings["buy_price"])

# 拉取价格
def fetch_prices():
    url = "https://www.okx.com/api/v5/market/tickers?instType=SPOT"
    r = requests.get(url)
    data = r.json()["data"]
    df = pd.DataFrame(data)
    df = df[["instId", "last", "open24h", "vol24h"]]
    df["last"] = df["last"].astype(float)
    df["open24h"] = df["open24h"].astype(float)
    df["vol24h"] = df["vol24h"].astype(float)
    return df

prices = fetch_prices()
portfolio = build_portfolio(holdings, prices)

# 组合
portfolio = pd.merge(holdings, prices, left_on="symbol", right_on="instId", how="left")
portfolio["current_value"] = portfolio["amount"] * portfolio["last"]
portfolio["cost"] = portfolio["amount"] * portfolio["buy_price"]
portfolio["pnl_$"] = portfolio["current_value"] - portfolio["cost"]
portfolio["pnl_%"] = (portfolio["pnl_$"] / portfolio["cost"]) * 100

# 展示表格
st.dataframe(portfolio[["symbol", "amount", "buy_price", "last",
                        "open24h", "vol24h", "cost", "current_value", "pnl_$", "pnl_%"]])

# Top5
st.subheader("📉 涨跌幅排行榜")
top_gainers = portfolio.sort_values("pnl_%", ascending=False).head(5)
top_losers = portfolio.sort_values("pnl_%", ascending=True).head(5)

col1, col2 = st.columns(2)
with col1:
    st.bar_chart(top_gainers.set_index("symbol")["pnl_%"])
with col2:
    st.bar_chart(top_losers.set_index("symbol")["pnl_%"])
