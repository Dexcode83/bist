# =========================================
# 🚀 BIST TrendScout PRO v3.5 - Streamlit Cloud Ready
# ✅ Python 3.14 Uyumlu | ✅ pandas_ta YOK | ✅ Sol Panel Ayarları
# =========================================

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import time
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

st.set_page_config(page_title="BIST TrendScout PRO", page_icon="📈", layout="wide")

# =========================================
# 📊 TEKNİK GÖSTERGELER (Manuel - pandas_ta gerektirmez)
# =========================================

def calculate_rsi(series, length=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))

def calculate_adx(high, low, close, length=14):
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    
    tr_smooth = tr.rolling(length).sum()
    plus_smooth = pd.Series(plus_dm).rolling(length).sum()
    minus_smooth = pd.Series(minus_dm).rolling(length).sum()
    
    plus_di = 100 * (plus_smooth / (tr_smooth + 1e-10))
    minus_di = 100 * (minus_smooth / (tr_smooth + 1e-10))
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
    return dx.rolling(length).mean()

def calculate_ema(series, length):
    return series.ewm(span=length, adjust=False).mean()

def calculate_cmf(high, low, close, volume, length=20):
    mfm = ((close - low) - (high - close)) / (high - low + 1e-10)
    mfv = mfm * volume
    return (mfv.rolling(length).sum()) / (volume.rolling(length).sum())

def add_indicators(df):
    df = df.copy()
    if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume']):
        return None
        
    df['RSI'] = calculate_rsi(df['close'], 14)
    df['ADX'] = calculate_adx(df['high'], df['low'], df['close'], 14)
    df['EMA50'] = calculate_ema(df['close'], 50)
    df['CMF'] = calculate_cmf(df['high'], df['low'], df['close'], df['volume'], 20)
    
    df['VOL_MEAN'] = df['volume'].rolling(20).mean()
    df['VOL_STD'] = df['volume'].rolling(20).std()
    df['VOL_Z'] = (df['volume'] - df['VOL_MEAN']) / (df['VOL_STD'] + 1e-10)
    df['HH20'] = df['high'].rolling(20).max()
    return df

# =========================================
# 🔄 VERİ ÇEKME
# =========================================

@st.cache_data(ttl=3600)
def get_bist_hisseler():
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
        return list(set([h.strip().upper() for h in hisseler if 2 <= len(h) <= 5]))
    except:
        return ["AKBNK", "GARAN", "ISCTR", "YKBNK", "THYAO", "EREGL", "TUPRS", 
                "BIMAS", "MGROS", "SISE", "KCHOL", "SAHOL", "ARCLK", "VESBE", "FROTO"]

def to_yf_symbol(symbol):
    return f"{symbol}.IS"

@st.cache_data(ttl=600)
def get_data_cached(symbol, interval_str):
    try:
        yf_symbol = to_yf_symbol(symbol)
        interval_map = {"1g": "1d", "4s": "1h", "1s": "1h", "15d": "15m"}
        period_map = {"1d": "2y", "1h": "6mo", "15m": "5d"}
        
        interval = interval_map.get(interval_str, "1d")
        period = period_map.get(interval, "2y")
        
        df = yf.download(yf_symbol, period=period, interval=interval, progress=False)
        if df is None or len(df) < 50: return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df = df.droplevel(1, axis=1)
            
        required = ["Open", "High", "Low", "Close", "Volume"]
        if not all(col in df.columns for col in required): return None
        
        return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    except:
        return None

# =========================================
# 🔍 ANALİZ
# =========================================

def ai_yorum(row):
    yorum = []
    if pd.notna(row.get("RSI")) and row["RSI"] > 60: yorum.append("📈 Momentum güçlü")
    if pd.notna(row.get("ADX")) and row["ADX"] > 25: yorum.append("🎯 Trend kuvvetli")
    if pd.notna(row.get("CMF")) and row["CMF"] > 0: yorum.append("💰 Para girişi var")
    if pd.notna(row.get("VOL_Z")) and row["VOL_Z"] > 2: yorum.append("🔥 Hacim patlaması")
    return " | ".join(yorum) if yorum else "⏳ Bekle-Gör"

def hizli_filtre(symbol):
    df = get_data_cached(symbol, "1g")
    if df is None: return False
    df["EMA20"] = calculate_ema(df["close"], 20)
    return df["close"].iloc[-1] > df["EMA20"].iloc[-1]

def analyze_symbol(symbol, params):
    df_d = get_data_cached(symbol, "1g")
    df_4h = get_data_cached(symbol, "4s")
    if df_d is None or df_4h is None: return None
    
    df_d = add_indicators(df_d)
    df_4h = add_indicators(df_4h)
    if df_d is None or df_4h is None: return None
    
    d = df_d.iloc[-1]
    h4 = df_4h.iloc[-1]
    
    trend = d["close"] > d["EMA50"]
    rsi = pd.notna(d["RSI"]) and d["RSI"] > params["rsi_min"]
    adx = pd.notna(d["ADX"]) and d["ADX"] > params["adx_min"]
    volume = pd.notna(d["VOL_Z"]) and d["VOL_Z"] > params["volume_z_min"]
    para = pd.notna(d["CMF"]) and d["CMF"] > 0
    breakout = len(df_d) > 20 and d["close"] > df_d["HH20"].iloc[-2]
    
    # ✅ Scalar hatası giderildi: add_indicators zaten EMA50 hesapladı
    mtf = (pd.notna(h4.get("RSI")) and h4["RSI"] > 50 and 
           pd.notna(h4.get("EMA50")) and h4["close"] > h4["EMA50"])
    
    if all([trend, rsi, adx, volume, para, breakout, mtf]):
        prev_close = df_d["close"].iloc[-2] if len(df_d) > 1 else d["close"]
        return {
            "Hisse": symbol, "Fiyat": round(float(d["close"]), 2),
            "Degisim_%": round(((d["close"]/prev_close)-1)*100, 2),
            "RSI": round(float(d["RSI"]), 2), "ADX": round(float(d["ADX"]), 2),
            "Hacim Skor": round(float(d["VOL_Z"]), 2), "CMF": round(float(d["CMF"]), 3),
            "AI Yorum": ai_yorum(d)
        }
    return None

