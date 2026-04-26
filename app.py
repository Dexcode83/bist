# =========================================
# 📊 BIST TrendScort Pro v2.2 (pandas-ta içermeyen sürüm)
# 📦 Gerekli kütüphaneler: pip install streamlit pandas numpy yfinance plotly
# ▶️ Çalıştırma: streamlit run app.py
# =========================================

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import time
from datetime import datetime

# Sayfa Konfigürasyonu
st.set_page_config(page_title="BIST TrendScort Pro", layout="wide", page_icon="📈")

# =========================================
# 🔧 GLOBAL AYARLAR & SABİTLER
# =========================================
DEFAULT_BIST_STOCKS = [
    "THYAO", "GARAN", "AKBNK", "ISCTR", "YKBNK", "EREGL", "TUPRS", "KCHOL", 
    "SISE", "BIMAS", "MGROS", "SASA", "TAVIL", "FROTO", "TOASO", "ARCLK", 
    "KOZAL", "ASELS", "TCELL", "TTKOM", "VESTL", "VAKBN", "HALKB", "PETKM", 
    "DOHOL", "ODAS", "EKGYO", "AKSEN", "ALARK", "ENKAI"
]

RSI_MIN = st.session_state.get("rsi_min", 60)
ADX_MIN = st.session_state.get("adx_min", 25)
VOLUME_Z_MIN = st.session_state.get("vol_z_min", 2.0)

# =========================================
# 📥 VERİ ÇEKME
# =========================================
@st.cache_data(ttl=300)
def get_data(symbol, timeframe="1d"):
    """Yahoo Finance'ten veri çeker. Hata durumunda None döner."""
    try:
        ticker = yf.Ticker(f"{symbol}.IS")
        # 4h interval bazı hisselerde desteklenmeyebilir, 1h fallback olarak kullanılabilir
        df = ticker.history(period="2y", interval=timeframe)
        if df.empty:
            return None
        
        # Sütun isimlerini standartlaştır
        df.columns = [col.lower() for col in df.columns]
        return df
    except Exception:
        return None

# =========================================
# 📊 GÖSTERGELER (Manuel Hesaplama - pandas/numpy)
# =========================================
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-8)
    return 100 - (100 / (1 + rs))

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calculate_adx(high, low, close, period=14):
    plus_dm = high.diff()
    minus_dm = low.diff()
    plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0)
    minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0)
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.DataFrame([tr1, tr2, tr3]).max()
    
    tr_smooth = tr.ewm(alpha=1/period, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm).rolling(window=period).mean() / (tr_smooth + 1e-8)
    minus_di = 100 * pd.Series(minus_dm).rolling(window=period).mean() / (tr_smooth + 1e-8)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-8)
    return dx.rolling(window=period).mean()

def calculate_roc(series, period=10):
    return ((series - series.shift(period)) / series.shift(period)) * 100

def calculate_cmf(high, low, close, volume, period=20):
    mfm = ((close - low) - (high - close)) / (high - low + 1e-8)
    mfv = mfm * volume
    return mfv.rolling(window=period).sum() / volume.rolling(window=period).sum()

def calculate_volume_zscore(volume, period=20):
    mean = volume.rolling(window=period).mean()
    std = volume.rolling(window=period).std()
    return (volume - mean) / (std + 1e-8)

def add_indicators(df):
    df = df.copy()
    df["RSI"] = calculate_rsi(df["close"], 14)
    df["ADX"] = calculate_adx(df["high"], df["low"], df["close"], 14)
    df["EMA50"] = calculate_ema(df["close"], 50)
    df["ROC"] = calculate_roc(df["close"], 10)
    df["CMF"] = calculate_cmf(df["high"], df["low"], df["close"], df["volume"], 20)
    df["VOL_Z"] = calculate_volume_zscore(df["volume"], 20)
    df["HH20"] = df["high"].rolling(20).max()
    return df

# =========================================
# ⚡ HIZLI ÖN FİLTRE
# =========================================
def hizli_filtre(symbol):
    df = get_data(symbol, "1d")
    if df is None or len(df) < 20:
        return False
    df["EMA20"] = calculate_ema(df["close"], 20)
    return df["close"].iloc[-1] > df["EMA20"].iloc[-1]

# =========================================
# 🤖 AI YORUM
# =========================================
def ai_yorum(row):
    yorum = []
    if pd.notna(row.get("RSI")) and row["RSI"] > 60:
        yorum.append("Momentum güçlü")
    if pd.notna(row.get("ADX")) and row["ADX"] > 25:
        yorum.append("Trend kuvvetli")
    if pd.notna(row.get("CMF")) and row["CMF"] > 0:
        yorum.append("Para girişi var")
    if pd.notna(row.get("VOL_Z")) and row["VOL_Z"] > 2:
        yorum.append("Hacim patlaması")
    return " | ".join(yorum) if yorum else "Nötr"

