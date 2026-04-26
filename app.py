# =========================================
# 🚀 BIST TrendScout PRO v3.5 - Streamlit Cloud Uyumlu
# ✅ Python 3.14 | ✅ pandas_ta YOK | ✅ Tüm ID'ler Benzersiz | ✅ 630 Hisse Tam İşlem
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
# 📊 MANUEL İNDİKATÖRLER (pandas_ta/numba GEREKTİRMEZ)
# =========================================

def calc_rsi(series, length=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))

def calc_adx(high, low, close, length=14):
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

def calc_ema(series, length):
    return series.ewm(span=length, adjust=False).mean()

def calc_cmf(high, low, close, volume, length=20):
    mfm = ((close - low) - (high - close)) / (high - low + 1e-10)
    mfv = mfm * volume
    return (mfv.rolling(length).sum()) / (volume.rolling(length).sum())

def add_indicators(df, p):
    df = df.copy()
    if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume']):
        return None
    df['RSI'] = calc_rsi(df['close'], p['rsi_len'])
    df['ADX'] = calc_adx(df['high'], df['low'], df['close'], p['adx_len'])
    df['EMA_SHORT'] = calc_ema(df['close'], p['ema_short'])
    df['EMA_LONG'] = calc_ema(df['close'], p['ema_long'])
    df['CMF'] = calc_cmf(df['high'], df['low'], df['close'], df['volume'], p['cmf_len'])
    df['VOL_MEAN'] = df['volume'].rolling(p['vol_len']).mean()
    df['VOL_STD'] = df['volume'].rolling(p['vol_len']).std()
    df['VOL_Z'] = (df['volume'] - df['VOL_MEAN']) / (df['VOL_STD'] + 1e-10)
    df['HH'] = df['high'].rolling(p['breakout_len']).max()
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
                "BIMAS", "MGROS", "Sise", "KCHOL", "SAHOL", "ARCLK", "VESBE", "FROTO"]

@st.cache_data(ttl=600)
def get_data_cached(symbol, interval_str):
    try:
        yf_sym = f"{symbol}.IS"
        interval_map = {"1g": "1d", "4s": "1h"}
        period_map = {"1d": "2y", "1h": "6mo"}
        intv = interval_map.get(interval_str, "1d")
        per = period_map.get(intv, "2y")
        
        df = yf.download(yf_sym, period=per, interval=intv, progress=False)
        if df is None or len(df) < 50: return None
        if isinstance(df.columns, pd.MultiIndex): df = df.droplevel(1, axis=1)
        if not all(c in df.columns for c in ["Open", "High", "Low", "Close", "Volume"]): return None
        
        return df.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"})
    except:
        return None

# =========================================
# 🔍 ANALİZ
# =========================================

def ai_yorum(row, p):
    yorum = []
    if row["RSI"] > p["rsi_min"]: yorum.append("📈 Momentum")
    if row["ADX"] > p["adx_min"]: yorum.append("🌪️ Trend")
    if row["CMF"] > p["cmf_min"]: yorum.append("💰 Para Girişi")
    if row["VOL_Z"] > p["vol_z_min"]: yorum.append("🔥 Hacim Patlaması")
    return " | ".join(yorum) if yorum else "⏳ Nötr"

def hizli_filtre(symbol):
    df = get_data_cached(symbol, "1g")
    if df is None: return False
    df["EMA20"] = calc_ema(df["close"], 20)
    return df["close"].iloc[-1] > df["EMA20"].iloc[-1]

def analyze_symbol(symbol, params):
    df_d = get_data_cached(symbol, "1g")
    df_4h = get_data_cached(symbol, "4s")
    if df_d is None or df_4h is None: return None

    df_d = add_indicators(df_d, params)
    df_4h = add_indicators(df_4h, params)
    if df_d is None or df_4h is None: return None

    d = df_d.iloc[-1]
    h4 = df_4h.iloc[-1]

    trend = d["close"] > d["EMA_LONG"]
    rsi = pd.notna(d["RSI"]) and d["RSI"] > params["rsi_min"]
    adx = pd.notna(d["ADX"]) and d["ADX"] > params["adx_min"]
    volume = pd.notna(d["VOL_Z"]) and d["VOL_Z"] > params["vol_z_min"]
    para = pd.notna(d["CMF"]) and d["CMF"] > params["cmf_min"]
    prev_close = df_d["close"].iloc[-2] if len(df_d) > 1 else d["close"]
    breakout = len(df_d) > params["breakout_len"] and d["close"] > df_d["HH"].iloc[-2]
    mtf = pd.notna(h4["RSI"]) and h4["RSI"] > 50 and h4["close"] > h4["EMA_LONG"]

    if all([trend, rsi, adx, volume, para, breakout, mtf]):
        return {
            "Hisse": symbol, "Fiyat": round(float(d["close"]), 2),
            "Degisim_%": round(((d["close"]/prev_close)-1)*100, 2),
            "RSI": round(float(d["RSI"]), 2), "ADX": round(float(d["ADX"]), 2),
            "Hacim_Z": round(float(d["VOL_Z"]), 2), "CMF": round(float(d["CMF"]), 3),
            "AI Yorum": ai_yorum(d, params)
        }
    return None

# =========================================
# 🎛️ SOL PANEL (TÜM PARAMETRELER - BENZERSİZ KEY'LER)
# =========================================

