import requests
import pandas as pd
import streamlit as st
import os
from dotenv import load_dotenv

# 读取 .env 配置（本地开发用）
load_dotenv()

# ===== API Key 配置 =====
def get_secret(key: str, default=None):
    """优先从 st.secrets 读取，其次从环境变量"""
    try:
        return st.secrets.get(key) or os.getenv(key, default)
    except Exception:
        return os.getenv(key, default)

CMC_API_KEY = get_secret("CMC_API_KEY")
BOT_TOKEN = get_secret("BOT_TOKEN")
CHAT_ID = get_secret("CHAT_ID")

if not CMC_API_KEY:
    st.warning("⚠️ 未检测到 CMC_API_KEY，请在 .env 或 Streamlit secrets 中配置")

# ========== CoinMarketCap 数据抓取 ==========
@st.cache_data(ttl=300)
def fetch_cmc_prices(limit: int = 500):
    if not CMC_API_KEY:
        return pd.DataFrame(columns=["symbol", "name", "last", "open24h", "change24h_percent", "source"])

    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
    headers = {'X-CMC_PRO_API_KEY': CMC_API_KEY}
    params = {'start': '1', 'limit': str(limit), 'convert': 'USD'}

    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            st.warning("⚠️ CMC 返回空数据")
            return pd.DataFrame(columns=["symbol", "name", "last", "open24h", "change24h_percent", "source"])

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
        return pd.DataFrame(columns=["symbol", "name", "last", "open24h", "change24h_percent", "source"])


# ========== 用 CMC 作为唯一价格源 ==========
def fetch_prices():
    return fetch_cmc_prices()


# ========== 构建组合数据 ==========
def build_portfolio(holdings, prices):
    # 兼容不同的 symbol 列名
    if "coin" in holdings.columns and "symbol" not in holdings.columns:
        holdings = holdings.rename(columns={"coin": "symbol"})
    if "amount" not in holdings.columns or "buy_price" not in holdings.columns:
        raise ValueError("❌ holdings 文件必须包含 'amount' 和 'buy_price' 列")

    merged = pd.merge(holdings, prices, on="symbol", how="left")
    merged["last"] = merged["last"].fillna(merged["buy_price"])
    merged["current_value"] = merged["amount"] * merged["last"]
    merged["cost"] = merged["amount"] * merged["buy_price"]
    merged["pnl_$"] = merged["current_value"] - merged["cost"]
    merged["pnl_%"] = (merged["pnl_$"] / merged["cost"]) * 100
    return merged


# ========== Telegram 警报 ==========
def send_alert(msg: str):
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️ 未配置 BOT_TOKEN/CHAT_ID，跳过发送 Telegram 警报")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"⚠️ Telegram 警报发送失败: {e}")
