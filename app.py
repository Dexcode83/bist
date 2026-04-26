# =========================================
# 🚀 BIST TrendScout PRO v3.5 - yfinance Edition
# =========================================

import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import requests
import json
import time
from datetime import datetime

# Sayfa ayarları
st.set_page_config(
    page_title="BIST TrendScout PRO",
    page_icon="📈",
    layout="wide"
)

# =========================================
# ⚙️ CACHE & YARDIMCI FONKSİYONLAR
# =========================================

@st.cache_data(ttl=3600)
def get_bist_hisseler():
    """BIST hisselerini TradingView'dan çek - cache'li"""
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
        # Fallback: Bilinen BIST hisseleri
        return ["AKBNK", "GARAN", "ISCTR", "YKBNK", "THYAO", "EREGL", "TUPRS", 
                "BIMAS", "MGROS", "SISE", "KCHOL", "SAHOL", "ARCLK", "VESBE", "FROTO"]

def to_yf_symbol(symbol):
    """BIST sembolünü yfinance formatına çevir"""
    return f"{symbol}.IS"

@st.cache_data(ttl=600)
def get_data_cached(symbol, interval_str, n_bars=100):
    """yfinance ile veri çekme - cache'li"""
    try:
        yf_symbol = to_yf_symbol(symbol)
        
        # Interval mapping
        interval_map = {
            "1g": "1d",
            "4s": "1h",   # yfinance BIST'de 4h desteklemeyebilir, 1h kullan
            "1s": "1h",
            "15d": "15m"
        }
        interval = interval_map.get(interval_str, "1d")
        
        # Period hesaplama
        period_map = {
            "1d": "2y",
            "1h": "6mo",
            "15m": "5d"
        }
        period = period_map.get(interval, "2y")
        
        df = yf.download(yf_symbol, period=period, interval=interval, progress=False)
        
        if df is None or len(df) < 50:
            return None
        
        # MultiIndex column fix
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # Gerekli kolonlar var mı kontrolü
        required = ["Open", "High", "Low", "Close", "Volume"]
        if not all(col in df.columns for col in required):
            return None
        
        # Kolon isimlerini küçük harfe çevir (orijinal kodla uyum)
        df = df.rename(columns={
            "Open": "open", "High": "high", "Low": "low", 
            "Close": "close", "Volume": "volume"
        })
        
        return df
    
    except Exception as e:
        return None

# =========================================
# 📊 GÖSTERGELER (ORİJİNAL KODLA AYNI)
# =========================================

def add_indicators(df):
    df = df.copy()
    df["RSI"] = ta.rsi(df["close"], length=14)
    adx_df = ta.adx(df["high"], df["low"], df["close"])
    df["ADX"] = adx_df["ADX_14"] if "ADX_14" in adx_df.columns else None
    df["EMA50"] = ta.ema(df["close"], length=50)
    df["ROC"] = ta.roc(df["close"], length=10)
    df["CMF"] = ta.cmf(df["high"], df["low"], df["close"], df["volume"])
    df["VOL_MEAN"] = df["volume"].rolling(20).mean()
    df["VOL_STD"] = df["volume"].rolling(20).std()
    df["VOL_Z"] = (df["volume"] - df["VOL_MEAN"]) / (df["VOL_STD"] + 1e-8)
    df["HH20"] = df["high"].rolling(20).max()
    return df

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

# =========================================
# 🔍 ANALİZ FONKSİYONLARI (ORİJİNAL MANTIK KORUNDU)
# =========================================

def hizli_filtre(symbol):
    df = get_data_cached(symbol, "1g")
    if df is None:
        return False
    df["EMA20"] = df["close"].ewm(span=20).mean()
    return df["close"].iloc[-1] > df["EMA20"].iloc[-1]

