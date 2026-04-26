"""
BIST TrendScout Pro v3.6 - Python 3.14 & Pandas 3.x Uyumlu
Tüm log hataları giderildi. pandas-ta bağımlılığı kaldırıldı.
"""
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import json
import re
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════
# 1. SAYFA AYARLARI & CSS
# ═══════════════════════════════════════════════════════════
st.set_page_config(page_title="BIST TrendScout Pro", page_icon="📈", layout="wide")

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem; border-radius: 12px; text-align: center; color: white; margin-bottom: 1.5rem;
    }
    .ai-card {
        background: linear-gradient(135deg, #667eea22, #764ba222);
        padding: 1rem; border-radius: 10px; border-left: 4px solid #667eea; margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# 2. VERİ ÇEKME & SAF PANDAS GÖSTERGELERİ (pandas-ta YOK)
# ═══════════════════════════════════════════════════════════
@st.cache_data(ttl=3600)
def fetch_bist_tickers():
    url = "https://scanner.tradingview.com/turkey/scan"
    payload = {"filter": [{"left": "exchange", "operation": "equal", "right": "BIST"}], "columns": ["name"]}
    try:
        res = requests.post(url, json=payload, timeout=10).json()
        tickers = [f"{item['d'][0].replace('BIST:','')}.IS" for item in res.get('data', []) if len(item['d'][0])<=5]
        return list(set(tickers))
    except:
        return ['THYAO.IS','ASELS.IS','GARAN.IS','ISCTR.IS','KCHOL.IS','EREGL.IS','TUPRS.IS','SISE.IS']

def fetch_data(symbol, period="6mo"):
    try:
        df = yf.Ticker(symbol).history(period=period)
        if len(df) < 30: return None
        df.columns = [c.lower().replace(' ', '_') for c in df.columns]
        return df
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
    tr = pd.concat([h-l, abs(h-c.shift(1)), abs(l-c.shift(1))], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    pdm = h.diff().clip(lower=0)
    mdm = (-l.diff()).clip(lower=0)
    pdm = pdm.where(pdm > mdm, 0)
    mdm = mdm.where(mdm > pdm, 0)
    pdi = 100 * (pdm.rolling(14).mean() / (atr + 1e-8))
    mdi = 100 * (mdm.rolling(14).mean() / (atr + 1e-8))
    dx = 100 * abs(pdi - mdi) / ((pdi + mdi) + 1e-8)
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
    
    # Degisim_% (DataFrame üzerinde hesapla, numpy.float64 hatası önlenir)
    df['degisim_pct'] = c.pct_change() * 100
    
    return df

# ═══════════════════════════════════════════════════════════
# 3. ANALİZ & AI MODÜLÜ
# ═══════════════════════════════════════════════════════════
def analyze_stock(symbol, params):
    df = fetch_data(symbol)
    if df is None or len(df) < 50: return None
    
    df = calculate_indicators(df)
    d = df.iloc[-1]
    
    # Filtreler
    if not (d['vol_z'] > params['vol_z'] and d['cmf'] > params['cmf'] and 
            d['rsi'] > params['rsi'] and d['roc'] > params['roc'] and
            d['close'] > d['ema50'] > d['ema200']):
        return None
        
    # Skor & Trend
    adx, base = d['adx'], 50
    if adx > params['adx_guclu']: trend, base = "Güçlü Boğa 🔥", 85
    elif adx > params['adx_trend']: trend, base = "Yükseliş 📈", 70
    else: trend, base = "Zayıf ⚠️", 40
    
    skor = int(min(100, base + d['vol_z']*1.5 + (5 if d['cmf']>0 else -3)))
    
    return {
        "Hisse": symbol.replace(".IS",""),
        "Fiyat": round(d["close"],2),
        "Degisim_%": round(d["degisim_pct"],2),
        "RSI": round(d["rsi"],1),
        "ADX": round(d["adx"],1),
        "CMF": round(d["cmf"],3),
        "Hacim_Z": round(d["vol_z"],2),
        "Skor": skor,
        "Trend": trend
    }

@st.cache_data(ttl=1800)
def get_ai_analysis(symbol, df):
    key = st.secrets.get("DASHSCOPE_API_KEY", "") or st.secrets.get("OPENAI_API_KEY", "")
    if not key: return {"error": "API Key eksik (.streamlit/secrets.toml)"}
    
    d = df.iloc[-1]
    prompt = f"""Sadece teknik analiz yap. Hisse: {symbol}, Fiyat: {d['close']}, RSI: {d['rsi']:.1f}, ADX: {d['adx']:.1f}, ROC: {d['roc']:.1f}, CMF: {d['cmf']:.3f}
Geçerli JSON döndür: {{"öneri": "AL/BEKLE/SAT", "gerekce": "kisa aciklama", "risk": 1-10}}"""
    
    try:
        res = requests.post("https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": "qwen-plus", "messages": [{"role":"user","content": prompt}], "temperature": 0.3},
            timeout=15).json()
        txt = res["choices"][0]["message"]["content"]
        return json.loads(re.sub(r'```(?:json)?\n?|\n?```', '', txt))
    except Exception as e:
        return {"error": str(e)}

# ═══════════════════════════════════════════════════════════
# 4. STREAMLIT UI & AKIŞ
# ═══════════════════════════════════════════════════════════
st.markdown("""<div class="main-header"><h1>🚀 BIST TrendScout Pro v3.6</h1><p>Python 3.14 Uyumlu | Saf Pandas Altyapısı</p></div>""", unsafe_allow_html=True)

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
    btn = st.button("🔍 Analiz Başlat", type="primary", width="stretch")
    ai_toggle = st.toggle("🤖 AI Yorumu", value=True)

if btn:
    tickers = fetch_bist_tickers()
    progress = st.progress(0, text="Taranıyor...")
    results = []
    for i, sym in enumerate(tickers):
        progress.progress((i+1)/len(tickers), text=f"{sym} ({i+1}/{len(tickers)})")
        res = analyze_stock(sym, params)
        if res: results.append(res)
    progress.empty()
    st.session_state.results = pd.DataFrame(results)
    st.success(f"✅ {len(results)} hisse bulundu." if results else "⚠️ Sonuç yok.")

if "results" in st.session_state and not st.session_state.results.empty:
    df_res = st.session_state.results
    
    # 🟢 Pandas 3.x Uyumlu Stil
    def color_row(row):
        if row['Skor'] >= 75: return 'background-color: #00cc0044'
        if row['Skor'] >= 50: return 'background-color: #ffaa0044'
        return 'background-color: #ff444444'
    st.dataframe(df_res.style.apply(color_row, axis=1), width="stretch", height=350)
    
    # İstatistikler
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam", len(df_res))
    c2.metric("Güçlü", len(df_res[df_res["Trend"].str.contains("Güçlü")]))
    c3.metric("Ort. RSI", df_res["RSI"].mean().round(1))
    c4.metric("Ort. Skor", df_res["Skor"].mean().round(1))
    
    # CSV
    csv = df_res.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 CSV İndir", csv, f"bist_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
    
    # Detay & AI
    st.markdown("---")
    sel = st.selectbox("Hisse Seç:", df_res["Hisse"].tolist())
    if sel:
        sym = f"{sel}.IS"
        df = fetch_data(sym)
        if df is not None:
            df = calculate_indicators(df)
            with st.expander("📊 Teknik Grafik", expanded=True):
                fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.5, 0.25, 0.25])
                fig.add_trace(go.Candlestick(x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"]), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df["rsi"], name="RSI"), row=2, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df["adx"], name="ADX"), row=3, col=1)
                fig.update_layout(height=600, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, width="stretch")
                
        if ai_toggle:
            with st.spinner("🤖 Qwen analiz yapıyor..."):
                ai_res = get_ai_analysis(sym, df)
            if "error" in ai_res:
                st.warning(ai_res["error"])
            else:
                st.markdown(f"""<div class="ai-card"><b>🎯 Öneri:</b> {ai_res.get('öneri','N/A')} | <b>Risk:</b> {ai_res.get('risk', '?')}/10<br><i>{ai_res.get('gerekce','')}</i></div>""", unsafe_allow_html=True)

st.caption("⚠️ Bu uygulama yatırım tavsiyesi değildir. Veriler bilgilendirme amaçlıdır. © 2026 TrendScout Pro")
