# =========================================
# 🚀 BIST TrendScout PRO v3.5 - YFINANCE EDITION
# Python 3.14 & Pandas 3.0 & Streamlit 1.56 Uyumlu
# =========================================

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import time
import logging
import warnings

# Logları temizle
warnings.filterwarnings('ignore')
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.getLogger("requests").setLevel(logging.CRITICAL)

# =========================================
# ⚙️ SAYFA YAPILANDIRMASI
# =========================================
st.set_page_config(
    page_title="BIST TrendScout PRO",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================
# 🎨 CSS STİLİ
# =========================================
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 1.5rem;
        color: white;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 0.3rem 0;
    }
    div[data-testid="stMetricValue"] { font-size: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# =========================================
# 📊 GÖSTERGELER (Saf Pandas/NumPy - pandas-ta gerektirmez)
# =========================================
def calc_ema(series, length):
    return series.ewm(span=length, adjust=False).mean()

def calc_rsi(series, length=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=length).mean()
    avg_loss = loss.rolling(window=length).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calc_adx(high, low, close, length=14):
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
    atr = tr.rolling(window=length).mean()
    plus_di = 100 * (plus_dm.rolling(window=length).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=length).mean() / atr)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    return dx.rolling(window=length).mean()

def calc_cmf(high, low, close, volume, length=20):
    mfm = ((close - low) - (high - close)) / (high - low + 1e-8)
    mfv = mfm * volume
    return mfv.rolling(window=length).sum() / volume.rolling(window=length).sum()

def calc_bbands(close, length=20, std_dev=2):
    sma = close.rolling(window=length).mean()
    std = close.rolling(window=length).std()
    return sma + (std_dev * std), sma, sma - (std_dev * std)

def add_indicators(df):
    df = df.copy()
    df["EMA20"] = calc_ema(df["Close"], 20)
    df["EMA50"] = calc_ema(df["Close"], 50)
    df["SMA200"] = calc_ema(df["Close"], 200) # ewm yerine sma daha stabil
    df["RSI"] = calc_rsi(df["Close"], 14)
    df["ADX"] = calc_adx(df["High"], df["Low"], df["Close"], 14)
    df["CMF"] = calc_cmf(df["High"], df["Low"], df["Close"], df["Volume"], 20)
    
    vol_ma = df["Volume"].rolling(20).mean()
    vol_std = df["Volume"].rolling(20).std()
    df["VOL_Z"] = (df["Volume"] - vol_ma) / (vol_std + 1e-8)
    
    df["BB_UPPER"], df["BB_MID"], df["BB_LOWER"] = calc_bbands(df["Close"])
    df["HH20"] = df["High"].rolling(20).max()
    return df

# =========================================
# 📈 VERİ ÇEKME (Güvenli & Cache'li)
# =========================================
@st.cache_data(ttl=300, show_spinner=False)
def fetch_data(symbol, period="6mo"):
    try:
        df = yf.download(symbol, period=period, progress=False, auto_adjust=True, ignore_tz=True)
        if df.empty or len(df) < 30:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        return df
    except Exception:
        return None

# =========================================
# ⚡ HIZLI FİLTRE & AI YORUM
# =========================================
def fast_filter(symbol):
    df = fetch_data(symbol, period="3mo")
    if df is None: return False
    ema20 = calc_ema(df["Close"], 20).iloc[-1]
    return df["Close"].iloc[-1] > ema20

def ai_comment(row):
    yorum = []
    if row["RSI"] > 70: yorum.append("🔥 Aşırı alım")
    elif row["RSI"] > 60: yorum.append("📈 Momentum güçlü")
    elif row["RSI"] < 30: yorum.append("❄️ Aşırı satım")
    
    if row["ADX"] > 35: yorum.append("🚀 Trend net")
    elif row["ADX"] < 15: yorum.append("🔄 Yatay")
    
    if row["CMF"] > 0.15: yorum.append("💰 Para girişi")
    elif row["CMF"] < -0.1: yorum.append("💸 Para çıkışı")
    
    if row["VOL_Z"] > 2.5: yorum.append("🎯 Hacim patlaması")
    return " | ".join(yorum) if yorum else "➡️ Nötr"

# =========================================
# 🧠 ANA ANALİZ
# =========================================
def analyze_stock(symbol, params):
    df = fetch_data(symbol, period="6mo")
    if df is None or len(df) < 50: return None
    
    df = add_indicators(df)
    d = df.iloc[-1]
    
    kriterler = {
        'trend': d["Close"] > d["EMA50"],
        'rsi': d["RSI"] > params['rsi_min'],
        'adx': d["ADX"] > params['adx_min'],
        'volume': d["VOL_Z"] > params['vol_z_min'],
        'cmf': d["CMF"] > params['cmf_min'],
        'breakout': d["Close"] > df["HH20"].iloc[-2],
        'higher_tf': df["Close"].iloc[-1] > df["SMA200"].iloc[-1]
    }
    
    skor = sum(kriterler.values())
    if skor >= 5:
        trend_cls = "🔥 ÇOK GÜÇLÜ" if d["ADX"] > 35 else "📈 GÜÇLÜ" if d["ADX"] > 25 else "⚠️ ORTA"
        return {
            'Hisse': symbol.replace('.IS', ''),
            'Fiyat': round(d["Close"], 2),
            'Degisim_%': round(((d["Close"]/d["Close"].shift(1))-1)*100, 2),
            'RSI': round(d["RSI"], 1), 'ADX': round(d["ADX"], 1),
            'CMF': round(d["CMF"], 3), 'Hacim_Z': round(d["VOL_Z"], 2),
            'Skor': skor, 'Trend': trend_cls, 'AI_Yorum': ai_comment(d),
            'Destek': round(df["BB_LOWER"].iloc[-1], 2),
            'Direnç': round(df["BB_UPPER"].iloc[-1], 2),
            'df': df
        }
    return None

