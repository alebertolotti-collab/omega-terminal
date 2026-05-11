import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings

warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="OMEGA Entropy Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    [data-testid="stMetric"] {
        background-color: #f9fafb;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #e5e7eb;
    }
    h1, h2, h3 {
        color: #111827;
    }
    .trade-signal-buy {
        background: rgba(16, 185, 129, 0.1);
        border: 2px solid #10b981;
        color: #10b981;
        padding: 15px;
        border-radius: 8px;
        font-weight: bold;
        text-align: center;
        font-size: 18px;
    }
    .trade-signal-sell {
        background: rgba(220, 38, 38, 0.1);
        border: 2px solid #dc2626;
        color: #dc2626;
        padding: 15px;
        border-radius: 8px;
        font-weight: bold;
        text-align: center;
        font-size: 18px;
    }
    .trade-signal-hold {
        background: rgba(245, 158, 11, 0.1);
        border: 2px solid #f59e0b;
        color: #f59e0b;
        padding: 15px;
        border-radius: 8px;
        font-weight: bold;
        text-align: center;
        font-size: 18px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

class ThermodynamicEngine:
    def __init__(self):
        self.gamma = 0.3
        self.alpha = 0.5
        self.beta = 0.8
        self.H_smoothed = 0.0
        self.last_entropy = 0.0

    def calculate_shannon_entropy(self, prices):
        prices = np.asarray(prices, dtype=float)
        if len(prices) < 2:
            return 0.0

        min_p = np.min(prices)
        max_p = np.max(prices)
        if max_p <= min_p:
            return 0.0

        hist, _ = np.histogram(prices, bins=10, range=(min_p, max_p))
        hist = hist[hist > 0]
        if len(hist) == 0:
            return 0.0

        probabilities = hist / np.sum(hist)
        entropy = -np.sum(probabilities * np.log(probabilities + 1e-12))
        return float(entropy)

    def add_data_point(self, price_series, volume_series=None):
        prices = np.asarray(price_series, dtype=float)
        volumes = (
            volume_series.to_numpy(dtype=float)
            if volume_series is not None
            else np.ones(len(prices), dtype=float)
        )

        if len(prices) == 0:
            return None

        window_size = min(30, len(prices))
        recent_prices = prices[-window_size:]

        entropy = self.calculate_shannon_entropy(recent_prices)
        self.H_smoothed = 0.7 * self.H_smoothed + 0.3 * entropy
        dH_dt = entropy - self.last_entropy
        radar = self.beta * dH_dt
        self.last_entropy = entropy

        theoretical_values = []
        V_prev = float(prices[0])

        for i in range(len(prices)):
            if i == 0:
                V_t = float(prices[0])
            else:
                P_curr = float(prices[i])
                P_prev = float(prices[i - 1])

                if P_prev > 0 and V_prev > 0 and P_curr > 0:
                    log_return = np.log(P_curr / P_prev)
                    inertia_factor = 1 + self.H_smoothed * self.gamma
                    correction = self.alpha * np.log(max(P_prev / V_prev, 1e-12))
                    exponent = (log_return / max(inertia_factor, 1e-12)) + correction
                    V_t = V_prev * np.exp(exponent)
                else:
                    V_t = P_curr

            theoretical_values.append(float(V_t))
            V_prev = float(V_t)

        theoretical_values = np.array(theoretical_values, dtype=float)

        avg_vol = float(np.mean(volumes[-30:])) if len(volumes) > 0 else 1.0
        current_vol = float(volumes[-1]) if len(volumes) > 0 else 1.0
        volume_multiplier = np.sqrt(current_vol / avg_vol) if avg_vol > 0 else 1.0

        current_price = float(prices[-1])
        current_theo = float(theoretical_values[-1])
        spread = ((current_price - current_theo) / current_theo) * 100 if current_theo != 0 else 0.0
        inertia = 1 + self.H_smoothed * self.gamma

        return {
            "prices": prices,
            "theoretical_values": theoretical_values,
            "entropy": float(entropy),
            "spread": float(spread),
            "inertia": float(inertia),
            "radar": float(radar),
            "volume_multiplier": float(volume_multiplier),
            "current_price": float(current_price),
            "theoretical_price": float(current_theo),
        }

    def get_trade_signal(self, spread):
        if spread < -3.5:
            return "BUY", "📈"
        elif spread > 3.5:
            return "SELL", "📉"
        else:
            return "HOLD", "⏸"


ASSETS_DB = {
    "CRYPTO": {
        "BTC": "Bitcoin",
        "ETH": "Ethereum",
        "XRP": "Ripple",
        "SOL": "Solana",
        "ADA": "Cardano",
        "DOGE": "Dogecoin",
        "LINK": "Chainlink",
        "MATIC": "Polygon",
        "AVAX": "Avalanche",
        "POLKA": "Polkadot"
    },
    "TECH": {
        "AAPL": "Apple",
        "MSFT": "Microsoft",
        "GOOGL": "Alphabet",
        "AMZN": "Amazon",
        "META": "Meta Platforms",
        "NVDA": "NVIDIA",
        "TSLA": "Tesla",
        "CRM": "Salesforce",
        "ADBE": "Adobe",
        "IBM": "IBM"
    },
    "FINANCE": {
        "JPM": "JPMorgan Chase",
        "BAC": "Bank of America",
        "WFC": "Wells Fargo",
        "GS": "Goldman Sachs",
        "BLK": "BlackRock",
        "SCHW": "Charles Schwab"
    },
    "HEALTHCARE": {
        "JNJ": "Johnson & Johnson",
        "UNH": "UnitedHealth",
        "PFE": "Pfizer",
        "ABBV": "AbbVie",
        "MRK": "Merck"
    },
    "ENERGY": {
        "XOM": "ExxonMobil",
        "CVX": "Chevron",
        "MPC": "Marathon Petroleum",
        "COP": "ConocoPhillips"
    },
    "CONSUMER": {
        "WMT": "Walmart",
        "KO": "Coca-Cola",
        "MCD": "McDonald's",
        "PG": "Procter & Gamble",
        "COST": "Costco"
    },
    "INDICES": {
        "^GSPC": "S&P 500",
        "^IXIC": "NASDAQ",
        "^DJI": "Dow Jones",
        "^FTSE": "FTSE 100",
        "^FCHI": "CAC 40"
    },
    "ETF": {
        "SPY": "S&P 500 ETF",
        "QQQ": "Nasdaq ETF",
        "IWM": "Russell 2000",
        "GLD": "Gold ETF",
        "TLT": "US Bonds"
    }
}


@st.cache_data(ttl=300)
def fetch_market_data(ticker, period="60d"):
    try:
        df = yf.download(ticker, period=period, progress=False, auto_adjust=False)
        if df is None or df.empty:
            return None
        return df
    except Exception:
        return None


def format_currency(v):
    try:
        v = float(v)
        if pd.isna(v):
            return "$0.00"
        return f"${v:,.2f}"
    except Exception:
        return "$0.00"


st.sidebar.markdown("### ⚡ OMEGA Entropy Terminal\nThermodynamic market analysis with ALL 5 formulas\n---")
category = st.sidebar.selectbox("📁 Category", list(ASSETS_DB.keys()))
asset_name = st.sidebar.selectbox("📊 Select Asset", list(ASSETS_DB[category].values()))
ticker = [t for t, n in ASSETS_DB[category].items() if n == asset_name][0]

st.sidebar.markdown("---")
period = st.sidebar.radio("📅 Period", ["30d", "60d", "90d", "6mo", "1y"], index=0)
auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh (60s)", value=True)

if auto_refresh:
    st.markdown('<meta http-equiv="refresh" content="60">', unsafe_allow_html=True)

st.sidebar.markdown(
    """
---
### 5 Official Thermodynamic Formulas
**1️⃣ V_t = V_{t-1} × exp((ln(P_t/P_{t-1})/(1+H_t·γ)) + α·ln(P_{t-1}/V_{t-1}))**
**2️⃣ H = -Σ p_i · ln(p_i)**
**3️⃣ M_t = √(Q_t / Q̄)**
**4️⃣ R_t = β · (dH/dt)**
**5️⃣ Δ = (P_real - V_theo) / V_theo**
"""
)

st.markdown(
    f"## {asset_name} ({ticker}) - Live Analysis\n"
    f"*Updated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}*"
)

with st.spinner(f"Fetching real data for {ticker}..."):
    data = fetch_market_data(ticker, period)

if data is None or len(data) < 10:
    st.error(f"Could not fetch data for {ticker}. Try a different asset.")
    st.stop()

engine = ThermodynamicEngine()
metrics = engine.add_data_point(data["Close"], data.get("Volume"))

if metrics is None:
    st.error("Not enough data to compute metrics.")
    st.stop()

col1, col2, col3, col4 = st.columns(4)

pc = float(metrics["current_price"])
pv = float(data["Close"].iloc[-2]) if len(data) > 1 else pc
pc_change = ((pc - pv) / pv * 100) if pv != 0 else 0.0

with col1:
    st.metric("Current Price", format_currency(pc), f"{pc_change:+.2f}%")

tc_change = ((float(metrics["theoretical_price"]) - pv) / pv * 100) if pv != 0 else 0.0
with col2:
    st.metric("Theoretical Value (F1)", format_currency(metrics["theoretical_price"]), f"{tc_change:+.2f}%")

trade_signal, icon = engine.get_trade_signal(metrics["spread"])
with col3:
    st.metric("Spread (Δ) - F5", f"{metrics['spread']:+.2f}%", f"Signal: {icon}")

with col4:
    st.metric("Shannon Entropy (F2)", f"{metrics['entropy']:.3f} bits", "Market disorder")

st.markdown("---")

if trade_signal == "BUY":
    st.markdown(
        f"<div class='trade-signal-buy'>{icon} BUY SIGNAL - Asset {abs(metrics['spread']):.2f}% undervalued</div>",
        unsafe_allow_html=True
    )
elif trade_signal == "SELL":
    st.markdown(
        f"<div class='trade-signal-sell'>{icon} SELL SIGNAL - Asset {metrics['spread']:.2f}% overvalued</div>",
        unsafe_allow_html=True
    )
else:
    st.markdown(
        f"<div class='trade-signal-hold'>{icon} HOLD - Market in equilibrium ({metrics['spread']:+.2f}%)</div>",
        unsafe_allow_html=True
    )

st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### ⚙️ Thermodynamic Parameters")
    st.metric("Inertia Factor (γ)", f"{metrics['inertia']:.3f}")
    st.metric("Transition Radar (F4)", f"{metrics['radar']:.4f}")
    st.metric("Mass Multiplier (F3)", f"{metrics['volume_multiplier']:.3f}x")

with col2:
    st.markdown("### 📊 Price Statistics")
    st.metric("Highest", format_currency(data["Close"].max()))
    st.metric("Lowest", format_currency(data["Close"].min()))
    st.metric("Average", format_currency(data["Close"].mean()))

with col3:
    st.markdown("### 📈 Volatility Metrics")
    daily_returns = data["Close"].pct_change().dropna()
    volatility = daily_returns.std() * np.sqrt(252) * 100 if len(daily_returns) > 1 else 0.0
    daily_std = daily_returns.std() * 100 if len(daily_returns) > 1 else 0.0
    st.metric("Annualized Volatility", f"{volatility:.2f}%")
    st.metric("Daily Std Dev", f"{daily_std:.4f}%")

st.markdown("---\n## 📊 Real-time Analysis Charts")

fig = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.12,
    row_heights=[0.7, 0.3],
    subplot_titles=("Price vs Theoretical Value (Formula 1)", "Shannon Entropy (Formula 2)")
)

