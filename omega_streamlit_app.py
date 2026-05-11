import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="OMEGA Entropy Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
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
""", unsafe_allow_html=True)

class ThermodynamicEngine:
    def __init__(self):
        self.gamma = 0.3
        self.alpha = 0.5
        self.beta = 0.8
        self.H_smoothed = 0
        self.last_entropy = 0

    def add_data_point(self, price_series, volume_series=None):
        prices = price_series.values
        volumes = volume_series.values if volume_series is not None else np.ones(len(prices))
        
        window_size = min(30, len(prices))
        recent_prices = prices[-window_size:]
        entropy = self.calculate_shannon_entropy(recent_prices)
        self.H_smoothed = 0.7 * self.H_smoothed + 0.3 * entropy
        
        dH_dt = entropy - self.last_entropy
        radar = self.beta * dH_dt
        self.last_entropy = entropy
        
        theoretical_values = []
        V_prev = prices[0]
        
        for i in range(len(prices)):
            if i == 0:
                V_t = prices[0]
            else:
                P_curr = prices[i]
                P_prev = prices[i-1]
                
                if P_prev > 0 and V_prev > 0:
                    log_return = np.log(P_curr / P_prev)
                    inertia_factor = 1 + self.H_smoothed * self.gamma
                    correction = self.alpha * np.log(P_prev / V_prev)
                    exponent = (log_return / inertia_factor) + correction
                    V_t = V_prev * np.exp(exponent)
                else:
                    V_t = P_curr
            
            theoretical_values.append(V_t)
            V_prev = V_t
        
        theoretical_values = np.array(theoretical_values)
        
        avg_vol = np.mean(volumes[-30:]) if len(volumes) > 0 else 1
        current_vol = volumes[-1] if len(volumes) > 0 else 1
        volume_multiplier = np.sqrt(current_vol / (avg_vol if avg_vol > 0 else 1))
        
        current_price = prices[-1]
        current_theo = theoretical_values[-1]
        spread = ((current_price - current_theo) / current_theo) * 100
        
        inertia = 1 + self.H_smoothed * self.gamma
        
        return {
            'prices': prices,
            'theoretical_values': theoretical_values,
            'entropy': entropy,
            'spread': spread,
            'inertia': inertia,
            'radar': radar,
            'volume_multiplier': volume_multiplier,
            'current_price': current_price,
            'theoretical_price': current_theo,
        }
    
    def calculate_shannon_entropy(self, prices):
        if len(prices) < 2:
            return 0
        
        min_p = np.min(prices)
        max_p = np.max(prices)
        bins = 10
        price_range = max_p - min_p if max_p > min_p else 1
        
        hist, _ = np.histogram(prices, bins=bins, range=(min_p, min_p + price_range))
        hist = hist[hist > 0]
        
        probabilities = hist / len(prices)
        entropy = -np.sum(probabilities * np.log(probabilities + 1e-10))
        
        return entropy
    
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
        "POLKA": "Polkadot",
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
        "IBM": "IBM",
    },
    "FINANCE": {
        "JPM": "JPMorgan Chase",
        "BAC": "Bank of America",
        "WFC": "Wells Fargo",
        "GS": "Goldman Sachs",
        "BLK": "BlackRock",
        "SCHW": "Charles Schwab",
    },
    "HEALTHCARE": {
        "JNJ": "Johnson & Johnson",
        "UNH": "UnitedHealth",
        "PFE": "Pfizer",
        "ABBV": "AbbVie",
        "MRK": "Merck",
    },
    "ENERGY": {
        "XOM": "ExxonMobil",
        "CVX": "Chevron",
        "MPC": "Marathon Petroleum",
        "COP": "ConocoPhillips",
    },
    "CONSUMER": {
        "WMT": "Walmart",
        "KO": "Coca-Cola",
        "MCD": "McDonald's",
        "PG": "Procter & Gamble",
        "COST": "Costco",
    },
    "INDICES": {
        "^GSPC": "S&P 500",
        "^IXIC": "NASDAQ",
        "^DJI": "Dow Jones",
        "^FTSE": "FTSE 100",
        "^FCHI": "CAC 40",
    },
    "ETF": {
        "SPY": "S&P 500 ETF",
        "QQQ": "Nasdaq ETF",
        "IWM": "Russell 2000",
        "GLD": "Gold ETF",
        "TLT": "US Bonds",
    },
}

@st.cache_data(ttl=300)
def fetch_market_data(ticker, period="60d"):
    try:
        data = yf.download(ticker, period=period, progress=False)
        return data
    except Exception as e:
        st.error(f"Error fetching {ticker}: {str(e)}")
        return None

def format_currency(value, decimals=2):
    try:
        if value is None or pd.isna(value):
            return "$0.00"
        return f"${float(value):,.{decimals}f}"
    except:
        return "$0.00"

st.sidebar.markdown("### ⚡ OMEGA Entropy Terminal")
st.sidebar.markdown("Thermodynamic market analysis with ALL 5 formulas")
st.sidebar.markdown("---")

category = st.sidebar.selectbox("📁 Category", list(ASSETS_DB.keys()))

asset_name = st.sidebar.selectbox(
    "📊 Select Asset",
    list(ASSETS_DB[category].values())
)

ticker = None
for t, name in ASSETS_DB[category].items():
    if name == asset_name:
        ticker = t
        break

st.sidebar.markdown("---")

period = st.sidebar.radio("📅 Period", ["30d", "60d", "90d", "6mo", "1y"], index=0)

auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh (60s)", value=True)

if auto_refresh:
    st.markdown('<meta http-equiv="refresh" content="60">', unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown("""