def analyze_symbol(symbol, params):
    df_d = get_data_cached(symbol, "1g")
    df_4h = get_data_cached(symbol, "4s")  # yfinance'ta 1h olarak düşecek
    
    if df_d is None or df_4h is None:
        return None
    
    df_d = add_indicators(df_d)
    df_4h = add_indicators(df_4h)
    
    d = df_d.iloc[-1]
    h4 = df_4h.iloc[-1]
    
    # Parametreler
    trend = d["close"] > d["EMA50"]
    rsi = pd.notna(d["RSI"]) and d["RSI"] > params["rsi_min"]
    adx = pd.notna(d["ADX"]) and d["ADX"] > params["adx_min"]
    volume = pd.notna(d["VOL_Z"]) and d["VOL_Z"] > params["volume_z_min"]
    para = pd.notna(d["CMF"]) and d["CMF"] > 0
    breakout = d["close"] > df_d["HH20"].iloc[-2] if len(df_d) > 20 else False
    mtf = pd.notna(h4["RSI"]) and h4["RSI"] > 50 and h4["close"] > h4["EMA50"]
    
    if all([trend, rsi, adx, volume, para, breakout, mtf]):
        return {
            "Hisse": symbol,
            "Fiyat": round(float(d["close"]), 2),
            "RSI": round(float(d["RSI"]), 2) if pd.notna(d["RSI"]) else None,
            "ADX": round(float(d["ADX"]), 2) if pd.notna(d["ADX"]) else None,
            "Hacim Skor": round(float(d["VOL_Z"]), 2) if pd.notna(d["VOL_Z"]) else None,
            "CMF": round(float(d["CMF"]), 3) if pd.notna(d["CMF"]) else None,
            "AI Yorum": ai_yorum(d)
        }
    return None

# =========================================
# 🎨 SIDEBAR AYARLARI
# =========================================

