import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="OMEGA Entropy Terminal", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
[data-testid="stMetric"] { background-color: #f9fafb; padding: 15px; border-radius: 8px; border: 1px solid #e5e7eb; }
.trade-signal-buy { background: rgba(16,185,129,0.1); border: 2px solid #10b981; color: #10b981; padding: 15px; border-radius: 8px; font-weight: bold; text-align: center; font-size: 18px; }
.trade-signal-sell { background: rgba(220,38,38,0.1); border: 2px solid #dc2626; color: #dc2626; padding: 15px; border-radius: 8px; font-weight: bold; text-align: center; font-size: 18px; }
.trade-signal-hold { background: rgba(245,158,11,0.1); border: 2px solid #f59e0b; color: #f59e0b; padding: 15px; border-radius: 8px; font-weight: bold; text-align: center; font-size: 18px; }
</style>""", unsafe_allow_html=True)

class ThermodynamicEngine:
    def __init__(self):
        self.gamma = 0.3
        self.alpha = 0.5
        self.beta = 0.8
        self.H_smoothed = 0
        self.last_entropy = 0

    def add_data_point(self, price_series, volume_series=None):
        prices = price_series.values.flatten().astype(float)
        volumes = volume_series.values.flatten().astype(float) if volume_series is not None else np.ones(len(prices))
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
                P_prev = float(prices[i-1])
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
        avg_vol = float(np.mean(volumes[-30:])) if len(volumes) > 0 else 1.0
        current_vol = float(volumes[-1]) if len(volumes) > 0 else 1.0
        volume_multiplier = np.sqrt(current_vol / (avg_vol if avg_vol > 0 else 1))
        current_price = float(prices[-1])
        current_theo = float(theoretical_values[-1])
        spread = ((current_price - current_theo) / current_theo) * 100
        inertia = 1 + self.H_smoothed * self.gamma
        return {'prices': prices, 'theoretical_values': theoretical_values, 'entropy': entropy, 'spread': spread, 'inertia': inertia, 'radar': radar, 'volume_multiplier': volume_multiplier, 'current_price': current_price, 'theoretical_price': current_theo}

    def calculate_shannon_entropy(self, prices):
        if len(prices) < 2:
            return 0
        min_p = np.min(prices)
        max_p = np.max(prices)
        price_range = max_p - min_p if max_p > min_p else 1
        hist, _ = np.histogram(prices, bins=10, range=(min_p, min_p + price_range))
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

ASSETS_DB = {"CRYPTO": {"BTC": "Bitcoin", "ETH": "Ethereum", "XRP": "Ripple", "SOL": "Solana", "ADA": "Cardano", "DOGE": "Dogecoin", "LINK": "Chainlink", "MATIC": "Polygon", "AVAX": "Avalanche"}, "TECH": {"AAPL": "Apple", "MSFT": "Microsoft", "GOOGL": "Alphabet", "AMZN": "Amazon", "META": "Meta Platforms", "NVDA": "NVIDIA", "TSLA": "Tesla", "IBM": "IBM"}, "FINANCE": {"JPM": "JPMorgan Chase", "BAC": "Bank of America", "GS": "Goldman Sachs", "BLK": "BlackRock"}, "HEALTHCARE": {"JNJ": "Johnson & Johnson", "UNH": "UnitedHealth", "PFE": "Pfizer", "MRK": "Merck"}, "ENERGY": {"XOM": "ExxonMobil", "CVX": "Chevron", "COP": "ConocoPhillips"}, "CONSUMER": {"WMT": "Walmart", "KO": "Coca-Cola", "MCD": "McDonald's", "COST": "Costco"}, "INDICES": {"^GSPC": "S&P 500", "^IXIC": "NASDAQ", "^DJI": "Dow Jones"}, "ETF": {"SPY": "S&P 500 ETF", "QQQ": "Nasdaq ETF", "GLD": "Gold ETF"}}

@st.cache_data(ttl=300)
def fetch_market_data(ticker, period="60d"):
    try:
        return yf.download(ticker, period=period, progress=False)
    except:
        return None

def fmt(v):
    try:
        return f"${float(v):,.2f}"
    except:
        return "$0.00"

st.sidebar.markdown("### ⚡ OMEGA Entropy Terminal\n---")
category = st.sidebar.selectbox("📁 Category", list(ASSETS_DB.keys()))
asset_name = st.sidebar.selectbox("📊 Asset", list(ASSETS_DB[category].values()))
ticker = [t for t, n in ASSETS_DB[category].items() if n == asset_name][0]
period = st.sidebar.radio("📅 Period", ["30d", "60d", "90d", "6mo", "1y"], index=0)
auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh", value=True)
if auto_refresh:
    st.markdown('<meta http-equiv="refresh" content="60">', unsafe_allow_html=True)
st.sidebar.markdown("""---
### 5 Formule Termodinamiche
**F1:** V_t = V_{t-1} × exp((ln(Pt/Pt-1)/(1+Ht·γ)) + α·ln(Pt-1/Vt-1))
**F2:** H = -Σ p_i · ln(p_i)
**F3:** M_t = √(Q_t / Q̄)
**F4:** R_t = β · (dH/dt)
**F5:** Δ = (P_reale - V_teorico) / V_teorico
γ=0.3, α=0.5, β=0.8
""")

st.markdown(f"## {asset_name} ({ticker}) - Live Analysis\n*{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}*")

with st.spinner("Caricamento dati..."):
    data = fetch_market_data(ticker, period)

if data is None or len(data) < 10:
    st.error(f"Impossibile caricare {ticker}. Prova un altro asset.")
    st.stop()

engine = ThermodynamicEngine()
metrics = engine.add_data_point(data['Close'], data.get('Volume'))

pc = metrics['current_price']
pv = float(data['Close'].iloc[-2]) if len(data) > 1 else pc
pc_change = ((pc - pv) / pv * 100) if pv > 0 else 0.0
tc = metrics['theoretical_price']
tc_change = ((tc - pv) / pv * 100) if pv > 0 else 0.0

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Prezzo Attuale", fmt(pc), f"{pc_change:+.2f}%")
with col2:
    st.metric("Valore Teorico F1", fmt(tc), f"{tc_change:+.2f}%")
with col3:
    st.metric("Spread Δ (F5)", f"{metrics['spread']:+.2f}%", f"{engine.get_trade_signal(metrics['spread'])[1]}")
with col4:
    st.metric("Entropia H (F2)", f"{metrics['entropy']:.3f} bits", "Disordine mercato")

st.markdown("---")
trade_signal, icon = engine.get_trade_signal(metrics['spread'])

if trade_signal == "BUY":
    st.markdown(f"<div class='trade-signal-buy'>{icon} BUY — Asset sottoraffreddato {abs(metrics['spread']):.2f}%</div>", unsafe_allow_html=True)
elif trade_signal == "SELL":
    st.markdown(f"<div class='trade-signal-sell'>{icon} SELL — Asset surriscaldato {metrics['spread']:.2f}%</div>", unsafe_allow_html=True)
else:
    st.markdown(f"<div class='trade-signal-hold'>{icon} HOLD — Mercato in equilibrio ({metrics['spread']:+.2f}%)</div>", unsafe_allow_html=True)

st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("### ⚙️ Parametri Termodinamici")
    st.metric("Inerzia (γ)", f"{metrics['inertia']:.3f}")
    st.metric("Radar R_t (F4)", f"{metrics['radar']:.4f}")
    st.metric("Massa M_t (F3)", f"{metrics['volume_multiplier']:.3f}x")
with col2:
    st.markdown("### 📊 Statistiche Prezzo")
    st.metric("Massimo", fmt(data['Close'].max()))
    st.metric("Minimo", fmt(data['Close'].min()))
    st.metric("Media", fmt(data['Close'].mean()))
with col3:
    st.markdown("### 📈 Volatilità")
    dr = data['Close'].pct_change().dropna()
    vol = float(dr.std()) * np.sqrt(252) * 100
    st.metric("Volatilità Annua", f"{vol:.2f}%")
    st.metric("Std Dev Giornaliera", f"{float(dr.std()) * 100:.4f}%")

st.markdown("---")
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12, row_heights=[0.7, 0.3], subplot_titles=("Prezzo vs Valore Teorico (Formula 1)", "Entropia di Shannon (Formula 2)"))
dates = data.index
prices = metrics['prices']
theo_values = metrics['theoretical_values']
fig.add_trace(go.Scatter(x=dates, y=prices, name="Prezzo Mercato", line=dict(color="#0d9488", width=2.5), fill='tozeroy', fillcolor='rgba(13,148,136,0.1)'), row=1, col=1)
fig.add_trace(go.Scatter(x=dates, y=theo_values, name="Valore Teorico", line=dict(color="#6b7280", width=2, dash='dash')), row=1, col=1)
rolling_entropy = [engine.calculate_shannon_entropy(prices[max(0, i-29):i+1]) for i in range(len(prices))]
fig.add_trace(go.Bar(x=dates, y=rolling_entropy, name="Entropia", marker_color="#f59e0b"), row=2, col=1)
fig.update_layout(height=700, hovermode='x unified', template='plotly_white', showlegend=True)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
col1, col2 = st.columns([4, 1])
with col1:
    user_input = st.text_input("Chiedi dell'entropia, dei segnali, delle formule...", placeholder="es: buy? entropia? formula 1?")
with col2:
    send_button = st.button("Invia")

def ai_response(q):
    q = q.lower()
    if 'entropy' in q or 'entropia' in q or 'formula 2' in q:
        level = "🔴 ALTA" if metrics['entropy'] > 2.5 else "🟡 MEDIA" if metrics['entropy'] > 1.5 else "🟢 BASSA"
        return f"**F2 Shannon Entropy: {metrics['entropy']:.3f} bits** — {level}"
    elif 'formula 1' in q or 'teorico' in q or 'theoretical' in q:
        return f"**F1 Motore del Valore: {fmt(tc)}**\nPrezzo attuale: {fmt(pc)}\nDiff: {metrics['spread']:+.2f}%"
    elif 'formula 3' in q or 'volume' in q or 'massa' in q:
        return f"**F3 Moltiplicatore di Massa: {metrics['volume_multiplier']:.3f}x**"
    elif 'formula 4' in q or 'radar' in q:
        return f"**F4 Radar di Transizione: {metrics['radar']:.4f}**"
    elif 'formula 5' in q or 'spread' in q or 'segnale' in q or 'signal' in q:
        return f"**F5 Spread Decisionale: {metrics['spread']:+.2f}%** — {trade_signal}"
    elif 'buy' in q or 'compra' in q:
        return f"🟢 BUY! {ticker} sottoraffreddato {abs(metrics['spread']):.2f}%" if trade_signal == "BUY" else f"❌ Nessun segnale BUY (spread: {metrics['spread']:+.2f}%)"
    elif 'sell' in q or 'vendi' in q:
        return f"🔴 SELL! {ticker} surriscaldato {metrics['spread']:.2f}%" if trade_signal == "SELL" else f"❌ Nessun segnale SELL (spread: {metrics['spread']:+.2f}%)"
    else:
        return f"**{ticker} — Riepilogo 5 Formule:**\n📊 F1 V_t: {fmt(tc)}\n🌪️ F2 H: {metrics['entropy']:.3f}\n⚖️ F3 M_t: {metrics['volume_multiplier']:.3f}x\n🔌 F4 R_t: {metrics['radar']:.4f}\n🎯 F5 Δ: {metrics['spread']:+.2f}%\n⚡ Segnale: {trade_signal}"

if send_button and user_input:
    st.info(f"Tu: {user_input}")
    st.success(f"OMEGA AI: {ai_response(user_input)}")

st.markdown("---\n⚠️ Solo scopo educativo — NON è consulenza finanziaria")
