"""
BIST TrendScout Pro v2.2 - Web Arayüzü (pandas-ta + Qwen AI versiyonu)
Yazar: TrendScout AI
Sürüm: 2.2.0
Not: .streamlit/secrets.toml dosyasına DASHSCOPE_API_KEY eklenmelidir.
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta
import requests
import json
import re
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════
# 1. SAYFA YAPILANDIRMASI & CSS
# ═══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="BIST TrendScout Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
        color: white;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #e9ecef;
        margin: 0.5rem 0;
    }
    .stDataFrame { font-size: 0.9rem; }
    .ai-card {
        background: linear-gradient(135deg, #667eea22, #764ba222);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# 2. VERİ ÇEKME & HAZIRLIK FONKSİYONLARI
# ═══════════════════════════════════════════════════════════
@st.cache_data(ttl=3600)
def fetch_bist_tickers():
    """TradingView'den BIST hisselerini çeker, başarısız olursa fallback döner"""
    url = "https://scanner.tradingview.com/turkey/scan"
    payload = {
        "filter": [{"left": "exchange", "operation": "equal", "right": "BIST"}],
        "options": {"lang": "tr"},
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": ["name"]
    }
    
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        data = r.json()
        tickers = []
        for item in data.get("data", []):
            name = item.get("d", [None])[0]
            if name:
                clean = name.replace("BIST:", "").strip().upper()
                if 3 <= len(clean) <= 5 and clean.isalpha():
                    tickers.append(f"{clean}.IS")
        return list(set(tickers))
    except Exception as e:
        st.warning(f"⚠️ TradingView API hatası: {e}")
        return [
            'THYAO.IS', 'ASELS.IS', 'GARAN.IS', 'ISCTR.IS', 'KCHOL.IS',
            'SISE.IS', 'TUPRS.IS', 'PETKM.IS', 'EREGL.IS', 'FROTO.IS',
            'SAHOL.IS', 'BIMAS.IS', 'TTKOM.IS', 'YKBNK.IS', 'AKBNK.IS',
            'KOZAL.IS', 'EKGYO.IS', 'TOASO.IS', 'OTKAR.IS', 'DOHOL.IS'
        ]

@st.cache_data(ttl=300)
def fetch_stock_data(symbol: str, period: str = "6mo") -> pd.DataFrame | None:
    """yfinance ile veri çeker ve temel validasyon yapar"""
    try:
        df = yf.Ticker(symbol).history(period=period)
        if df.empty or len(df) < 30:
            return None
        df.columns = df.columns.str.lower()
        if 'adj close' in df.columns:
            df.rename(columns={'adj close': 'adj_close'}, inplace=True)
        df = df.dropna(subset=['close', 'volume'])
        return df
    except Exception as e:
        st.warning(f"Veri hatası ({symbol}): {str(e)}")
        return None