# =========================================
# 🧠 ANALİZ
# =========================================
def analyze_symbol(symbol):
    df_d = get_data(symbol, "1d")
    df_4h = get_data(symbol, "4h")
    
    if df_d is None or df_4h is None:
        return None
    if len(df_d) < 50 or len(df_4h) < 50:
        return None
        
    df_d = add_indicators(df_d).dropna()
    df_4h = add_indicators(df_4h).dropna()
    
    if len(df_d) == 0 or len(df_4h) == 0:
        return None
        
    d = df_d.iloc[-1]
    h4 = df_4h.iloc[-1]
    
    # Şartlar (AND Mantığı)
    trend = d["close"] > d["EMA50"]
    rsi = pd.notna(d["RSI"]) and d["RSI"] > RSI_MIN
    adx = pd.notna(d["ADX"]) and d["ADX"] > ADX_MIN
    volume = pd.notna(d["VOL_Z"]) and d["VOL_Z"] > VOLUME_Z_MIN
    para = pd.notna(d["CMF"]) and d["CMF"] > 0
    breakout = d["close"] > df_d["HH20"].iloc[-2] if len(df_d) > 1 else False
    mtf = (pd.notna(h4["RSI"]) and h4["RSI"] > 50 and h4["close"] > h4["EMA50"])
    
    if all([trend, rsi, adx, volume, para, breakout, mtf]):
        return {
            "Hisse": symbol,
            "Fiyat": round(float(d["close"]), 2),
            "RSI": round(float(d["RSI"]), 2),
            "ADX": round(float(d["ADX"]), 2),
            "Hacim Skor": round(float(d["VOL_Z"]), 2),
            "AI Yorum": ai_yorum(d)
        }
    return None

# =========================================
# 📈 GRAFİK OLUŞTURUCU
# =========================================
def create_chart(symbol, df):
    fig = go.Figure()
    
    # Fiyat & EMA50
    fig.add_trace(go.Candlestick(x=df.index, open=df["open"], high=df["high"], 
                                 low=df["low"], close=df["close"], name="Fiyat"))
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA50"], line=dict(color="orange", width=2), name="EMA50"))
    
    # RSI (Alt grafik)
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], yaxis="y2", line=dict(color="purple", width=2), name="RSI"))
    fig.add_hline(y=70, line_dash="dash", line_color="red", yaxis="y2")
    fig.add_hline(y=30, line_dash="dash", line_color="green", yaxis="y2")
    
    # Layout
    fig.update_layout(
        title=f"{symbol} Teknik Analiz",
        xaxis_rangeslider_visible=False,
        yaxis=dict(title="Fiyat", side="right"),
        yaxis2=dict(title="RSI", overlaying="y", side="left", range=[0, 100], showgrid=False),
        height=600,
        template="plotly_dark"
    )
    return fig

# =========================================
# 🖥️ STREAMLET ARAYÜZÜ
# =========================================
st.title("📊 BIST TrendScort Pro v2.2")
st.caption("pandas-ta bağımlılığı olmayan, saf pandas/numpy tabanlı çoklu zaman dilimi tarayıcı")

with st.sidebar:
    st.header("⚙️ Parametreler")
    RSI_MIN = st.slider("Minimum RSI", 30, 80, 60)
    ADX_MIN = st.slider("Minimum ADX", 10, 40, 25)
    VOLUME_Z_MIN = st.slider("Min Hacim Z-Skoru", 1.0, 5.0, 2.0)
    st.divider()
    selected_stock = st.selectbox("🔍 Detaylı Grafik İçin Hisse Seç", DEFAULT_BIST_STOCKS)
    
    st.session_state.update({
        "rsi_min": RSI_MIN, "adx_min": ADX_MIN, "vol_z_min": VOLUME_Z_MIN
    })

# Global değişkenleri güncelle
RSI_MIN = st.session_state.get("rsi_min", 60)
ADX_MIN = st.session_state.get("adx_min", 25)
VOLUME_Z_MIN = st.session_state.get("vol_z_min", 2.0)

if st.button("🚀 Analiz Başlat", type="primary"):
    results = []
    total = len(DEFAULT_BIST_STOCKS)
    
    with st.status("🔎 BIST hisseleri taranıyor...", expanded=True) as status:
        for i, symbol in enumerate(DEFAULT_BIST_STOCKS):
            # Rate limit önleme
            if i % 20 == 0:
                time.sleep(0.5)
                
            # Hızlı filtre
            if hizli_filtre(symbol):
                res = analyze_symbol(symbol)
                if res:
                    results.append(res)
            st.progress((i + 1) / total, text=f"📊 {i+1}/{total} tarandı: {symbol}")
            
        status.update(label="✅ Tarama tamamlandı!", state="complete", expanded=False)
    
    if results:
        st.success(f"🎯 {len(results)} adet kriterlere uygun hisse bulundu!")
        df_results = pd.DataFrame(results)
        st.dataframe(df_results, use_container_width=True, hide_index=True)
        
        # CSV İndirme
        csv = df_results.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 Sonuçları CSV Olarak İndir", csv, "bist_sinyaller.csv", "text/csv")
    else:
        st.warning("⚠️ Belirtilen kriterlere uygun hisse bulunamadı. Parametreleri gevşetmeyi deneyin.")

# Detay Grafik
st.divider()
st.subheader(f"📈 {selected_stock} Detay Görünümü")
df_detail = get_data(selected_stock, "1d")
if df_detail is not None and len(df_detail) > 50:
    df_detail = add_indicators(df_detail).dropna()
    if len(df_detail) > 0:
        st.plotly_chart(create_chart(selected_stock, df_detail), use_container_width=True)
        st.info(f"📅 Son güncelleme: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Veri kaynağı: Yahoo Finance")
    else:
        st.error("📉 Yeterli geçmiş veri bulunamadı.")
else:
    st.error("🔗 Veri çekilemedi. Hissenin Yahoo Finance'te `.IS` uzantısı ile listelendiğinden emin olun.")
