import requests
import pandas as pd
import streamlit as st

BOT_TOKEN = "8381895106:AAEr93DHIwGEEZLlGKKtILuWucUlp0uprEY"  #TG BOT
CHAT_ID = "1527225659" #TG USER ID

# 获取 OKX 最新价格
@st.cache_data(ttl=60)
def fetch_prices():
    url = "https://www.okx.com/api/v5/market/tickers?instType=SPOT"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            st.warning("⚠️ OKX API 返回空数据，将使用买入价代替")
            return pd.DataFrame(columns=["instId", "last", "open24h", "change24h_percent"])
        
        df = pd.DataFrame(data)

        # 打印调试用，看看实际字段
        print("✅ OKX 返回字段:", df.columns.tolist())

        # 兼容字段名（有些可能是 open24h，有些是 open24H）
        open_col = None
        for c in df.columns:
            if c.lower() == "open24h":
                open_col = c
                break
        
        if not {"instId", "last"}.issubset(df.columns) or open_col is None:
            st.warning("⚠️ OKX 返回数据缺少 last/open24h，将使用买入价代替")
            return pd.DataFrame(columns=["instId", "last", "open24h", "change24h_percent"])

        # 只保留需要的列
        df = df[["instId", "last", open_col]].copy()
        df = df.rename(columns={open_col: "open24h"})

        # 转换数值
        df["last"] = pd.to_numeric(df["last"], errors="coerce")
        df["open24h"] = pd.to_numeric(df["open24h"], errors="coerce")
        df = df.dropna(subset=["last", "open24h"])

        # 计算 24h 涨跌幅
        df["change24h_percent"] = (df["last"] - df["open24h"]) / df["open24h"] * 100

        return df

    except Exception as e:
        st.warning(f"⚠️ 无法获取 OKX 实时价格，将使用买入价代替 ({e})")
        return pd.DataFrame(columns=["instId", "last", "open24h", "change24h_percent"])



# 构建组合数据
def build_portfolio(holdings, prices):
    merged = pd.merge(holdings, prices, left_on="symbol", right_on="instId", how="left")
    merged["last"] = merged["last"].fillna(merged["buy_price"])  # 修正 chained assignment
    merged["current_value"] = merged["amount"] * merged["last"]
    merged["cost"] = merged["amount"] * merged["buy_price"]
    merged["pnl_$"] = merged["current_value"] - merged["cost"]
    merged["pnl_%"] = (merged["pnl_$"] / merged["cost"]) * 100
    return merged



def send_alert(msg: str):
    """
    发送 Telegram 警报
    """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"⚠️ Telegram 警报发送失败: {e}")