import requests
import pandas as pd
import streamlit as st

# 获取 OKX 最新价格
@st.cache_data(ttl=60)
def fetch_prices():
    url = "https://www.okx.com/api/v5/market/tickers?instType=SPOT"
    try:
        r = requests.get(url)
        data = r.json()["data"]
        df = pd.DataFrame(data)
        df = df[["instId", "last"]]
        df["last"] = df["last"].astype(float)
        return df
    except:
        st.warning("⚠️ 无法获取 OKX 实时价格，将使用买入价代替")
        return pd.DataFrame(columns=["instId", "last"])

# 构建组合数据
def build_portfolio(holdings, prices):
    merged = pd.merge(holdings, prices, left_on="symbol", right_on="instId", how="left")
    merged["last"] = merged["last"].fillna(merged["buy_price"])  # 修正 chained assignment
    merged["current_value"] = merged["amount"] * merged["last"]
    merged["cost"] = merged["amount"] * merged["buy_price"]
    merged["pnl_$"] = merged["current_value"] - merged["cost"]
    merged["pnl_%"] = (merged["pnl_$"] / merged["cost"]) * 100
    return merged
