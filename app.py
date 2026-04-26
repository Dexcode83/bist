# =========================================
# 🚀 BIST TrendScout PRO v3.5 - yfinance + Streamlit Cloud Uyumlu
# ✅ pandas_ta YOK - Tüm indikatörler manuel hesaplanıyor
# =========================================

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import json
import time
from datetime import datetime

# Sayfa ayarları
st.set_page_config(page_title="BIST TrendScout PRO", page_icon="📈", layout="wide")

# =========================================
# 📊 TEKNİK GÖSTERGELER (Manuel Hesaplama - pandas_ta GEREKTİRMEZ)
# =========================================

def calculate_rsi(series, length=14):
    """RSI hesapla - manuel"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))

def calculate_adx(high, low, close, length=14):
    """ADX hesapla - manuel"""
    def true_range(h, l, c):
        tr1 = h - l
        tr2 = abs(h - c.shift(1))
        tr3 = abs(l - c.shift(1))
        return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    def directional_movement(h, l, c):
        up_move = h - h.shift(1)
        down_move = l.shift(1) - l
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        return pd.Series(plus_dm), pd.Series(minus_dm)
    
    tr = true_range(high, low, close)
    plus_dm, minus_dm = directional_movement(high, low, close)
    
    tr_smooth = tr.rolling(length).sum()
    plus_smooth = plus_dm.rolling(length).sum()
    minus_smooth = minus_dm.rolling(length).sum()
    
    plus_di = 100 * (plus_smooth / (tr_smooth + 1e-10))
    minus_di = 100 * (minus_smooth / (tr_smooth + 1e-10))
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
    adx = dx.rolling(length).mean()
    return adx

def calculate_ema(series, length):
    """EMA hesapla - manuel"""
    return series.ewm(span=length, adjust=False).mean()

def calculate_roc(series, length):
    """ROC hesapla - manuel"""
    return ((series - series.shift(length)) / series.shift(length)) * 100

def calculate_cmf(high, low, close, volume, length=20):
    """Chaikin Money Flow - manuel"""
    mfm = ((close - low) - (high - close)) / (high - low + 1e-10)
    mfv = mfm * volume
    return (mfv.rolling(length).sum()) / (volume.rolling(length).sum())

def add_indicators(df):
    """Tüm indikatörleri ekle"""
    df = df.copy()
    
    # Gerekli kolonlar var mı?
    required = ['open', 'high', 'low', 'close', 'volume']
    if not all(col in df.columns for col in required):
        return None
    
    df['RSI'] = calculate_rsi(df['close'], 14)
    df['ADX'] = calculate_adx(df['high'], df['low'], df['close'], 14)
    df['EMA50'] = calculate_ema(df['close'], 50)
    df['ROC'] = calculate_roc(df['close'], 10)
    df['CMF'] = calculate_cmf(df['high'], df['low'], df['close'], df['volume'], 20)
    
    # Volume Z-Score
    df['VOL_MEAN'] = df['volume'].rolling(20).mean()
    df['VOL_STD'] = df['volume'].rolling(20).std()
    df['VOL_Z'] = (df['volume'] - df['VOL_MEAN']) / (df['VOL_STD'] + 1e-10)
    
    # 20 günlük en yüksek
    df['HH20'] = df['high'].rolling(20).max()
    
    return df

# =========================================
# 🔄 VERİ ÇEKME (yfinance)
# =========================================

@st.cache_data(ttl=3600)
def get_bist_hisseler():
    """BIST hisselerini TradingView'dan çek"""
    try:
        url = "https://scanner.tradingview.com/turkey/scan"
        payload = {
            "filter": [{"left": "exchange", "operation": "equal", "right": "BIST"}],
            "options": {"lang": "tr"},
            "symbols": {"query": {"types": []}, "tickers": []},
            "columns": ["name"]
        }
        r = requests.post(url, json=payload, timeout=30)
        data = r.json()
        hisseler = [item["d"][0].replace("BIST:", "") for item in data["data"]]
        hisseler = [h.strip().upper() for h in hisseler if len(h) <= 5]
        return list(set(hisseler))
    except:
        return ["AKBNK", "GARAN", "ISCTR", "YKBNK", "THYAO", "EREGL", "TUPRS", 
                "BIMAS", "MGROS", "SISE", "KCHOL", "SAHOL", "ARCLK", "VESBE", "FROTO"]

def to_yf_symbol(symbol):
    return f"{symbol}.IS"