with st.sidebar:
    st.title("⚙️ Parametreler")
    
    rsi_min = st.slider("RSI Minimum", 30, 80, 55)
    adx_min = st.slider("ADX Minimum", 10, 50, 20)
    volume_z_min = st.slider("Hacim Z-Skor Min", 0.5, 5.0, 2.0)
    
    st.divider()
    
    max_hisse = st.slider("Maksimum İşlenecek Hisse", 50, 500, 200)
    use_fast_filter = st.checkbox("Hızlı Ön Filtre Kullan", value=True)
    
    st.divider()
    
    if st.button("🔄 Ayarları Sıfırla", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# =========================================
# 🖥️ ANA ARAYÜZ
# =========================================

st.title("🚀 BIST TrendScout PRO v3.5")
st.markdown("""
<div style='background: linear-gradient(90deg, #1e3c72, #2a5298); padding: 15px; border-radius: 10px; color: white;'>
<strong>📊 yfinance ile Gerçek Zamanlı BIST Analizi</strong>
</div>
""", unsafe_allow_html=True)

# Başlat butonu
if st.button("🔍 Taramayı Başlat", type="primary", use_container_width=True):
    
    params = {"rsi_min": rsi_min, "adx_min": adx_min, "volume_z_min": volume_z_min}
    
    with st.spinner("📡 BIST hisseleri yükleniyor..."):
        hisseler = get_bist_hisseler()
    
    if not hisseler:
        st.error("❌ Hisseler yüklenemedi. Lütfen daha sonra tekrar deneyin.")
        st.stop()
    
    st.info(f"✅ {len(hisseler)} hisse bulundu. Tarama başlıyor...")
    
    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    results_container = st.empty()
    
    results = []
    total = min(len(hisseler), max_hisse)
    
    for i, h in enumerate(hisseler[:total]):
        # İlerleme güncelle
        progress_bar.progress((i + 1) / total)
        status_text.text(f"🔎 İşleniyor: {h} ({i+1}/{total})")
        
        # Hızlı filtre
        if use_fast_filter and not hizli_filtre(h):
            continue
        
        # Detaylı analiz
        res = analyze_symbol(h, params)
        if res:
            results.append(res)
            # Canlı sonuç göster
            if results:
                results_container.dataframe(
                    pd.DataFrame(results).sort_values("Hacim Skor", ascending=False),
                    use_container_width=True,
                    hide_index=True
                )
        
        # Rate limit için kısa bekleme
        time.sleep(0.3)  # yfinance için biraz daha uzun bekleme
    
    progress_bar.empty()
    status_text.empty()
    
    # =========================================
    # 📊 SONUÇLARI GÖSTER
    # =========================================
    
    st.success(f"🎉 Tarama tamamlandı! **{len(results)}** PRO sinyal bulundu")
    
    if results:
        df_results = pd.DataFrame(results).sort_values("Hacim Skor", ascending=False)
        
        # Metrik kartları
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📈 Toplam Sinyal", len(results))
        with col2:
            st.metric("💹 Ort. Fiyat", f"{df_results['Fiyat'].mean():.2f} ₺")
        with col3:
            st.metric("🔥 Ort. RSI", f"{df_results['RSI'].dropna().mean():.1f}")
        with col4:
            st.metric("🎯 Ort. ADX", f"{df_results['ADX'].dropna().mean():.1f}")
        
        # Detaylı tablo
        st.subheader("📋 Sinyal Detayları")
        st.dataframe(
            df_results.style.format({
                "Fiyat": "{:.2f}",
                "RSI": "{:.2f}",
                "ADX": "{:.2f}",
                "Hacim Skor": "{:.2f}",
                "CMF": "{:.3f}"
            }).background_gradient(subset=["Hacim Skor"], cmap="YlOrRd"),
            use_container_width=True,
            hide_index=True
        )
        
        # İndirme butonu
        csv = df_results.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            "📥 CSV Olarak İndir",
            data=csv,
            file_name=f"bist_sinyaller_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        # JSON kaydet (opsiyonel)
        with st.expander("🗄️ JSON Verisi"):
            st.json(results)
    
    else:
        st.warning("⚠️ Kriterlerinize uygun sinyal bulunamadı. Parametreleri gevşetmeyi deneyin.")

# =========================================
# ℹ️ BİLGİ PANELİ
# =========================================

with st.expander("📖 Nasıl Kullanılır?"):
    st.markdown("""
    ### 🔧 Parametre Açıklamaları
    - **RSI Minimum**: Momentum gücü için minimum RSI değeri (55+ önerilir)
    - **ADX Minimum**: Trend kuvveti için minimum ADX değeri (20+ trend var demektir)
    - **Hacim Z-Skor**: Normalin üzerindeki hacim patlamalarını filtreler
    
    ### 🎯 Sinyal Kriterleri
    1. ✅ Fiyat > EMA50 (Yükseliş trendi)
    2. ✅ RSI > threshold (Güçlü momentum)
    3. ✅ ADX > threshold (Kuvvetli trend)
    4. ✅ Hacim Z-Skor > 2 (Anormal hacim)
    5. ✅ CMF > 0 (Para girişi)
    6. ✅ 20 günlük zirve kırılımı
    7. ✅ 4H timeframe'de onay (MTF)
    
    ### 💡 yfinance Notları
    - BIST hisseleri `.IS` uzantısıyla çekilir (örn: `THYAO.IS`)
    - 4 saatlik veri yerine 1 saatlik veri kullanılır (yfinance limiti)
    - Veriler 15-20 dakika gecikmeli olabilir
    
    > ⚠️ **Uyarı**: Bu araç yatırım tavsiyesi DEĞİLDİR. Tüm analizler eğitim amaçlıdır.
    """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 0.9em;'>"
    "📊 BIST TrendScout PRO v3.5 | yfinance Edition | "
    f"Son güncelleme: {datetime.now().strftime('%H:%M:%S')}"
    "</div>",
    unsafe_allow_html=True
)
