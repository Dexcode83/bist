import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import warnings
from datetime import datetime

# Uyarıları gizle
warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════
# 1. SAYFA AYARLARI
# ═══════════════════════════════════════════════════════════
st.set_page_config(page_title="BIST TrendScout Pro", page_icon="📈", layout="wide")

st.markdown("""
<style>
    .main-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 12px; text-align: center; color: white; margin-bottom: 1.5rem; }
    .ai-card { background: linear-gradient(135deg, #667eea22, #764ba222); padding: 1rem; border-radius: 10px; border-left: 4px solid #667eea; margin: 1rem 0; }
    .metric-val { font-size: 1.5rem; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# 2. MANUEL GÖSTERGE HESAPLAYICILARI (pandas-ta YOK)
# ═══════════════════════════════════════════════════════════
def calculate_indicators(df, params):
    """pandas-ta kullanmadan, saf pandas/numpy ile tüm göstergeleri hesaplar"""
    df = df.copy()
    c, h, l, v = df['Close'], df['High'], df['Low'], df['Volume']
    
    # RSI(14)
    delta = c.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-8)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # ADX(14)
    tr = pd.concat([h - l, abs(h - c.shift(1)), abs(l - c.shift(1))], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    plus_dm = h.diff().clip(lower=0)
    minus_dm = (-l.diff()).clip(lower=0)
    plus_di = 100 * (plus_dm.rolling(14).mean() / (atr + 1e-8))
    minus_di = 100 * (minus_dm.rolling(14).mean() / (atr + 1e-8))
    dx = 100 * abs(plus_di - minus_di) / ((plus_di + minus_di) + 1e-8)
    df['ADX'] = dx.rolling(14).mean()
    
    # ROC(10)
    df['ROC'] = c.pct_change(10) * 100
    
    # CMF(20)
    mf = ((c - l) - (h - c)) / ((h - l) + 1e-8)
    df['CMF'] = (mf * v).rolling(20).sum() / v.rolling(20).sum()
    
    # EMA'lar
    df['EMA50'] = c.ewm(span=50, adjust=False).mean()
    df['EMA200'] = c.ewm(span=200, adjust=False).mean()
    
    # Hacim Z-Skor
    vol_m = v.rolling(20).mean()
    vol_s = v.rolling(20).std()
    df['VOL_Z'] = (v - vol_m) / (vol_s + 1e-8)
    
    # Değişim Yüzdesi
    df['Degisim_%'] = c.pct_change() * 100
    
    return df

# ═══════════════════════════════════════════════════════════
# 3. VERİ & ANALİZ
# ═══════════════════════════════════════════════════════════
@st.cache_data(ttl=3600)
def fetch_tickers():
    try:
        url = "https://scanner.tradingview.com/turkey/scan"
        res = requests.post(url, json={"filter": [{"left": "exchange", "operation": "equal", "right": "BIST"}], "columns": ["name"]}, timeout=10).json()
        return [f"{x['d'][0].replace('BIST:','')}.IS" for x in res.get('data', []) if len(x['d'][0])<=5]
    except:
        return ['THYAO.IS', 'ASELS.IS', 'GARAN.IS', 'EREGL.IS', 'KCHOL.IS']

def analyze_stock(symbol, params):
    try:
        df = yf.Ticker(symbol).history(period="6mo")
        if len(df) < 50: return None
        
        df = calculate_indicators(df, params)
        d = df.iloc[-1]
        
        # Filtreler
        if not (d['VOL_Z'] > params['vol_z'] and d['CMF'] > params['cmf'] and 
                d['RSI'] > params['rsi'] and d['ROC'] > params['roc'] and
                d['Close'] > d['EMA50'] > d['EMA200']):
            return None
            
        # Skorlama
        base = 50
        if d['ADX'] > params['adx_guclu']: base = 85
        elif d['ADX'] > params['adx_trend']: base = 70
        skor = int(min(100, base + d['VOL_Z'] * 1.5))
        
        return {
            "Hisse": symbol.replace(".IS",""),
            "Fiyat": round(d["Close"],2),
            "Degisim_%": round(d["Degisim_%"],2),
            "RSI": round(d["RSI"],1),
            "ADX": round(d["ADX"],1),
            "CMF": round(d["CMF"],3),
            "Hacim_Z": round(d["VOL_Z"],2),
            "Skor": skor,
            "Trend": "Güçlü 🔥" if base > 80 else "Yükseliş 📈"
        }
    except: return None

# ═══════════════════════════════════════════════════════════
# 4. UI & AKIŞ
# ═══════════════════════════════════════════════════════════
st.markdown("<div class='main-header'><h1>🚀 BIST TrendScout PRO v4.0</h1><p>Python 3.14 Uyumlu | Saf Pandas Motoru</p></div>", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Parametreler")
    params = {
        "rsi": st.slider("Min RSI", 30, 80, 55),
        "roc": st.slider("Min ROC(%)", -10, 30, 5),
        "vol_z": st.slider("Hacim Z-Skor", 1.0, 4.0, 2.0, 0.1),
        "cmf": st.slider("Min CMF", -0.3, 0.3, 0.0, 0.05),
        "adx_trend": st.slider("ADX Trend", 15, 35, 20),
        "adx_guclu": st.slider("ADX Güçlü", 25, 50, 30)
    }
    
    if st.button("🔍 Analiz Başlat", type="primary", width="stretch"):
        tickers = fetch_tickers()
        progress = st.progress(0, text="Taranıyor...")
        results = []
        for i, sym in enumerate(tickers):
            progress.progress((i+1)/len(tickers), text=f"{sym} ({i+1}/{len(tickers)})")
            res = analyze_stock(sym, params)
            if res: results.append(res)
        progress.empty()
        st.session_state.results = pd.DataFrame(results) if results else pd.DataFrame()
        st.success(f"✅ {len(results)} hisse bulundu." if results else "⚠️ Sonuç yok.")

# Sonuçlar
if "results" in st.session_state and not st.session_state.results.empty:
    df_res = st.session_state.results
    
    # Tablo Renklendirme (Pandas 3.x uyumlu)
    def color_row(row):
        if row['Skor'] >= 75: return ['background-color: #00cc0044'] * len(row)
        if row['Skor'] >= 50: return ['background-color: #ffaa0044'] * len(row)
        return ['background-color: #ff444444'] * len(row)
        
    st.dataframe(df_res.style.apply(color_row, axis=1), width="stretch", height=350)
    
    # İstatistikler
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam", len(df_res))
    c2.metric("Güçlü", len(df_res[df_res["Trend"].str.contains("Güçlü")]))
    c3.metric("Ort. RSI", df_res["RSI"].mean().round(1))
    c4.metric("Ort. Skor", df_res["Skor"].mean().round(1))
    
    # CSV İndir
    csv = df_res.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 CSV İndir", csv, f"bist_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", width="stretch")
    
    # Detay Grafik
    st.markdown("---")
    sel = st.selectbox("Detay Grafik İçin Hisse:", df_res["Hisse"].tolist())
    if sel:
        sym = f"{sel}.IS"
        df = yf.Ticker(sym).history(period="3mo")
        if len(df) > 0:
            df = calculate_indicators(df, params)
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.5, 0.25, 0.25])
            fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"]), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df["EMA50"], line=dict(color="orange"), name="EMA50"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI"), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df["ADX"], name="ADX"), row=3, col=1)
            fig.update_layout(height=600, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, width="stretch")
        else:
            st.warning("Grafik verisi yüklenemedi.")

st.caption("⚠️ Bu uygulama yatırım tavsiyesi değildir. © 2026 TrendScout Pro")