@st.cache_data(ttl=600)
def get_data_cached(symbol, interval_str, n_bars=100):
    """yfinance ile veri çek"""
    try:
        yf_symbol = to_yf_symbol(symbol)
        interval_map = {"1g": "1d", "4s": "1h", "1s": "1h", "15d": "15m"}
        period_map = {"1d": "2y", "1h": "6mo", "15m": "5d"}
        
        interval = interval_map.get(interval_str, "1d")
        period = period_map.get(interval, "2y")
        
        df = yf.download(yf_symbol, period=period, interval=interval, progress=False)
        
        if df is None or len(df) < 50:
            return None
        
        # MultiIndex column fix
        if isinstance(df.columns, pd.MultiIndex):
            df = df.droplevel(1, axis=1)
        
        # Gerekli kolon kontrolü
        required = ["Open", "High", "Low", "Close", "Volume"]
        if not all(col in df.columns for col in required):
            return None
        
        # Küçük harfe çevir
        df = df.rename(columns={
            "Open": "open", "High": "high", "Low": "low", 
            "Close": "close", "Volume": "volume"
        })
        
        return df
    except:
        return None

# =========================================
# 🎯 ANALİZ FONKSİYONLARI
# =========================================

def ai_yorum(row):
    yorum = []
    if pd.notna(row.get("RSI")) and row["RSI"] > 60:
        yorum.append("📈 Momentum güçlü")
    if pd.notna(row.get("ADX")) and row["ADX"] > 25:
        yorum.append("🎯 Trend kuvvetli")
    if pd.notna(row.get("CMF")) and row["CMF"] > 0:
        yorum.append("💰 Para girişi var")
    if pd.notna(row.get("VOL_Z")) and row["VOL_Z"] > 2:
        yorum.append("🔥 Hacim patlaması")
    return " | ".join(yorum) if yorum else "⏳ Bekle-Gör"

def hizli_filtre(symbol):
    df = get_data_cached(symbol, "1g")
    if df is None:
        return False
    df["EMA20"] = calculate_ema(df["close"], 20)
    return df["close"].iloc[-1] > df["EMA20"].iloc[-1]

def analyze_symbol(symbol, params):
    df_d = get_data_cached(symbol, "1g")
    df_4h = get_data_cached(symbol, "4s")
    
    if df_d is None or df_4h is None:
        return None
    
    df_d = add_indicators(df_d)
    df_4h = add_indicators(df_4h)
    
    if df_d is None or df_4h is None:
        return None
    
    d = df_d.iloc[-1]
    h4 = df_4h.iloc[-1]
    
    # Kriterler
    trend = d["close"] > d["EMA50"]
    rsi = pd.notna(d["RSI"]) and d["RSI"] > params["rsi_min"]
    adx = pd.notna(d["ADX"]) and d["ADX"] > params["adx_min"]
    volume = pd.notna(d["VOL_Z"]) and d["VOL_Z"] > params["volume_z_min"]
    para = pd.notna(d["CMF"]) and d["CMF"] > 0
    breakout = len(df_d) > 20 and d["close"] > df_d["HH20"].iloc[-2]
    mtf = pd.notna(h4["RSI"]) and h4["RSI"] > 50 and h4["close"] > calculate_ema(h4["close"], 50).iloc[-1]
    
    if all([trend, rsi, adx, volume, para, breakout, mtf]):
        # Degisim_% hesaplaması (fix: numpy.float64.shift hatası)
        prev_close = df_d["close"].iloc[-2] if len(df_d) > 1 else d["close"]
        degisim = ((d["close"] / prev_close) - 1) * 100
        
        return {
            "Hisse": symbol,
            "Fiyat": round(float(d["close"]), 2),
            "Degisim_%": round(float(degisim), 2),
            "RSI": round(float(d["RSI"]), 2) if pd.notna(d["RSI"]) else None,
            "ADX": round(float(d["ADX"]), 2) if pd.notna(d["ADX"]) else None,
            "Hacim Skor": round(float(d["VOL_Z"]), 2) if pd.notna(d["VOL_Z"]) else None,
            "CMF": round(float(d["CMF"]), 3) if pd.notna(d["CMF"]) else None,
            "AI Yorum": ai_yorum(d)
        }
    return None

# =========================================
# 🎨 ARAYÜZ
# =========================================

