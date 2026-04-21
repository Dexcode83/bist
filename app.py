# =====================================================
# 🚀 BIST TrendScout Pro v2.1 - Streamlit Dashboard
# Gelişmiş Teknik Analiz ve Hisse Tarama Sistemi
# =====================================================
# Çalıştırma: streamlit run app.py
# =====================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from tvDatafeed import TvDatafeed, Interval
from tqdm import tqdm
import json
import os
from datetime import datetime
import ssl
from urllib import request
import time

# Sayfa ayarları
st.set_page_config(page_title="BIST TrendScout Pro", page_icon="📊", layout="wide")

# =====================================================
# 🎨 CSS & TEMALAR
# =====================================================
st.markdown("""
<style>
    .main-header { font-size: 2rem; font-weight: bold; color: #1f77b4; text-align: center; padding: 1rem; }
    .metric-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; color: white; text-align: center; }
    .bull { color: #22c55e; font-weight: bold; }
    .bear { color: #ef4444; font-weight: bold; }
    .trend-strong { color: #dc2626; font-weight: bold; }
    .trend-new { color: #2563eb; font-weight: bold; }
    .trend-weak { color: #f59e0b; font-weight: bold; }
    .stDataFrame { font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

# =====================================================
# ⚙️ KONFİGÜRASYON YÖNETİMİ
# =====================================================
@st.cache_data(ttl=3600)
def load_config():
    """Varsayılan konfigürasyonu yükler"""
    return {
        "kriterler": {
            "hacim_artis_min": 2.5,
            "rsi_min": 57,
            "momentum_min": 105,
            "rsi_period": 14,
            "momentum_period": 10,
            "adx_period": 14,
            "adx_trend_min": 19,
            "adx_guclu_min": 29
        },
        "veri_ayarlari": {
            "n_bars": 50,
            "exchange": "BIST",
            "interval": "gun"
        }
    }

def save_results(results, filename="trendscout_sonuc.json"):
    """Sonuçları JSON dosyasına kaydeder"""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return filename

# =====================================================
# 📡 VERİ ÇEKME (İş Yatırım + TradingView)
# =====================================================
@st.cache_data(ttl=1800)
def get_bist_hisseleri():
    """İş Yatırım'dan BIST hisse kodlarını çeker"""
    url = "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/Temel-Degerler-Ve-Oranlar.aspx"
    try:
        context = ssl._create_unverified_context()
        html = request.urlopen(url, context=context, timeout=30).read()
        tablolar = pd.read_html(html, decimal=",", thousands=".")
        for t in tablolar:
            if "Kod" in t.columns:
                return t["Kod"].dropna().astype(str).str.strip().tolist()
    except:
        pass
    # Yedek BIST 30 listesi
    return ['AKBNK', 'ASELS', 'BIMAS', 'EREGL', 'FROTO', 'GARAN', 'HALKB', 'ISCTR', 
            'KCHOL', 'KOZAL', 'KRDMD', 'PETKM', 'PGSUS', 'SAHOL', 'SISE', 'TCELL', 
            'THYAO', 'TKFEN', 'TUPRS', 'ULKER', 'VAKBN', 'YKBNK', 'HEKTS', 'MAVI',
            'SOKM', 'DOHOL', 'AFYON', 'AKCNS', 'AKFGY', 'AKGRT']

@st.cache_data(ttl=300)
def fetch_tv_data(symbol, n_bars=50):
    """TradingView'den hisse verisi çeker"""
    try:
        tv = TvDatafeed()
        df = tv.get_hist(symbol=symbol, exchange="BIST", interval=Interval.in_daily, n_bars=n_bars)
        if df is None or len(df) < 20:
            return None
        return df
    except:
        return None

# =====================================================
# 🧮 TEKNİK GÖSTERGELER (Orijinal Mantık)
# =====================================================
def rsi_hesapla(df, period=14):
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = -delta.where(delta < 0, 0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def momentum_hesapla(df, period=10):
    return (df["close"] / df["close"].shift(period)) * 100

def adx_hesapla(df, period=14):
    high, low, close = df["high"], df["low"], df["close"]
    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    atr = tr.rolling(period).mean()
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    return dx.rolling(period).mean()

def analyze_stock(symbol, config):
    """Tek hisse için analiz"""
    df = fetch_tv_data(symbol, config["veri_ayarlari"]["n_bars"])
    if df is None:
        return None
    
    # Göstergeleri hesapla
    df["RSI"] = rsi_hesapla(df, config["kriterler"]["rsi_period"])
    df["Momentum"] = momentum_hesapla(df, config["kriterler"]["momentum_period"])
    df["ADX"] = adx_hesapla(df, config["kriterler"]["adx_period"])
    df["Hacim_Ort_20"] = df["volume"].rolling(20).mean()
    
    bugun, dun = df.iloc[-1], df.iloc[-2]
    
    # Hacim artışı
    hacim_k = bugun["volume"] / dun["volume"] if dun["volume"] > 0 else 0
    hacim_patlamasi = bugun["volume"] > (bugun["Hacim_Ort_20"] * config["kriterler"]["hacim_artis_min"])
    
    # Kriter kontrolü
    if not (
        hacim_k >= config["kriterler"]["hacim_artis_min"]
        and hacim_patlamasi
        and bugun["RSI"] > config["kriterler"]["rsi_min"]
        and bugun["Momentum"] > config["kriterler"]["momentum_min"]
    ):
        return None
    
    # Trend gücü
    adx = bugun["ADX"]
    if pd.isna(adx):
        return None
    if adx > config["kriterler"]["adx_guclu_min"]:
        trend = "Güçlü Trend 🔥"
    elif adx > config["kriterler"]["adx_trend_min"]:
        trend = "Yeni Trend 📈"
    else:
        trend = "Zayıf ⚠️"
    
    return {
        "Hisse": symbol,
        "Fiyat": round(bugun["close"], 2),
        "RSI": round(bugun["RSI"], 2),
        "Momentum": round(bugun["Momentum"], 2),
        "ADX": round(adx, 2),
        "Hacim_Artis": round(hacim_k, 2),
        "Hacim_Patlamasi": True,
        "Trend": trend,
        "df": df  # Grafik için
    }

# =====================================================
# 📈 PLOTLY GRAFİK
# =====================================================
def create_chart(df, symbol):
    """Interaktif mum grafik oluşturur"""
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        name='Fiyat', increasing_line_color='#22c55e', decreasing_line_color='#ef4444'
    )])
    
    # Hacim
    fig.add_trace(go.Bar(
        x=df.index, y=df['volume'], name='Hacim', marker_color=['#22c55e' if c>=o else '#ef4444' 
        for o, c in zip(df['open'], df['close'])], opacity=0.5, yaxis='y2'
    ))
    
    fig.update_layout(
        title=f"{symbol} - Teknik Analiz",
        yaxis_title='Fiyat (TL)',
        yaxis2_title='Hacim',
        yaxis2=dict(overlaying='y', side='right'),
        hovermode='x unified',
        template='plotly_white',
        height=500,
        xaxis_rangeslider_visible=False
    )
    return fig

