import requests
import pandas as pd
import streamlit as st
import os
from dotenv import load_dotenv

# 读取 .env 配置
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CMC_API_KEY = os.getenv("CMC_API_KEY")


# ========== OKX 实时价格 ==========
@st.cache_data(ttl=60)
def fetch_okx_prices():
    url = "https://www.okx.com/api/v5/market/tickers?instType=SPOT"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            st.warning("⚠️ OKX API 返回空数据")
            return pd.DataFrame(columns=["instId", "last", "open24h", "change24h_percent", "source"])

        df = pd.DataFrame(data)
        df = df[["instId", "last", "open24h"]].copy()
        df["last"] = pd.to_numeric(df["last"], errors="coerce")
        df["open24h"] = pd.to_numeric(df["open24h"], errors="coerce")
        df["change24h_percent"] = (df["last"] - df["open24h"]) / df["open24h"] * 100
        df["source"] = "OKX"

        # 提取基础币 symbol
        df["symbol"] = df["instId"].str.split("-").str[0]
        return df

    except Exception as e:
        st.warning(f"⚠️ 无法获取 OKX 实时价格 ({e})")
        return pd.DataFrame(columns=["instId", "last", "open24h", "change24h_percent", "source", "symbol"])


# ========== CoinMarketCap 数据抓取 ==========
@st.cache_data(ttl=300)
def fetch_cmc_prices(limit: int = 500):
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
    headers = {'X-CMC_PRO_API_KEY': CMC_API_KEY}
    params = {'start': '1', 'limit': str(limit), 'convert': 'USD'}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            st.warning("⚠️ CMC 返回空数据")
            return pd.DataFrame()

        df = pd.DataFrame([{
            "symbol": coin['symbol'],
            "name": coin['name'],
            "last": coin['quote']['USD']['price'],
            "open24h": coin['quote']['USD']['price'] / (1 + coin['quote']['USD']['percent_change_24h']/100),
            "change24h_percent": coin['quote']['USD']['percent_change_24h'],
            "source": "CMC"
        } for coin in data])
        return df

    except Exception as e:
        st.warning(f"⚠️ 无法获取 CMC 数据 ({e})")
        return pd.DataFrame()


# ========== 合并 OKX + CMC ==========
def fetch_all_prices():
    df_okx = fetch_okx_prices()
    df_cmc = fetch_cmc_prices()
    df_all = pd.concat([df_okx, df_cmc], ignore_index=True)
    return df_all


# 构建组合数据
def build_portfolio(holdings, prices):
    # 用 symbol 对齐，而不是 instId
    merged = pd.merge(holdings, prices, on="symbol", how="left")
    merged["last"] = merged["last"].fillna(merged["buy_price"])
    merged["current_value"] = merged["amount"] * merged["last"]
    merged["cost"] = merged["amount"] * merged["buy_price"]
    merged["pnl_$"] = merged["current_value"] - merged["cost"]
    merged["pnl_%"] = (merged["pnl_$"] / merged["cost"]) * 100
    return merged


# ========== Telegram 警报 ==========
def send_alert(msg: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"⚠️ Telegram 警报发送失败: {e}")