with st.sidebar:
    st.title("⚙️ Parametreler")
    rsi_min = st.slider("RSI Minimum", 30, 80, 55)
    adx_min = st.slider("ADX Minimum", 10, 50, 20)
    volume_z_min = st.slider("Hacim Z-Skor Min", 0.5, 5.0, 2.0)
    st.divider()
    max_hisse = st.slider("Maksimum Hisse", 50, 500, 200)
    use_fast_filter = st.checkbox("Hızlı Filtre", value=True)
    if st.button("🔄 Sıfırla", use_container_width=True):
        st.session_state.clear()
        st.rerun()

st.title("🚀 BIST TrendScout PRO v3.5")
st.markdown("""<div style='background:linear-gradient(90deg,#1e3c72,#2a5298);padding:15px;border-radius:10px;color:white'>
<strong>📊 yfinance ile Gerçek Zamanlı BIST Analizi (pandas_ta GEREKTİRMEZ)</strong></div>""", unsafe_allow_html=True)

if st.button("🔍 Taramayı Başlat", type="primary", use_container_width=True):
    params = {"rsi_min": rsi_min, "adx_min": adx_min, "volume_z_min": volume_z_min}
    
    with st.spinner("📡 Hisseler yükleniyor..."):
        hisseler = get_bist_hisseler()
    
    if not hisseler:
        st.error("❌ Hisseler yüklenemedi")
        st.stop()
    
    st.info(f"✅ {len(hisseler)} hisse bulundu")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    results_container = st.empty()
    
    results = []
    total = min(len(hisseler), max_hisse)
    
    for i, h in enumerate(hisseler[:total]):
        progress_bar.progress((i + 1) / total)
        status_text.text(f"🔎 {h} ({i+1}/{total})")
        
        if use_fast_filter and not hizli_filtre(h):
            continue
        
        res = analyze_symbol(h, params)
        if res:
            results.append(res)
            if results:
                results_container.dataframe(
                    pd.DataFrame(results).sort_values("Hacim Skor", ascending=False),
                    width="stretch", hide_index=True
                )
        
        time.sleep(0.2)  # yfinance rate limit
    
    progress_bar.empty()
    status_text.empty()
    
    st.success(f"🎉 {len(results)} PRO sinyal bulundu")
    
    if results:
        df_results = pd.DataFrame(results).sort_values("Hacim Skor", ascending=False)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📈 Sinyal", len(results))
        col2.metric("💹 Ort. Fiyat", f"{df_results['Fiyat'].mean():.2f} ₺")
        col3.metric("🔥 Ort. RSI", f"{df_results['RSI'].dropna().mean():.1f}")
        col4.metric("🎯 Ort. ADX", f"{df_results['ADX'].dropna().mean():.1f}")
        
        st.subheader("📋 Sonuçlar")
        
        # ✅ applymap yerine map kullan (pandas>=2.1)
        def color_trend(val):
            if val == "Güçlü Yükseliş": return 'background-color: #44ff4444'
            if val == "Yükseliş": return 'background-color: #aaffaa44'
            if val == "Nötr": return 'background-color: #ffa50044'
            return 'background-color: #ff444444'
        
        # Trend kolonu yoksa ekle
        if 'Trend' not in df_results.columns:
            df_results['Trend'] = 'Yükseliş'
        
        styled_df = df_results.style.map(color_trend, subset=['Trend'])
        st.dataframe(styled_df.format({
            "Fiyat": "{:.2f}", "Degisim_%": "{:.2f}%", "RSI": "{:.2f}", 
            "ADX": "{:.2f}", "Hacim Skor": "{:.2f}", "CMF": "{:.3f}"
        }), width="stretch", hide_index=True)
        
        # İndir
        csv = df_results.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("📥 CSV İndir", csv, 
                          f"bist_sinyaller_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                          "text/csv", use_container_width=True)
    else:
        st.warning("⚠️ Sinyal bulunamadı. Parametreleri gevşetin.")

with st.expander("📖 Bilgi"):
    st.markdown("""
    ### 🔧 Parametreler
    - **RSI**: Momentum gücü (55+ önerilir)
    - **ADX**: Trend kuvveti (20+ trend var)
    - **Hacim Z-Skor**: Anormal hacim tespiti
    
    ### 🎯 Sinyal Kriterleri
    1. Fiyat > EMA50 | 2. RSI > threshold | 3. ADX > threshold
    4. Hacim Z > 2 | 5. CMF > 0 | 6. 20g zirve kırılımı | 7. 4H onay
    
    > ⚠️ Yatırım tavsiyesi DEĞİLDİR. Eğitim amaçlıdır.
    """)

st.markdown("---")
st.markdown(f"<div style='text-align:center;color:gray;font-size:0.9em'>📊 BIST TrendScout PRO | {datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