# =========================================
# 📈 GRAFİK
# =========================================
def plot_chart(df, symbol):
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.04,
                        row_heights=[0.5, 0.15, 0.15, 0.2],
                        subplot_titles=(f"{symbol} Fiyat", "RSI", "ADX", "Hacim"))
    
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_UPPER'], line=dict(color='gray', dash='dot')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_LOWER'], line=dict(color='gray', dash='dot')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA50'], line=dict(color='orange', width=2)), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple')), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
    
    fig.add_trace(go.Scatter(x=df.index, y=df['ADX'], line=dict(color='brown')), row=3, col=1)
    fig.add_hline(y=25, line_dash="dash", line_color="gray", row=3, col=1)
    
    colors = ['green' if c >= o else 'red' for c, o in zip(df['Close'], df['Open'])]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors), row=4, col=1)
    
    fig.update_layout(height=650, xaxis_rangeslider_visible=False, template="plotly_white", hovermode='x unified')
    return fig

# =========================================
# 🎨 ARAYÜZ & AKIŞ
# =========================================
with st.sidebar:
    st.header("⚙️ Parametreler")
    params = {
        'rsi_min': st.slider("Min RSI", 30, 80, 55),
        'adx_min': st.slider("Min ADX", 10, 50, 20),
        'vol_z_min': st.slider("Hacim Z-Skor", 1.0, 4.0, 2.0, 0.1),
        'cmf_min': st.slider("Min CMF", -0.2, 0.2, 0.0, 0.05)
    }
    
    run_btn = st.button("🔍 Analiz Başlat", type="primary", width="stretch")
    if st.button("🔄 Cache Temizle", width="stretch"):
        st.cache_data.clear()
        st.rerun()

st.markdown('<div class="main-header"><h1>📈 BIST TrendScout PRO v3.5</h1><p>yfinance • Saf Pandas • AI Destekli</p></div>', unsafe_allow_html=True)

if run_btn:
    with st.spinner("🔍 BIST hisseleri taranıyor..."):
        progress = st.progress(0)
        status = st.empty()
        hisseler = [f"{t}.IS" for t in ["THYAO","GARAN","AKBNK","EREGL","TUPRS","SISE","BIMAS","ASELS","FROTO","KCHOL","ARCLK","TCELL","ISCTR","VAKBN","YKBNK","HALKB","KOZAL","SASA","GUBRF","TOASO","PETKM","MGROS","DOHOL","ENKAI","KRSAN","OTKAR"]]
        results, skipped = [], 0
        
        for i, sym in enumerate(hisseler):
            progress.progress((i+1)/len(hisseler))
            status.text(f"⏳ {sym} ({i+1}/{len(hisseler)})")
            if not fast_filter(sym):
                skipped += 1
                continue
            res = analyze_stock(sym, params)
            if res: results.append(res)
            if i % 5 == 0: time.sleep(0.05)
        
        progress.empty(); status.empty()
        if results:
            st.session_state.results = results
            st.success(f"✅ Tamamlandı! **{len(results)}** sinyal bulundu ({skipped} elendi)")
        else:
            st.warning("⚠️ Kriterlere uyan hisse bulunamadı. Parametreleri gevşetin.")

if 'results' in st.session_state:
    results = st.session_state.results
    df_t = pd.DataFrame([{k: v for k, v in r.items() if k != 'df'} for r in results])
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🎯 Sinyal", len(results))
    c2.metric("🔥 Çok Güçlü", len([r for r in results if "ÇOK GÜÇLÜ" in r['Trend']]))
    c3.metric("📈 Ort. RSI", round(df_t['RSI'].mean(), 1))
    c4.metric("📊 Ort. ADX", round(df_t['ADX'].mean(), 1))
    
    def highlight(row):
        if "ÇOK GÜÇLÜ" in row['Trend']: return ['background-color: #d4edda']*len(row)
        if "GÜÇLÜ" in row['Trend']: return ['background-color: #fff3cd']*len(row)
        return ['']*len(row)
        
    st.dataframe(df_t.style.map(highlight, subset=['Trend']).format({'Fiyat':'{:.2f}', 'RSI':'{:.1f}', 'ADX':'{:.1f}'}), height=300, width="stretch")
    
    st.subheader("📈 Detay İnceleme")
    col_g, col_i = st.columns([2, 1])
    with col_g:
        sec = st.selectbox("Hisse:", df_t['Hisse'].tolist(), key="sel")
        sec_data = next((r for r in results if r['Hisse'] == sec), None)
        if sec_data: st.plotly_chart(plot_chart(sec_data['df'], sec), width="stretch")
    with col_i:
        if sec_data:
            st.markdown(f"""
            <div class="metric-card">
                <h4>{sec}</h4>
                <p><b>Fiyat:</b> {sec_data['Fiyat']} ({sec_data['Degisim_%']}%)</p>
                <p><b>Trend:</b> {sec_data['Trend']} | <b>Skor:</b> {sec_data['Skor']}/7</p>
                <p><b>Destek/Direnç:</b> {sec_data['Destek']} / {sec_data['Direnç']}</p>
                <hr><p><b>💡 AI:</b><br>{sec_data['AI_Yorum']}</p>
            </div>""", unsafe_allow_html=True)
    
    st.download_button("📥 CSV İndir", df_t.to_csv(index=False).encode('utf-8-sig'), 
                       f"bist_sinyaller_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv", width="stretch")

st.markdown("---")
st.info("⚠️ Bu araç eğitim amaçlıdır. Yatırım tavsiyesi içermez. Veriler yfinance üzerinden alınır, gecikmeler olabilir.")
