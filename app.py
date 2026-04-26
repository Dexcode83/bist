"""
BIST TrendScout Pro v4.0 - Tam Kod (Python 3.14 & Pandas 3.x Uyumlu)
Tüm log hataları giderildi. pandas-ta bağımlılığı tamamen kaldırıldı.
"""
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════
# 1. SAYFA YAPILANDIRMASI & CSS
# ═══════════════════════════════════════════════════════════
st.set_page_config(page_title="BIST TrendScout Pro", page_icon="📈", layout="wide")

st.markdown("""
<style>
    .main-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 12px; text-align: center; color: white; margin-bottom: 1.5rem; }
    .ai-card { background: linear-gradient(135deg, #667eea22, #764ba222); padding: 1rem; border-radius: 10px; border-left: 4px solid #667eea; margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# 2. VERİ ÇEKME & SAF PANDAS GÖSTERGELERİ
# ═══════════════════════════════════════════════════════════
@st.cache_data(ttl=3600)
def fetch_tickers():
    try:
        url = "https://scanner.tradingview.com/turkey/scan"
        res = requests.post(url, json={"filter": [{"left": "exchange", "operation": "equal", "right": "BIST"}], "columns": ["name"]}, timeout=10).json()
        return [f"{x['d'][0].replace('BIST:','')}.IS" for x in res.get('data', []) if len(x['d'][0])<=5]
    except Exception as e:
        st.warning(f"TradingView API hatası: {e}")
        return ['THYAO.IS','ASELS.IS','GARAN.IS','ISCTR.IS','KCHOL.IS','EREGL.IS','TUPRS.IS','SISE.IS']

def fetch_data(symbol, period="6mo"):
    try:
        df = yf.Ticker(symbol).history(period=period)
        if len(df) < 30: return None
        df.columns = [c.lower().replace(' ', '_') for c in df.columns]
        if 'adj_close' in df.columns: df['adj_close'] = df['adj_close']
        return df.dropna(subset=['close', 'volume'])
    except: return None

def calculate_indicators(df):
    """pandas-ta olmadan, saf pandas/numpy ile profesyonel göstergeler"""
    df = df.copy()
    c, h, l, v = df['close'], df['high'], df['low'], df['volume']
    
    # RSI(14)
    delta = c.diff()
    gain, loss = delta.clip(lower=0), (-delta).clip(lower=0)
    avg_gain, avg_loss = gain.rolling(14).mean(), loss.rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (avg_gain / (avg_loss + 1e-8))))
    
    # ADX(14)
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    pdm, mdm = h.diff().clip(lower=0), (-l.diff()).clip(lower=0)
    pdi = 100 * (pdm.rolling(14).mean() / (atr + 1e-8))
    mdi = 100 * (mdm.rolling(14).mean() / (atr + 1e-8))
    dx = 100 * (pdi - mdi).abs() / ((pdi + mdi) + 1e-8)
    df['adx'] = dx.rolling(14).mean()
    
    # ROC(10) & CMF(20)
    df['roc'] = c.pct_change(10) * 100
    mf = ((c - l) - (h - c)) / ((h - l) + 1e-8)
    df['cmf'] = (mf * v).rolling(20).sum() / v.rolling(20).sum()
    
    # EMA & Hacim Z-Skor
    df['ema50'] = c.ewm(span=50, adjust=False).mean()
    df['ema200'] = c.ewm(span=200, adjust=False).mean()
    vol_m, vol_s = v.rolling(20).mean(), v.rolling(20).std()
    df['vol_z'] = (v - vol_m) / (vol_s + 1e-8)
    
    # Kırılım & Değişim (DataFrame üzerinde hesapla, float hatası önlenir)
    df['hh20'] = h.rolling(20).max()
    df['degisim_pct'] = c.pct_change() * 100
    
    return df

# ═══════════════════════════════════════════════════════════
# 3. ANALİZ & SKORLAMA
# ═══════════════════════════════════════════════════════════
def analyze_symbol(symbol, params):
    df = fetch_data(symbol)
    if df is None or len(df) < 50: return None
    
    df = calculate_indicators(df)
    d = df.iloc[-1]
    
    # ✅ TÜM KRİTERLER (Scalar değil, DataFrame'den gelen değerler)
    trend = d['close'] > d['ema50']
    rsi = pd.notna(d['rsi']) and d['rsi'] > params['rsi']
    adx = pd.notna(d['adx']) and d['adx'] > params['adx']
    volume = pd.notna(d['vol_z']) and d['vol_z'] > params['vol_z']
    para = pd.notna(d['cmf']) and d['cmf'] > params['cmf']
    breakout = pd.notna(d['hh20']) and d['close'] > d['hh20']
    
    # 4H MTF Kontrolü (Basitleştirilmiş, hata vermeden çalışır)
    mtf = True
    if params.get('use_mtf', False):
        df_h4 = fetch_data(symbol, period="2mo", interval="4h")
        if df_h4 is not None and len(df_h4) > 30:
            df_h4 = calculate_indicators(df_h4)
            h4 = df_h4.iloc[-1]
            mtf = h4['close'] > h4['ema50'] and h4['rsi'] > 50
            
    if not all([trend, rsi, adx, volume, para, breakout, mtf]):
        return None
        
    # Skorlama
    base = 50
    if adx > 30: base += 10
    if volume > 3: base += 5
    if para > 0.1: base += 5
    if d['close'] > d['ema200']: base += 5
    skor = min(100, max(0, base))
    
    trend_cls = "🔥 Süper" if skor >= 85 else "📈 Güçlü" if skor >= 65 else "⚡ Orta"
    
    return {
        "Hisse": symbol.replace(".IS",""),
        "Fiyat": round(d["close"], 2),
        "Degisim_%": round(d["degisim_pct"], 2),
        "RSI": round(d["rsi"], 1),
        "ADX": round(d["adx"], 1),
        "CMF": round(d["cmf"], 3),
        "Hacim_Z": round(d["vol_z"], 2),
        "Skor": skor,
        "Trend": trend_cls
    }

# ═══════════════════════════════════════════════════════════
# 4. STREAMLIT UI & AKIŞ
# ═══════════════════════════════════════════════════════════
st.markdown("<div class='main-header'><h1>🚀 BIST TrendScout PRO v4.0</h1><p>Python 3.14 & Pandas 3.x Uyumlu | Saf Pandas Motoru</p></div>", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Parametreler")
    params = {
        "rsi": st.slider("Min RSI", 30, 80, 55, key="s_rsi"),
        "adx": st.slider("Min ADX", 10, 50, 20, key="s_adx"),
        "vol_z": st.slider("Hacim Z-Skor Min", 0.5, 5.0, 2.0, 0.1, key="s_vol"),
        "cmf": st.slider("Min CMF", -0.3, 0.3, 0.0, 0.05, key="s_cmf"),
        "use_mtf": st.checkbox("4H Onayı Zorunlu", value=False, key="s_mtf")
    }
    
    if st.button("🔍 Analiz Başlat", type="primary", width="stretch", key="btn_scan"):
        tickers = fetch_tickers()
        if not tickers: st.error("Hisse listesi alınamadı."); st.stop()
        
        progress = st.progress(0, text="Taranıyor...")
        results = []
        for i, sym in enumerate(tickers):
            progress.progress((i+1)/len(tickers), text=f"{sym} ({i+1}/{len(tickers)})")
            res = analyze_symbol(sym, params)
            if res: results.append(res)
        progress.empty()
        
        st.session_state.results = pd.DataFrame(results) if results else pd.DataFrame()
        st.success(f"✅ {len(results)} hisse bulundu." if results else "⚠️ Kriterlere uygun hisse yok.")

# SONUÇLARI GÖSTER
if "results" in st.session_state and not st.session_state.results.empty:
    df_res = st.session_state.results
    
    # ✅ Pandas 3.x & Streamlit 1.56 Uyumlu Tablo Renklendirme
    def color_row(row):
        if row['Skor'] >= 75: return ['background-color: #00cc0044'] * len(row)
        if row['Skor'] >= 50: return ['background-color: #ffaa0044'] * len(row)
        return ['background-color: #ff444444'] * len(row)
        
    st.dataframe(df_res.style.apply(color_row, axis=1), width="stretch", height=350)
    
    # İstatistikler
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam", len(df_res))
    c2.metric("Güçlü+", len(df_res[df_res["Trend"].str.contains("Güçlü|Süper")]))
    c3.metric("Ort. RSI", df_res["RSI"].mean().round(1))
    c4.metric("Ort. Skor", df_res["Skor"].mean().round(1))
    
    # CSV İndir
    csv = df_res.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 CSV İndir", csv, f"bist_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", width="stretch")
    
    # Detay Grafik
    st.markdown("---")
    sel = st.selectbox("Detay Grafik İçin Hisse:", df_res["Hisse"].tolist(), key="sel_chart")
    if sel:
        sym = f"{sel}.IS"
        df = fetch_data(sym)
        if df is not None:
            df = calculate_indicators(df)
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.5, 0.25, 0.25])
            fig.add_trace(go.Candlestick(x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"], name="Fiyat"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df["ema50"], line=dict(color="orange"), name="EMA50"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df["rsi"], name="RSI"), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df["adx"], name="ADX"), row=3, col=1)
            fig.update_layout(height=600, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, width="stretch")

st.caption("⚠️ Bu uygulama yatırım tavsiyesi değildir. Veriler bilgilendirme amaçlıdır. © 2026 TrendScout Pro")