# ═══════════════════════════════════════════════════════════
# 3. TEKNİK GÖSTERGELER (pandas-ta)
# ═══════════════════════════════════════════════════════════
def calculate_indicators(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """pandas-ta ile profesyonel gösterge hesaplaması"""
    df = df.copy()
    
    # Temel Göstergeler
    df["RSI"] = ta.rsi(df["close"], length=params.get("rsi_period", 14))
    
    adx_df = ta.adx(df["high"], df["low"], df["close"], length=params.get("adx_period", 14))
    df["ADX"] = adx_df[f"ADX_{params.get('adx_period', 14)}"]
    
    df["ROC"] = ta.roc(df["close"], length=params.get("momentum_period", 10))
    df["CMF"] = ta.cmf(df["high"], df["low"], df["close"], df["volume"], length=20)
    
    # Trend Filtreleri
    df["EMA50"] = ta.ema(df["close"], length=50)
    df["EMA200"] = ta.ema(df["close"], length=200)
    
    # Hacim İstatistikleri (Z-Score)
    vol_mean = df["volume"].rolling(20).mean()
    vol_std = df["volume"].rolling(20).std()
    df["VOL_Z"] = (df["volume"] - vol_mean) / (vol_std + 1e-8)
    
    # Ek Göstergeler (Grafik için)
    macd_df = ta.macd(df["close"])
    df["MACD"] = macd_df["MACD_12_26_9"]
    df["MACD_SIGNAL"] = macd_df["MACDs_12_26_9"]
    
    bb_df = ta.bbands(df["close"], length=20, std=2)
    df["BB_UPPER"] = bb_df["BBU_20_2.0"]
    df["BB_LOWER"] = bb_df["BBL_20_2.0"]
    
    stoch_df = ta.stochrsi(df["close"], length=14)
    df["STOCHRSI_K"] = stoch_df["STOCHRSI_K_14_14_3_3"]
    
    return df

# ═══════════════════════════════════════════════════════════
# 4. HİSSE ANALİZ & SKORLAMA
# ═══════════════════════════════════════════════════════════
def analyze_stock(symbol: str, params: dict) -> dict | None:
    df = fetch_stock_data(symbol, period="6mo")
    if df is None or len(df) < 50:
        return None
        
    df = calculate_indicators(df, params)
    last = df.iloc[-1]
    
    # Kriter Kontrolü
    vol_spike = last["VOL_Z"] > params.get("hacim_z_min", 2.0)
    cmf_bullish = last["CMF"] > params.get("cmf_min", 0.0)
    ema_bullish = last["close"] > last["EMA50"] > last["EMA200"] if params.get("use_ema_filter") else True
    rsi_ok = last["RSI"] > params["rsi_min"]
    roc_ok = last["ROC"] > params["momentum_min"]
    
    if not (vol_spike and cmf_bullish and rsi_ok and roc_ok and ema_bullish):
        return None
        
    # Trend & Skor Hesaplama
    adx = last["ADX"]
    if adx > params["adx_guclu_min"] and ema_bullish:
        trend, trend_class, base_score = "Güçlü Boğa 🔥", "strong_bull", 85
    elif adx > params["adx_guclu_min"]:
        trend, trend_class, base_score = "Güçlü Trend 📊", "strong", 70
    elif adx > params["adx_trend_min"] and ema_bullish:
        trend, trend_class, base_score = "Yükseliş Başlangıcı 📈", "new_bull", 60
    elif adx > params["adx_trend_min"]:
        trend, trend_class, base_score = "Trend Oluşuyor ⚡", "new", 50
    else:
        trend, trend_class, base_score = "Zayıf/Yatay ⚠️", "weak", 35
        
    # Skor modifikatörleri
    score = base_score + min(10, last["VOL_Z"] * 1.5) + (5 if cmf_bullish else -3)
    score = int(min(100, max(0, score)))
    
    return {
        "Hisse": symbol.replace(".IS", ""),
        "Fiyat": round(last["close"], 2),
        "RSI": round(last["RSI"], 1),
        "Momentum": round(last["ROC"], 1),
        "ADX": round(adx, 1),
        "CMF": round(last["CMF"], 3),
        "Hacim_Z": round(last["VOL_Z"], 2),
        "Skor": score,
        "Trend": trend,
        "Trend_Class": trend_class
    }

# ═══════════════════════════════════════════════════════════
# 5. GRAFİK OLUŞTURMA (Plotly)
# ═══════════════════════════════════════════════════════════
def create_chart(symbol: str, df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=("Fiyat & Trend", "RSI & StochRSI", "ADX & CMF", "Hacim Z-Score"),
        row_heights=[0.45, 0.2, 0.175, 0.175]
    )
    
    # Fiyat + EMA + BB
    fig.add_trace(go.Candlestick(x=df.index, open=df["open"], high=df["high"],
                                 low=df["low"], close=df["close"], name="Fiyat"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA50"], line=dict(color="orange"), name="EMA50"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA200"], line=dict(color="purple", width=2), name="EMA200"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["BB_UPPER"], line=dict(color="gray", dash="dot"), name="BB Üst"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["BB_LOWER"], line=dict(color="gray", dash="dot", fill="tonexty"), name="BB Alt"), row=1, col=1)
    
    # RSI & StochRSI
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], line=dict(color="blue"), name="RSI"), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["STOCHRSI_K"], line=dict(color="cyan", width=1), name="StochRSI"), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
    
    # ADX & CMF
    fig.add_trace(go.Scatter(x=df.index, y=df["ADX"], line=dict(color="purple"), name="ADX"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["CMF"], line=dict(color="green"), name="CMF"), row=3, col=1)
    fig.add_hline(y=25, line_dash="dash", line_color="gray", row=3, col=1)
    fig.add_hline(y=0, line_dash="solid", line_color="rgba(128,128,128,0.3)", row=3, col=1)
    
    # Hacim Z-Score
    colors = np.where(df["VOL_Z"] > 2, "#ff4444", np.where(df["VOL_Z"] < -2, "#44ff44", "#888888"))
    fig.add_trace(go.Bar(x=df.index, y=df["VOL_Z"], name="Hacim Z", marker_color=colors), row=4, col=1)
    fig.add_hline(y=2, line_dash="dash", line_color="red", row=4, col=1)
    
    fig.update_layout(
        title=f"{symbol} - Gelişmiş Teknik Analiz", height=850,
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

# ═══════════════════════════════════════════════════════════
# 6. QWEN AI ANALİZ MODÜLÜ
# ═══════════════════════════════════════════════════════════
@st.cache_data(ttl=1200)
def generate_ai_analysis(symbol: str, df: pd.DataFrame, params: dict) -> dict:
    """Qwen/DashScope API ile teknik analiz yorumu üretir"""
    api_key = st.secrets.get("DASHSCOPE_API_KEY", "") or st.secrets.get("OPENAI_API_KEY", "")
    if not api_key:
        return {"error": "⚠️ API anahtarı eksik. `.streamlit/secrets.toml` dosyasına `DASHSCOPE_API_KEY` ekleyin."}
        
    try:
        last = df.iloc[-1]
        prev = df.iloc[-7] if len(df) >= 7 else df.iloc[0]
        
        context = f"""
Hisse: {symbol} | Fiyat: {last['close']:.2f} TL | Haftalık: {((last['close']/prev['close'])-1)*100:+.2f}%
RSI(14): {last['RSI']:.1f} | ADX(14): {last['ADX']:.1f} | ROC(10): {last['ROC']:.1f}%
CMF(20): {last['CMF']:.3f} | Hacim Z-Score: {last['VOL_Z']:.1f}
EMA50: {last['EMA50']:.2f} | EMA200: {last['EMA200']:.2f}
BB Üst: {last['BB_UPPER']:.2f} | BB Alt: {last['BB_LOWER']:.2f}
"""
        prompt = f"""Sen uzman bir teknik analiz asistanısın. Sadece verdiğim göstergelere dayanarak kısa, net ve yatırımçı dostu bir rapor hazırla.

{context}

SADECE GEÇERLİ JSON DÖNDÜR. Format:
{{
  "ozet": "2 cümlelik durum özeti",
  "trend_yonü": "Yükseliş/Düşüş/Yatay",
  "kisa_vade_beklenti": "1-2 hafta hedef",
  "destek_seviyesi": float,
  "direnç_seviyesi": float,
  "risk_puanı": 1-10,
  "öneri": "AL/BEKLE/SAT",
  "gerekce": "Teknik gerekçe",
  "dikkat": ["madde1", "madde2"]
}}
"""
        # DashScope / OpenAI Compatible Endpoint
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "qwen-plus",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "response_format": {"type": "json_object"}
        }
        
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        res.raise_for_status()
        content = res.json()["choices"][0]["message"]["content"]
        
        # JSON temizleme
        clean = re.sub(r'```(?:json)?\n?|\n?```', '', content).strip()
        return json.loads(clean)
        
    except Exception as e:
        return {"error": f"AI hatası: {str(e)}"}