dates = data.index
prices = data["Close"].to_numpy(dtype=float)
theo_values = metrics["theoretical_values"]

fig.add_trace(
    go.Scatter(
        x=dates,
        y=prices,
        name="Market Price",
        line=dict(color="#0d9488", width=2.5),
        fill="tozeroy",
        fillcolor="rgba(13, 148, 136, 0.1)"
    ),
    row=1,
    col=1
)

fig.add_trace(
    go.Scatter(
        x=dates,
        y=theo_values,
        name="Theoretical Value",
        line=dict(color="#6b7280", width=2, dash="dash")
    ),
    row=1,
    col=1
)

rolling_entropy = [
    engine.calculate_shannon_entropy(prices[max(0, i - 29):i + 1])
    for i in range(len(prices))
]

fig.add_trace(
    go.Bar(
        x=dates,
        y=rolling_entropy,
        name="Entropy",
        marker_color="#f59e0b"
    ),
    row=2,
    col=1
)

fig.update_layout(
    height=700,
    hovermode="x unified",
    template="plotly_white",
    font=dict(family="Inter, sans-serif", size=11, color="#6b7280"),
    title_text=f"{ticker} - Thermodynamic Analysis",
    showlegend=True
)

fig.update_xaxes(title_text="Date", row=2, col=1)
fig.update_yaxes(title_text=f"Price ({ticker})", row=1, col=1)
fig.update_yaxes(title_text="Entropy", row=2, col=1)