### 5 Official Thermodynamic Formulas

**1️⃣ Motor of Value (V_t)**
V_t = V_{t-1} × exp((ln(P_t/P_{t-1})/(1+H_t·γ)) + α·ln(P_{t-1}/V_{t-1}))

**2️⃣ Entropic Friction (H)**
H = -Σ p_i · ln(p_i)

**3️⃣ Mass Multiplier (M_t)**
M_t = √(Q_t / Q̄)

**4️⃣ Transition Radar (R_t)**
R_t = β · (dH/dt)

**5️⃣ Decision Spread (Δ)**
Δ = (P_real - V_theo) / V_theo
""")

st.markdown(f"## {asset_name} ({ticker}) - Live Analysis")
st.markdown(f"*Updated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}*")

with st.spinner(f"Fetching real data for {ticker}..."):
    data = fetch_market_data(ticker, period)

if data is None or len(data) < 10:
    st.error(f"Could not fetch data for {ticker}. Try a different asset.")
    st.stop()

engine = ThermodynamicEngine()
metrics = engine.add_data_point(data['Close'], data.get('Volume'))

col1, col2, col3, col4 = st.columns(4)

with col1:
    current_price = metrics['current_price']
    prev_close = data['Close'].iloc[-2] if len(data) > 1 else current_price
    price_change = ((current_price - prev_close) / prev_close) * 100
    
    st.metric(
        "Current Price",
        format_currency(current_price),
        f"{price_change:+.2f}%"
    )

with col2:
    st.metric(
        "Theoretical Value (F1)",
        format_currency(metrics['theoretical_price']),
        f"{(metrics['theoretical_price'] - prev_close) / prev_close * 100:+.2f}%"
    )

with col3:
    st.metric(
        "Spread (Δ) - F5",
        f"{metrics['spread']:+.2f}%",
        f"Signal: {engine.get_trade_signal(metrics['spread'])[1]}"
    )

with col4:
    st.metric(
        "Shannon Entropy (F2)",
        f"{metrics['entropy']:.3f} bits",
        "Market disorder"
    )

st.markdown("---")

trade_signal, icon = engine.get_trade_signal(metrics['spread'])

if trade_signal == "BUY":
    st.markdown(f"<div class='trade-signal-buy'>{icon} BUY SIGNAL - Asset {abs(metrics['spread']):.2f}% undervalued</div>", unsafe_allow_html=True)
elif trade_signal == "SELL":
    st.markdown(f"<div class='trade-signal-sell'>{icon} SELL SIGNAL - Asset {metrics['spread']:.2f}% overvalued</div>", unsafe_allow_html=True)
else:
    st.markdown(f"<div class='trade-signal-hold'>{icon} HOLD - Market in equilibrium ({metrics['spread']:+.2f}%)</div>", unsafe_allow_html=True)

st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### ⚙️ Thermodynamic Parameters")
    st.metric("Inertia Factor (γ)", f"{metrics['inertia']:.3f}")
    st.metric("Transition Radar (F4)", f"{metrics['radar']:.4f}")
    st.metric("Mass Multiplier (F3)", f"{metrics['volume_multiplier']:.3f}x")

with col2:
    st.markdown("### 📊 Price Statistics")
    st.metric("Highest (30d)", format_currency(data['Close'].max()))
    st.metric("Lowest (30d)", format_currency(data['Close'].min()))
    st.metric("Average", format_currency(data['Close'].mean()))

with col3:
    st.markdown("### 📈 Volatility Metrics")
    daily_returns = data['Close'].pct_change().dropna()
    volatility = daily_returns.std() * np.sqrt(252) * 100
    st.metric("Annualized Volatility", f"{volatility:.2f}%")
    st.metric("Daily Std Dev", f"{daily_returns.std() * 100:.4f}%")

st.markdown("---")

st.markdown("## 📊 Real-time Analysis Charts")

fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.12,
    row_heights=[0.7, 0.3],
    subplot_titles=("Price vs Theoretical Value (Formula 1)", "Shannon Entropy (Formula 2)")
)

dates = data.index
prices = data['Close'].values
theo_values = metrics['theoretical_values']

fig.add_trace(
    go.Scatter(x=dates, y=prices, name="Market Price", 
               line=dict(color="#0d9488", width=2.5),
               fill='tozeroy', fillcolor='rgba(13, 148, 136, 0.1)'),
    row=1, col=1
)

fig.add_trace(
    go.Scatter(x=dates, y=theo_values, name="Theoretical Value",
               line=dict(color="#6b7280", width=2, dash='dash'),
               fill=None),
    row=1, col=1
)

rolling_entropy = []
for i in range(len(prices)):
    window = min(30, i + 1)
    recent = prices[max(0, i - window + 1):i + 1]
    ent = engine.calculate_shannon_entropy(recent)
    rolling_entropy.append(ent)

fig.add_trace(
    go.Bar(x=dates, y=rolling_entropy, name="Entropy", marker_color="#f59e0b"),
    row=2, col=1
)

fig.update_layout(
    height=700,
    hovermode='x unified',
    template='plotly_white',
    font=dict(family="Inter, sans-serif", size=11, color="#6b7280"),
    title_text=f"{ticker} - Thermodynamic Analysis",
    showlegend=True,
)

fig.update_xaxes(title_text="Date", row=2, col=1)
fig.update_yaxes(title_text=f"Price ({ticker})", row=1, col=1)
fig.update_yaxes(title_text="Entropy (bits)", row=2, col=1)

st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

st.markdown("## 🤖 AI Entropy Assistant")

col1, col2 = st.columns([4, 1])

with col1:
    user_input = st.text_input("Ask about formulas, entropy, signals, or market state:", placeholder="e.g., What's the entropy? Is this a buy?")

with col2:
    send_button = st.button("Send", use_container_width=True)

def generate_ai_response(query):
    lower_query = query.lower()
    
    if 'entropy' in lower_query or 'formula 2' in lower_query:
        level = "🔴 HIGH (turbulent)" if metrics['entropy'] > 2.5 else "🟡 MODERATE" if metrics['entropy'] > 1.5 else "🟢 LOW (stable)"
        return f"**FORMULA 2 - Shannon Entropy: {metrics['entropy']:.3f} bits** | Level: {level}\n\nHigh entropy = more market disorder and unpredictability."
    
    elif 'formula 1' in lower_query or 'theoretical' in lower_query:
        return f"**FORMULA 1 - Motor of Value (V_t): {format_currency(metrics['theoretical_price'])}**\n\nCurrent Price: {format_currency(metrics['current_price'])}\nDifference: {metrics['spread']:+.2f}%"
    
    elif 'formula 3' in lower_query or 'volume' in lower_query or 'mass' in lower_query:
        return f"**FORMULA 3 - Mass Multiplier (M_t): {metrics['volume_multiplier']:.3f}x**\n\nVolume validation factor for price movements."
    
    elif 'formula 4' in lower_query or 'radar' in lower_query or 'transition' in lower_query:
        return f"**FORMULA 4 - Transition Radar (R_t): {metrics['radar']:.4f}**\n\nEntropy acceleration (dH/dt). {'⚠️ High change!' if abs(metrics['radar']) > 0.1 else '✓ Stable'}"
    
    elif 'formula 5' in lower_query or 'spread' in lower_query or 'signal' in lower_query:
        return f"**FORMULA 5 - Decision Spread (Δ): {metrics['spread']:+.2f}%**\n\nCurrent Signal: {trade_signal}\nBUY if < -3.5% | SELL if > +3.5%"
    
    elif 'buy' in lower_query or 'compra' in lower_query:
        if trade_signal == "BUY":
            return f"🟢 **BUY SIGNAL ACTIVE!**\n\n{ticker} is **{abs(metrics['spread']):.2f}% UNDERVALUED** vs theoretical value.\n\nTheoretical (F1): {format_currency(metrics['theoretical_price'])}\nCurrent: {format_currency(metrics['current_price'])}"
        else:
            return f"❌ No BUY signal. Current spread: {metrics['spread']:+.2f}%\n\nNeed spread < -3.5% to trigger BUY."
    
    elif 'sell' in lower_query or 'vendi' in lower_query:
        if trade_signal == "SELL":
            return f"🔴 **SELL SIGNAL ACTIVE!**\n\n{ticker} is **{metrics['spread']:.2f}% OVERVALUED** vs theoretical value.\n\nTheoretical (F1): {format_currency(metrics['theoretical_price'])}\nCurrent: {format_currency(metrics['current_price'])}"
        else:
            return f"❌ No SELL signal. Current spread: {metrics['spread']:+.2f}%\n\nNeed spread > +3.5% to trigger SELL."
    
    else:
        return f"**{ticker} Thermodynamic Summary (All 5 Formulas):**\n\n📊 **F1 Theoretical Value:** {format_currency(metrics['theoretical_price'])}\n🌪️ **F2 Entropy:** {metrics['entropy']:.3f} bits\n⚖️ **F3 Mass Multiplier:** {metrics['volume_multiplier']:.3f}x\n🔌 **F4 Transition Radar:** {metrics['radar']:.4f}\n🎯 **F5 Spread:** {metrics['spread']:+.2f}%\n\n⚡ **Signal:** {trade_signal}\n\nAsk about any formula (1-5), entropy, signals, or market state!"

if send_button and user_input:
    st.info(f"**You:** {user_input}")
    response = generate_ai_response(user_input)
    st.success(f"**OMEGA AI:** {response}")

st.markdown("---")

with st.expander("📋 View detailed price data"):
    display_data = data[['Close']].tail(20).copy()
    display_data.columns = ['Close Price']
    display_data['Close Price'] = display_data['Close Price'].apply(lambda x: format_currency(x))
    st.dataframe(display_data, use_container_width=True)

st.markdown("---")
st.markdown("""
### ⚠️ Disclaimer

This is an **educational tool** demonstrating thermodynamic market analysis. 
- **NOT financial advice**
- **NOT a trading system**
- Historical performance ≠ future results
- Always consult a financial advisor before trading
""")