# =========================================
# 🖥️ SOL PANEL (SIDEBAR)
# =========================================

with st.sidebar:
    st.title("⚙️ Parametreler")
    
    rsi_min = st.slider("📊 RSI Minimum", 30, 80, 55, help="Momentum gücü eşiği")
    adx_min = st.slider("🌪️ ADX Minimum", 10, 50, 20, help="Trend kuvveti eşiği")
    volume_z_min = st.slider("📦 Hacim Z-Skor Min", 0.5, 5.0, 2.0, help="Anormal hacim tespiti")
    st.divider()
    
    st.markdown("**📈 İşlenecek Hisse Sayısı**")
    hisse_modu = st.radio("Seçim", ["Tümü", "Belirli Sayı"], horizontal=True)
    if hisse_modu == "Belirli Sayı":
        max_hisse = st.number_input("Adet", min_value=10, max_value=500, value=100, step=10)
    else:
        max_hisse = 500  # Yeterince büyük sınır
    
    use_fast_filter = st.checkbox("⚡ Hızlı Ön Filtre (EMA20)", value=True)
    st.divider()
    
    if st.button("🔍 Taramayı Başlat", type="primary", width="stretch"):
        st.session_state.run_scan = True
        
    if st.button("🔄 Sıfırla", width="stretch"):
        st.session_state.clear()
        st.rerun()

# =========================================
# 🖥️ ANA EKRAN
# =========================================

st.title("🚀 BIST TrendScout PRO v3.5")
st.markdown("""<div style='background:linear-gradient(90deg,#1e3c72,#2a5298);padding:12px;border-radius:8px;color:white'>
<strong>📊 yfinance + Manuel İndikatörler | Python 3.14 Uyumlu</strong></div>""", unsafe_allow_html=True)

if st.session_state.get("run_scan", False):
    st.session_state.run_scan = False  # Tekrar tetiklenmeyi engelle
    
    params = {"rsi_min": rsi_min, "adx_min": adx_min, "volume_z_min": volume_z_min}
    
    with st.spinner("📡 BIST hisseleri yükleniyor..."):
        hisseler = get_bist_hisseler()
    
    if not hisseler:
        st.error("❌ Hisseler yüklenemedi. Lütfen daha sonra deneyin.")
        st.stop()
        
    # Seçilen limite göre kırp
    total_scan = min(len(hisseler), max_hisse)
    st.info(f"✅ Toplam {len(hisseler)} hisse bulundu. **{total_scan} adet** işlenecek.")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    results = []
    
    for i, h in enumerate(hisseler[:total_scan]):
        progress_bar.progress((i + 1) / total_scan)
        status_text.text(f"🔎 {h} ({i+1}/{total_scan})")
        
        if use_fast_filter and not hizli_filtre(h):
            continue
            
        res = analyze_symbol(h, params)
        if res:
            results.append(res)
            if len(results) % 5 == 0:
                st.dataframe(pd.DataFrame(results).sort_values("Hacim Skor", ascending=False), width="stretch", hide_index=True)
                
        time.sleep(0.15)  # yfinance rate limit koruması
        
    progress_bar.empty()
    status_text.empty()
    
    # =========================================
    # 📊 SONUÇLAR
    # =========================================
    if results:
        df_res = pd.DataFrame(results).sort_values("Hacim Skor", ascending=False)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🎯 Sinyal", len(results))
        c2.metric("💹 Ort. Fiyat", f"{df_res['Fiyat'].mean():.2f} ₺")
        c3.metric("📈 Ort. RSI", f"{df_res['RSI'].dropna().mean():.1f}")
        c4.metric("🌪️ Ort. ADX", f"{df_res['ADX'].dropna().mean():.1f}")
        
        st.subheader("📋 Sinyal Tablosu")
        st.dataframe(
            df_res.style.format({
                "Fiyat": "{:.2f}", "Degisim_%": "{:.2f}%", "RSI": "{:.2f}", 
                "ADX": "{:.2f}", "Hacim Skor": "{:.2f}", "CMF": "{:.3f}"
            }).background_gradient(subset=["Hacim Skor"], cmap="YlOrRd"),
            width="stretch", hide_index=True
        )
        
        csv = df_res.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("📥 CSV İndir", csv, f"bist_sinyaller_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", "text/csv", width="stretch")
    else:
        st.warning("⚠️ Kriterlerinize uygun sinyal bulunamadı. Parametreleri gevşetmeyi deneyin.")

# Footer
st.markdown("---")
st.markdown(f"<div style='text-align:center;color:gray;font-size:0.85em'>📊 BIST TrendScout PRO | Veriler 15dk gecikmeli olabilir | {datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