st.plotly_chart(fig, use_container_width=True)

st.markdown("---\n## 🤖 AI Entropy Assistant")
col1, col2 = st.columns([4, 1])

with col1:
    user_input = st.text_input(
        "Ask about formulas, entropy, signals, or market state:",
        placeholder="e.g., What's the entropy? Is this a buy?"
    )

with col2:
    send_button = st.button("Send", use_container_width=True)


def generate_ai_response(q):
    q = q.lower()

    if "entropy" in q or "formula 2" in q:
        level = "🔴 HIGH" if metrics["entropy"] > 2.5 else "🟡 MODERATE" if metrics["entropy"] > 1.5 else "🟢 LOW"
        return f"FORMULA 2 - Shannon Entropy: {metrics['entropy']:.3f} bits | {level}"

    if "formula 1" in q or "theoretical" in q:
        return (
            f"FORMULA 1 - V_t: {format_currency(metrics['theoretical_price'])}\n"
            f"Current: {format_currency(metrics['current_price'])}\n"
            f"Diff: {metrics['spread']:+.2f}%"
        )

    if "formula 3" in q or "volume" in q or "mass" in q:
        return f"FORMULA 3 - M_t: {metrics['volume_multiplier']:.3f}x"

    if "formula 4" in q or "radar" in q:
        return f"FORMULA 4 - R_t: {metrics['radar']:.4f}"

    if "formula 5" in q or "spread" in q or "signal" in q:
        return f"FORMULA 5 - Δ: {metrics['spread']:+.2f}% | Signal: {trade_signal}"

    if "buy" in q or "compra" in q:
        if trade_signal == "BUY":
            return f"BUY! {ticker} is {abs(metrics['spread']):.2f}% undervalued"
        return "No BUY signal"

    if "sell" in q or "vendi" in q:
        if trade_signal == "SELL":
            return f"SELL! {ticker} is {metrics['spread']:.2f}% overvalued"
        return "No SELL signal"

    return (
        f"F1: {format_currency(metrics['theoretical_price'])}\n"
        f"F2: {metrics['entropy']:.3f}\n"
        f"F3: {metrics['volume_multiplier']:.3f}x\n"
        f"F4: {metrics['radar']:.4f}\n"
        f"F5: {metrics['spread']:+.2f}%\n"
        f"Signal: {trade_signal}"
    )


if send_button and user_input:
    st.info(f"You: {user_input}")
    st.success(f"OMEGA: {generate_ai_response(user_input)}")

st.markdown("---")

with st.expander("📋 Price Data"):
    dd = data[["Close"]].tail(20).copy()
    dd.columns = ["Close Price"]
    dd["Close Price"] = dd["Close Price"].apply(format_currency)
    st.dataframe(dd, use_container_width=True)

st.markdown("---\n⚠️ Educational tool - NOT financial advice")
