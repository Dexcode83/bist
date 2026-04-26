"""
BIST TrendScout Pro v4.1 - Stabil & Python 3.14 Uyumlu
✅ pandas-ta kaldırıldı (Manuel Hesaplama)
✅ Yahoo 4h hatası düzeltildi (1h kullanılıyor)
✅ Styler/Applymap hataları giderildi
"""
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time
import warnings

warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════
# 1. VERİ ÇEKME FONKSİYONLARI (Güncellenmiş)
# ═══════════════════════════════════════════════════════════
@st.cache_data(ttl=3600)
def fetch_tickers():
    """TradingView'den BIST hisselerini çeker"""
    try:
        url = "https://scanner.tradingview.com/turkey/scan"
        res = requests.post(url, json={"filter": [{"left": "exchange", "operation": "equal", "right": "BIST"}], "columns": ["name"]}, timeout=10).json()
        return [f"{x['d'][0].replace('BIST:','')}.IS" for x in res.get('data', []) if len(x['d'][0])<=5]
    except:
        return ['THYAO.IS','ASELS.IS','GARAN.IS','ISCTR.IS','KCHOL.IS','EREGL.IS','TUPRS.IS','SISE.IS']

def fetch_data(symbol, period="6mo", interval=None):
    """Veri çeker. İsteğe bağlı interval (1h vb.) destekler."""
    try:
        ticker = yf.Ticker(symbol)
        if interval:
            df = ticker.history(period=period, interval=interval)
        else:
            df = ticker.history(period=period)
            
        if df.empty or len(df) < 30: 
            return None
            
        df.columns = [c.lower().replace(' ', '_') for c in df.columns]
        if 'adj_close' in df.columns: df.rename(columns={'adj_close': 'adj_close'}, inplace=True)
        return df.dropna(subset=['close', 'volume'])
    except Exception:
        return None

# ═══════════════════════════════════════════════════════════
# 2. GÖSTERGE HESAPLAMA (Saf Pandas)
# ═══════════════════════════════════════════════════════════
def calculate_indicators(df):
    df = df.copy()
    c, h, l, v = df['close'], df['high'], df['low'], df['volume']
    
    # RSI(14)
    delta = c.diff()
    gain, loss = delta.clip(lower=0), (-delta).clip(lower=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (avg_gain / (avg_loss + 1e-8))))
    
    # ADX(14)
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    pdm = h.diff().clip(lower=0)
    mdm = (-l.diff()).clip(lower=0)
    pdi = 100 * (pdm.rolling(14).mean() / (atr + 1e-8))
    mdi = 100 * (mdm.rolling(14).mean() / (atr + 1e-8))
    dx = 100 * (pdi - mdi).abs() / ((pdi + mdi) + 1e-8)
    df['adx'] = dx.rolling(14).mean()
    
    # CMF(20) & ROC(10)
    mf = ((c - l) - (h - c)) / ((h - l) + 1e-8)
    df['cmf'] = (mf * v).rolling(20).sum() / v.rolling(20).sum()
    df['roc'] = c.pct_change(10) * 100
    
    # EMA
    df['ema50'] = c.ewm(span=50, adjust=False).mean()
    df['ema200'] = c.ewm(span=200, adjust=False).mean()
    
    # Hacim Z-Skor
    vol_m = v.rolling(20).mean()
    vol_s = v.rolling(20).std()
    df['vol_z'] = (v - vol_m) / (vol_s + 1e-8)
    
    return df