# =====================================================
# 🔄 PARALEL TARAMA
# =====================================================
def run_scan(symbols, config, progress_callback):
    """Tüm hisseleri tarar"""
    results = []
    total = len(symbols)
    
    for i, hisse in enumerate(symbols):
        try:
            result = analyze_stock(hisse, config)
            if result:
                results.append(result)
        except:
            pass
        
        if progress_callback and (i + 1) % 10 == 0:
            progress_callback(i + 1, total, len(results))
    
    return sorted(results, key=lambda x: x["ADX"], reverse=True)

# =====================================================
# 🎨 SIDEBAR - AYARLAR
# =====================================================
def render_sidebar():
    with st.sidebar:
        st.header("⚙️ Tarama Ayarları")
        
        # Kriterler
        st.subheader("📊 Kriterler")
        hacim_min = st.slider("Min Hacim Artışı (x)", 1.0, 5.0, 2.5, 0.1)
        rsi_min = st.slider("Min RSI", 30, 80, 57)
        momentum_min = st.slider("Min Momentum", 90, 120, 105)
        adx_trend = st.slider("ADX Trend Eşiği", 10, 40, 19)
        adx_guclu = st.slider("ADX Güçlü Trend", 20, 50, 29)
        
        # Veri Ayarları
        st.subheader("📡 Veri Ayarları")
        n_bars = st.selectbox("Geçmiş Veri (Bar)", [30, 50, 100, 200], index=1)
        
        # Hisse Seçimi
        st.subheader("📋 Hisse Listesi")
        if st.button("🔄 Listeyi Yenile", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        all_symbols = get_bist_hisseleri()
        search = st.text_input("Hisse Ara", placeholder="örn: ASELS")
        filtered = [s for s in all_symbols if search.upper() in s] if search else all_symbols
        
        selected = st.multiselect("Seçili Hisseler", all_symbols, default=filtered[:20] if filtered else all_symbols[:20])
        
        # Aksiyon
        st.divider()
        scan_btn = st.button("🚀 TARAMAYI BAŞLAT", type="primary", use_container_width=True)
        
        config = {
            "kriterler": {
                "hacim_artis_min": hacim_min,
                "rsi_min": rsi_min,
                "momentum_min": momentum_min,
                "rsi_period": 14,
                "momentum_period": 10,
                "adx_period": 14,
                "adx_trend_min": adx_trend,
                "adx_guclu_min": adx_guclu
            },
            "veri_ayarlari": {
                "n_bars": n_bars,
                "exchange": "BIST",
                "interval": "gun"
            }
        }
        
        return {"symbols": selected, "config": config, "scan": scan_btn}

# =====================================================
# 🚀 ANA UYGULAMA
# =====================================================
def main():
    st.markdown('<div class="main-header">🚀 BIST TrendScout Pro v2.1</div>', unsafe_allow_html=True)
    st.caption("Gelişmiş Hacim Patlaması + Momentum + ADX Tarama Sistemi")
    
    if 'results' not in st.session_state:
        st.session_state.results = None
    
    settings = render_sidebar()
    
    if settings["scan"]:
        with st.status("🔄 Tarama başlatılıyor...", expanded=True) as status:
            pb = st.progress(0)
            txt = st.empty()
            
            def cb(done, total, found):
                pb.progress(done / total)
                txt.text(f"📊 Tarandı: {done}/{total} | ✅ Bulundu: {found}")
            
            start = time.time()
            results = run_scan(settings["symbols"], settings["config"], cb)
            elapsed = time.time() - start
            
            st.session_state.results = results
            status.update(label=f"✅ Tamamlandı! {len(results)} hisse bulundu. ({elapsed:.1f} sn)", state="complete", expanded=False)
            st.rerun()
    
    # Sonuçları göster
    if st.session_state.results is not None:
        results = st.session_state.results
        st.divider()
        
        # Özet
        c1, c2, c3 = st.columns(3)
        c1.metric("📈 Taranan Hisse", len(settings["symbols"]))
        c2.metric("✅ Kriterlere Uyan", len(results))
        c3.metric("🎯 Ort. ADX", f"{np.mean([r['ADX'] for r in results]):.1f}" if results else "-")
        
        # Tablo
        st.subheader("🏆 Tarama Sonuçları")
        
        if not results:
            st.info("⚠️ Kriterlere uygun hisse bulunamadı. Ayarları gevşetmeyi deneyin.")
        else:
            # DataFrame hazırla
            data = [{k: v for k, v in r.items() if k != "df"} for r in results]
            df = pd.DataFrame(data)
            
            # Renklendirme
            def color_trend(val):
                if "🔥" in val: return 'color: #dc2626; font-weight: bold'
                elif "📈" in val: return 'color: #2563eb; font-weight: bold'
                return 'color: #f59e0b; font-weight: bold'
            
            styled = df.style.map(color_trend, subset=['Trend'])
            st.dataframe(styled, use_container_width=True, height=400)
            
            # CSV İndir
            csv = df.drop(columns=["df"], errors='ignore').to_csv(index=False, encoding='utf-8-sig')
            st.download_button("📥 CSV İndir", csv, file_name=f"trendscout_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
            
            # JSON Kaydet
            if st.button("💾 JSON Olarak Kaydet"):
                filename = save_results([{k: v for k, v in r.items() if k != "df"} for r in results])
                st.success(f"✅ Kaydedildi: {filename}")
            
            # Detaylı Grafik
            st.divider()
            col1, col2 = st.columns([3, 1])
            with col1:
                selected = st.selectbox("🔍 Grafik İçin Hisse Seçin", df["Hisse"].tolist())
            with col2:
                if st.button("📊 Grafiği Göster", use_container_width=True):
                    pass  # Otomatik gösterilecek
            
            if selected:
                item = next((r for r in results if r["Hisse"] == selected), None)
                if item and "df" in item:
                    st.plotly_chart(create_chart(item["df"], selected), use_container_width=True)
                    
                    # Detay Bilgileri
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("💰 Fiyat", f"{item['Fiyat']} TL")
                    c2.metric("📊 RSI", item["RSI"])
                    c3.metric("🚀 Momentum", item["Momentum"])
                    c4.metric("📈 ADX", item["ADX"])
    
    # Footer
    st.divider()
    st.caption("⚠️ Bu analizler bilgilendirme amaçlıdır. Yatırım tavsiyesi değildir. Veriler TradingView altyapısından alınır.")

if __name__ == "__main__":
    main()