# ═══════════════════════════════════════════════════════════
# 7. STREAMLIT UI & ANA AKIŞ
# ═══════════════════════════════════════════════════════════
st.markdown("""<div class="main-header"><h1>🚀 BIST TrendScout Pro v2.2</h1><p>pandas-ta + Qwen AI Destekli Akıllı Hisse Tarama</p></div>""", unsafe_allow_html=True)

# Hisse listesi
with st.spinner("📡 BIST hisse listesi hazırlanıyor..."):
    BIST_TICKERS = fetch_bist_tickers()
if not BIST_TICKERS:
    st.error("❌ Hisse listesi alınamadı. Lütfen internet bağlantınızı kontrol edin.")
    st.stop()

# SIDEBAR
with st.sidebar:
    st.header("⚙️ Parametreler")
    st.info(f"📊 {len(BIST_TICKERS)} hisse taranacak")
    
    params = {
        "rsi_min": st.slider("Minimum RSI", 30, 80, 55),
        "momentum_min": st.slider("Minimum ROC (%)", -10, 30, 5),
        "hacim_z_min": st.slider("Hacim Z-Score Eşiği", 1.0, 4.0, 2.0, 0.1),
        "cmf_min": st.slider("Min CMF (Para Akışı)", -0.3, 0.3, 0.0, 0.05),
        "adx_trend_min": st.slider("ADX Trend Eşiği", 10, 35, 20),
        "adx_guclu_min": st.slider("ADX Güçlü Eşiği", 20, 50, 30),
        "rsi_period": 14, "momentum_period": 10, "adx_period": 14,
        "use_ema_filter": st.checkbox("EMA50>EMA200 Filtresi", value=True)
    }
    
    st.markdown("---")
    analyze_btn = st.button("🔍 Analiz Başlat", type="primary", use_container_width=True)
    
    with st.expander("🤖 Qwen AI Ayarları"):
        ai_enabled = st.toggle("AI Analizi Aktif", value=True)
        st.caption("💡 AI çağrısı ~5-10 saniye sürer. `secrets.toml` gerektirir.")
    
    if st.button("🔄 Listeyi Yenile", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# MAIN
if analyze_btn:
    progress_bar = st.progress(0, text="Hisseler taranıyor...")
    results = []
    
    for i, sym in enumerate(BIST_TICKERS):
        progress_bar.progress((i + 1) / len(BIST_TICKERS), text=f"Taranıyor: {sym} ({i+1}/{len(BIST_TICKERS)})")
        res = analyze_stock(sym, params)
        if res:
            results.append(res)
            
    progress_bar.empty()
    st.session_state.results = pd.DataFrame(results) if results else pd.DataFrame()
    st.success(f"✅ Tarama bitti! {len(results)} hisse bulundu." if results else "⚠️ Kriterlere uygun hisse bulunamadı.")

# SONUÇLAR
if "results" in st.session_state and not st.session_state.results.empty:
    df_res = st.session_state.results
    
    # Tablo
    st.subheader("📋 Bulunan Hisseler")
    def color_score(val):
        return 'background-color: #00cc0044' if val >= 70 else 'background-color: #ffaa0044' if val >= 50 else 'background-color: #ff444444'
    
    styled = df_res.style.map(color_score, subset=["Skor"])
    st.dataframe(styled, use_container_width=True, height=350)
    
    # İstatistikler
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam", len(df_res))
    c2.metric("Güçlü Trend", len(df_res[df_res["Trend"].str.contains("Güçlü")]))
    c3.metric("Ort. RSI", df_res["RSI"].mean().round(1))
    c4.metric("Ort. Skor", df_res["Skor"].mean().round(1))
    
    # CSV Export
    csv = df_res.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 CSV İndir", csv, f"bist_tarama_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", "text/csv")
    
    # Detay & AI Bölümü
    st.markdown("---")
    c1, c2 = st.columns([3, 1])
    with c1:
        selected = st.selectbox("📈 Detay & AI Analiz İçin Hisse Seçin:", df_res["Hisse"].tolist())
    with c2:
        chart_btn = st.button("📊 Grafiği Göster", use_container_width=True)
        ai_btn = st.button("🤖 AI Analizi", use_container_width=True, disabled=not ai_enabled)
    
    if selected and chart_btn:
        sym_full = f"{selected}.IS"
        df = fetch_stock_data(sym_full)
        if df is not None:
            df = calculate_indicators(df, params)
            st.plotly_chart(create_chart(sym_full, df), use_container_width=True)
            
    if selected and ai_btn and ai_enabled:
        sym_full = f"{selected}.IS"
        df = fetch_stock_data(sym_full)
        if df is not None:
            df = calculate_indicators(df, params)
            with st.spinner("🤖 Qwen analiz yapıyor..."):
                ai_res = generate_ai_analysis(sym_full, df, params)
                
            if "error" in ai_res:
                st.error(ai_res["error"])
            else:
                st.markdown(f"""
                <div class="ai-card">
                    <h4>🎯 {ai_res.get("ozet", "Analiz tamamlandı")}</h4>
                </div>
                """, unsafe_allow_html=True)
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Öneri", ai_res.get("öneri", "N/A"))
                m2.metric("Trend", ai_res.get("trend_yonü", "N/A"))
                m3.metric("Risk", f"{ai_res.get('risk_puanı', '?')}/10")
                m4.metric("Destek", f"{ai_res.get('destek_seviyesi', '?')} TL")
                
                with st.expander("📝 AI Detay Raporu"):
                    st.markdown(f"**Beklenti:** {ai_res.get('kisa_vade_beklenti')}\n\n**Gerekçe:** {ai_res.get('gerekce')}")
                    st.write("**Dikkat:**", ai_res.get("dikkat", []))

# FOOTER
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#6c757d; font-size:0.9em; padding:1rem;">
    ⚠️ Bu uygulama <b>yatırım tavsiyesi DEĞİLDİR</b>. Teknik veriler ve AI yorumları bilgilendirme amaçlıdır.<br>
    Veri Kaynakları: Yahoo Finance, TradingView, Qwen AI | © 2026 BIST TrendScout Pro v2.2
</div>
""", unsafe_allow_html=True)