# ═══════════════════════════════════════════════════════════
# 3. ANALİZ & SKORLAMA
# ═══════════════════════════════════════════════════════════
def analyze_symbol(symbol, params):
    # Günlük Veri
    df = fetch_data(symbol, period="6mo")
    if df is None or len(df) < 50: return None
    
    df = calculate_indicators(df)
    d = df.iloc[-1]
    
    # 1. Günlük Filtreler
    trend = d['close'] > d['ema50'] > d['ema200']
    rsi = pd.notna(d['rsi']) and d['rsi'] > params['rsi']
    adx = pd.notna(d['adx']) and d['adx'] > params['adx']
    vol = pd.notna(d['vol_z']) and d['vol_z'] > params['vol_z']
    cmf = pd.notna(d['cmf']) and d['cmf'] > 0.0
    
    # 2. MTF (Çoklu Zaman Dilimi) Kontrolü - DÜZELTİLDİ
    mtf = True # Varsayılan olarak True (filtrelemeyi engellememesi için)
    if params.get('use_mtf', False):
        try:
            # Yahoo 4h desteklemiyor, 1h (60d) kullanıyoruz
            df_h = fetch_data(symbol, period="60d", interval="1h")
            if df_h is not None and len(df_h) > 50:
                df_h = calculate_indicators(df_h)
                h = df_h.iloc[-1]
                # 1 Saatlikte RSI>50 ve Fiyat>EMA50 olmalı
                mtf = h['close'] > h['ema50'] and h['rsi'] > 50
        except Exception:
            mtf = True # Veri çekilemezse hisseyi elme

    # 3. Tüm Şartlar Sağlanıyor mu?
    if not all([trend, rsi, adx, vol, cmf, mtf]):
        return None
        
    # 4. Skorlama
    base = 50
    if adx > 30: base += 10
    if vol > 3.0: base += 10
    if cmf > 0.15: base += 5
    skor = min(100, max(0, int(base)))
    
    trend_cls = "🔥 Süper" if skor >= 80 else "📈 Güçlü" if skor >= 60 else "⚡ Orta"
    
    return {
        "Hisse": symbol.replace(".IS",""),
        "Fiyat": round(d["close"], 2),
        "RSI": round(d["rsi"], 1),
        "ADX": round(d["adx"], 1),
        "CMF": round(d["cmf"], 3),
        "Hacim_Z": round(d["vol_z"], 2),
        "Skor": skor,
        "Trend": trend_cls
    }

# ═══════════════════════════════════════════════════════════
# 4. UI & STREAMLIT AKIŞI
# ═══════════════════════════════════════════════════════════
st.set_page_config(page_title="BIST TrendScout Pro", page_icon="📈", layout="wide")

st.markdown("<div style='background:linear-gradient(135deg,#667eea,#764ba2);padding:1rem;border-radius:10px;text-align:center;color:white'><h1>🚀 BIST TrendScout PRO</h1><p>Stabil & Hızlı Tarama (Python 3.14 Uyumlu)</p></div>", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Parametreler")
    params = {
        "rsi": st.slider("Min RSI", 30, 80, 55),
        "adx": st.slider("Min ADX", 10, 50, 20),
        "vol_z": st.slider("Min Hacim Z", 1.0, 5.0, 2.0, 0.1),
        "use_mtf": st.checkbox("🔍 1 Saatlik Onay (Yavaşlar)", value=False)
    }
    
    if st.button("🚀 Analizi Başlat", type="primary", width="stretch"):
        tickers = fetch_tickers()
        if not tickers: st.error("Hisse listesi alınamadı."); st.stop()
        
        progress = st.progress(0, text="Taranıyor...")
        results = []
        
        for i, sym in enumerate(tickers):
            progress.progress((i+1)/len(tickers), text=f"{sym} ({i+1}/{len(tickers)})")
            res = analyze_symbol(sym, params)
            if res: results.append(res)
            time.sleep(0.02) # Yahoo Rate Limit koruması
            
        progress.empty()
        st.session_state.results = pd.DataFrame(results)
        st.success(f"✅ {len(results)} hisse bulundu." if results else "⚠️ Sonuç yok.")

if "results" in st.session_state and not st.session_state.results.empty:
    df_res = st.session_state.results
    
    # Tablo Renklendirme (Pandas 3.x List Dönüşü)
    def color_row(row):
        if row['Skor'] >= 80: return ['background-color: #00cc0044'] * len(row)
        if row['Skor'] >= 60: return ['background-color: #ffaa0044'] * len(row)
        return ['background-color: #ff444444'] * len(row)
        
    st.dataframe(df_res.style.apply(color_row, axis=1), width="stretch", height=350)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam", len(df_res))
    c2.metric("Güçlü+", len(df_res[df_res["Trend"].str.contains("Süper|Güçlü")]))
    c3.metric("Ort. RSI", df_res["RSI"].mean().round(1))
    c4.metric("Ort. Skor", df_res["Skor"].mean().round(1))

    # Grafik Detay
    st.markdown("---")
    sel = st.selectbox("Hisse Seç:", df_res["Hisse"].tolist())
    if sel:
        sym = f"{sel}.IS"
        df = fetch_data(sym, "3mo")
        if df is not None:
            df = calculate_indicators(df)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"], name="Fiyat"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df["ema50"], line=dict(color="orange"), name="EMA50"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df["rsi"], name="RSI"), row=2, col=1)
            fig.update_layout(height=500)
            st.plotly_chart(fig, width="stretch")