with st.sidebar:
    st.title("⚙️ Tüm Parametreler")
    
    st.subheader("📊 RSI")
    rsi_len = st.number_input("RSI Periyot", 5, 50, 14, key="rsi_len_input")
    rsi_min = st.slider("RSI Minimum Değer", 30, 80, 55, key="rsi_min_slider")
    
    st.subheader("🌪️ ADX")
    adx_len = st.number_input("ADX Periyot", 5, 50, 14, key="adx_len_input")
    adx_min = st.slider("ADX Minimum Değer", 10, 50, 20, key="adx_min_slider")
    
    st.subheader("📉 EMA")
    ema_short = st.number_input("Kısa EMA Periyot", 10, 100, 20, key="ema_short_input")
    ema_long = st.number_input("Uzun EMA Periyot", 20, 200, 50, key="ema_long_input")
    
    st.subheader("💰 CMF")
    cmf_len = st.number_input("CMF Periyot", 10, 50, 20, key="cmf_len_input")
    cmf_min = st.slider("CMF Minimum Değer", -0.5, 0.5, 0.0, 0.01, key="cmf_min_slider")
    
    st.subheader("📦 Hacim (Z-Skor)")
    vol_len = st.number_input("Hacim Periyot", 10, 50, 20, key="vol_len_input")
    vol_z_min = st.slider("Min Z-Skor", 0.5, 5.0, 2.0, key="vol_z_min_slider")
    
    st.subheader("📈 Kırılım")
    breakout_len = st.number_input("Zirve Penceresi", 10, 100, 20, key="breakout_len_input")
    
    st.divider()
    use_fast = st.checkbox("⚡ Hızlı Filtre (EMA20)", value=True, key="use_fast_checkbox")
    
    if st.button("🚀 Taramayı Başlat", type="primary", width="stretch", key="start_scan_btn"):
        st.session_state.run_scan = True

# =========================================
# 🖥️ ANA ÇALIŞMA
# =========================================

st.title("🚀 BIST TrendScout PRO v3.5")
st.markdown("""<div style='background:linear-gradient(90deg,#1e3c72,#2a5298);padding:12px;border-radius:8px;color:white'>
<strong>📊 yfinance + Manuel İndikatörler | Python 3.14 Uyumlu</strong></div>""", unsafe_allow_html=True)

if st.session_state.get("run_scan", False):
    st.session_state.run_scan = False
    
    params = {
        "rsi_len": rsi_len, "rsi_min": rsi_min, "adx_len": adx_len, "adx_min": adx_min,
        "ema_short": ema_short, "ema_long": ema_long, "cmf_len": cmf_len, "cmf_min": cmf_min,
        "vol_len": vol_len, "vol_z_min": vol_z_min, "breakout_len": breakout_len
    }
    
    with st.spinner("📡 BIST hisseleri çekiliyor..."):
        hisseler = get_bist_hisseler()
    
    if not hisseler:
        st.error("❌ Hisseler yüklenemedi.")
        st.stop()
        
    st.info(f"✅ Toplam {len(hisseler)} hisse bulundu. **Tümü işlenecek.**")
    
    progress = st.progress(0)
    status = st.empty()
    results = []
    total = len(hisseler)
    
    for i, h in enumerate(hisseler):
        progress.progress((i + 1) / total)
        status.text(f"🔎 {h} ({i+1}/{total})")
        
        if use_fast and not hizli_filtre(h): continue
        res = analyze_symbol(h, params)
        if res: results.append(res)
            
        if i % 15 == 0: time.sleep(0.15)  # yfinance rate limit koruması
        
    progress.empty()
    status.empty()
    
    if results:
        df_res = pd.DataFrame(results).sort_values("Hacim_Z", ascending=False)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🎯 Sinyal", len(results))
        c2.metric("💹 Ort. Fiyat", f"{df_res['Fiyat'].mean():.2f} ₺")
        c3.metric("📈 Ort. RSI", f"{df_res['RSI'].dropna().mean():.1f}")
        c4.metric("🌪️ Ort. ADX", f"{df_res['ADX'].dropna().mean():.1f}")
        
        st.subheader("📋 Sinyal Tablosu")
        styled = df_res.style.format({
            "Fiyat": "{:.2f}", "Degisim_%": "{:.2f}%", "RSI": "{:.2f}", 
            "ADX": "{:.2f}", "Hacim_Z": "{:.2f}", "CMF": "{:.3f}"
        }).background_gradient(subset=["Hacim_Z"], cmap="YlOrRd")
        
        st.dataframe(styled, width="stretch", hide_index=True)
        
        csv = df_res.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("📥 CSV İndir", csv, f"bist_sinyaller_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", "text/csv", width="stretch")
    else:
        st.warning("⚠️ Kriterlerinize uygun sinyal bulunamadı. Parametreleri gevşetmeyi deneyin.")

with st.expander("📖 Bilgi & Kullanım"):
    st.markdown("""
    - **Tüm parametreler** sol panelden anlık değiştirilebilir.
    - **Tüm BIST hisseleri** sırasıyla taranır. Delisted veya veri çekilemeyenler otomatik atlanır.
    - `pandas_ta` ve `numba` **kaldırıldı**. Python 3.14 ile %100 uyumlu.
    - Veriler 15-20dk gecikmeli olabilir. Yatırım tavsiyesi değildir.
    """)

st.markdown("---")
st.markdown(f"<div style='text-align:center;color:gray;font-size:0.85em'>📊 BIST TrendScout PRO | {datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
