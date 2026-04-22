"""
BIST TrendScout Pro v2.1 - Web Arayüzü
Streamlit tabanlı gelişmiş teknik analiz ve hisse tarama sistemi
"""

import streamlit as st
import pandas as pd
import ssl
from urllib import request
from tvDatafeed import TvDatafeed, Interval
import json
import os
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Sayfa yapılandırması
st.set_page_config(
    page_title="BIST TrendScout Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Özel CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .trend-strong {
        color: #00ff00;
        font-weight: bold;
    }
    .trend-new {
        color: #ffa500;
        font-weight: bold;
    }
    .trend-weak {
        color: #ff4444;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- KONFİGÜRASYON ---
class TrendScoutConfig:
    def __init__(self, config_file="trendscout_config.json"):
        self.config_file = config_file
        self.default_config = {
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
        self.config = self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self.default_config.update(loaded)
        return self.default_config

    def save_config(self):
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def get(self, key, default=None):
        keys = key.split(".")
        val = self.config
        for k in keys:
            val = val.get(k, default)
        return val
    
    def update(self, key, value):
        keys = key.split(".")
        target = self.config
        for k in keys[:-1]:
            target = target.setdefault(k, {})
        target[keys[-1]] = value
        self.save_config()

# --- GÖSTERGELER ---
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
    tr = pd.concat([
        high - low,
        abs(high - close.shift()),
        abs(low - close.shift())
    ], axis=1).max(axis=1)

    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)

    atr = tr.rolling(period).mean()
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    return dx.rolling(period).mean()

# --- VERİ ÇEKME ---
@st.cache_data(ttl=300)
def isyatirim_kodlar():
    url = "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/Temel-Degerler-Ve-Oranlar.aspx"
    context = ssl._create_unverified_context()
    html = request.urlopen(url, context=context).read()
    tablolar = pd.read_html(html, decimal=",", thousands=".")
    for t in tablolar:
        if "Kod" in t.columns:
            return t["Kod"].dropna().tolist()
    return []

@st.cache_data(ttl=300)
def teknik_veri(hisse, config):
    try:
        tv = TvDatafeed()
        df = tv.get_hist(
            symbol=hisse,
            exchange=config.get("veri_ayarlari.exchange"),
            interval=Interval.in_daily,
            n_bars=config.get("veri_ayarlari.n_bars")
        )
        if df is None or len(df) < 20:
            return None

        df["RSI"] = rsi_hesapla(df, config.get("kriterler.rsi_period"))
        df["Momentum"] = momentum_hesapla(df, config.get("kriterler.momentum_period"))
        df["ADX"] = adx_hesapla(df, config.get("kriterler.adx_period"))
        df["Hacim_Ort_20"] = df["volume"].rolling(20).mean()

        return df
    except:
        return None

def hacim_artis(bugun, dun):
    return bugun["volume"] / dun["volume"] if dun["volume"] > 0 else 0

# --- ANA ANALİZ FONKSİYONU ---
def trendscout_analiz(config, progress_bar=None):
    hisseler = isyatirim_kodlar()
    sonuc = []
    
    for idx, hisse in enumerate(hisseler):
        if progress_bar:
            progress_bar.progress((idx + 1) / len(hisseler), f"Analiz ediliyor: {hisse}")
        
        df = teknik_veri(hisse, config)
        if df is None:
            continue

        bugun, dun = df.iloc[-1], df.iloc[-2]

        hacim_k = hacim_artis(bugun, dun)
        hacim_patlamasi = bugun["volume"] > (bugun["Hacim_Ort_20"] * config.get("kriterler.hacim_artis_min"))

        if (
            hacim_k >= config.get("kriterler.hacim_artis_min")
            and hacim_patlamasi
            and bugun["RSI"] > config.get("kriterler.rsi_min")
            and bugun["Momentum"] > config.get("kriterler.momentum_min")
        ):
            adx = bugun["ADX"]
            if adx > config.get("kriterler.adx_guclu_min"):
                trend = "Güçlü Trend"
                trend_class = "trend-strong"
            elif adx > config.get("kriterler.adx_trend_min"):
                trend = "Yeni Trend"
                trend_class = "trend-new"
            else:
                trend = "Zayıf"
                trend_class = "trend-weak"

            sonuc.append({
                "Hisse": hisse,
                "Fiyat": round(bugun["close"], 2),
                "RSI": round(bugun["RSI"], 2),
                "Momentum": round(bugun["Momentum"], 2),
                "ADX": round(adx, 2),
                "Hacim_Artis": round(hacim_k, 2),
                "Trend": trend,
                "Trend_Class": trend_class
            })
    
    return pd.DataFrame(sonuc)

# --- GRAFİK ÇİZİMİ ---
def hisse_grafik(hisse, df):
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=("Fiyat", "RSI", "ADX"),
        row_heights=[0.5, 0.25, 0.25]
    )
    
    # Fiyat grafiği
    fig.add_trace(
        go.Candlestick(x=df.index, open=df['open'], high=df['high'],
                      low=df['low'], close=df['close'], name="Fiyat"),
        row=1, col=1
    )
    
    # RSI grafiği
    fig.add_trace(
        go.Scatter(x=df.index, y=df['RSI'], mode='lines', name='RSI', line=dict(color='purple')),
        row=2, col=1
    )
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
    
    # ADX grafiği
    fig.add_trace(
        go.Scatter(x=df.index, y=df['ADX'], mode='lines', name='ADX', line=dict(color='orange')),
        row=3, col=1
    )
    fig.add_hline(y=25, line_dash="dash", line_color="gray", row=3, col=1)
    
    fig.update_layout(
        title=f"{hisse} - Teknik Analiz Grafiği",
        xaxis_title="Tarih",
        height=800,
        showlegend=True
    )
    
    return fig

# --- WEB ARAYÜZÜ ---
def main():
    # Başlık
    st.markdown("""
    <div class="main-header">
        <h1>🚀 BIST TrendScout Pro v2.1</h1>
        <p>Gelişmiş Teknik Analiz ve Hisse Tarama Sistemi</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar - Konfigürasyon
    with st.sidebar:
        st.header("⚙️ Analiz Parametreleri")
        
        config = TrendScoutConfig()
        
        st.subheader("📊 Teknik Göstergeler")
        rsi_min = st.slider("Minimum RSI", 30, 80, config.get("kriterler.rsi_min"), 1)
        momentum_min = st.slider("Minimum Momentum", 90, 150, config.get("kriterler.momentum_min"), 1)
        hacim_artis_min = st.slider("Hacim Artış Katsayısı", 1.0, 5.0, config.get("kriterler.hacim_artis_min"), 0.1)
        adx_trend_min = st.slider("ADX Trend Eşiği", 10, 40, config.get("kriterler.adx_trend_min"), 1)
        adx_guclu_min = st.slider("ADX Güçlü Trend Eşiği", 20, 50, config.get("kriterler.adx_guclu_min"), 1)
        
        st.subheader("📈 Veri Ayarları")
        n_bars = st.slider("Gün Sayısı", 30, 200, config.get("veri_ayarlari.n_bars"), 10)
        
        if st.button("🔄 Parametreleri Güncelle"):
            config.update("kriterler.rsi_min", rsi_min)
            config.update("kriterler.momentum_min", momentum_min)
            config.update("kriterler.hacim_artis_min", hacim_artis_min)
            config.update("kriterler.adx_trend_min", adx_trend_min)
            config.update("kriterler.adx_guclu_min", adx_guclu_min)
            config.update("veri_ayarlari.n_bars", n_bars)
            st.success("✅ Parametreler güncellendi!")
            st.rerun()
        
        st.markdown("---")
        st.info("💡 **İpucu:** Parametreleri değiştirip 'Analiz Başlat' butonuna tıklayın.")
    
    # Ana içerik
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📊 Analiz Edilecek Hisse", len(isyatirim_kodlar()))
    with col2:
        st.metric("🎯 RSI Eşiği", config.get("kriterler.rsi_min"))
    with col3:
        st.metric("📈 Momentum Eşiği", config.get("kriterler.momentum_min"))
    
    # Analiz butonu
    if st.button("🔍 Analiz Başlat", type="primary", use_container_width=True):
        with st.spinner("Analiz yapılıyor..."):
            progress_bar = st.progress(0)
            results_df = trendscout_analiz(config, progress_bar)
            progress_bar.empty()
        
        if not results_df.empty:
            st.success(f"✅ Analiz tamamlandı! {len(results_df)} hisse bulundu.")
            
            # Tablo gösterimi
            st.subheader("📋 Taranan Hisseler")
            
            # Renklendirme için stil
            def color_trend(val):
                if val == "Güçlü Trend":
                    return 'color: #00ff00; font-weight: bold'
                elif val == "Yeni Trend":
                    return 'color: #ffa500; font-weight: bold'
                return 'color: #ff4444; font-weight: bold'
            
            styled_df = results_df.style.applymap(color_trend, subset=['Trend'])
            st.dataframe(styled_df, use_container_width=True, height=400)
            
            # CSV export
            csv = results_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 CSV Olarak İndir",
                data=csv,
                file_name=f"trendscout_raporu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            # Detaylı grafikler
            st.subheader("📈 Hisse Detayları")
            selected_hisse = st.selectbox("Grafiğini görmek istediğiniz hisseyi seçin:", results_df['Hisse'].tolist())
            
            if selected_hisse:
                with st.spinner("Veri çekiliyor..."):
                    df = teknik_veri(selected_hisse, config)
                    if df is not None:
                        fig = hisse_grafik(selected_hisse, df)
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Hisse bilgileri
                        hisse_data = results_df[results_df['Hisse'] == selected_hisse].iloc[0]
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("💰 Fiyat", f"₺{hisse_data['Fiyat']}")
                        with col2:
                            st.metric("📊 RSI", hisse_data['RSI'])
                        with col3:
                            st.metric("⚡ Momentum", hisse_data['Momentum'])
                        with col4:
                            st.metric("📈 ADX", hisse_data['ADX'])
        else:
            st.warning("⚠️ Kriterleri karşılayan hisse bulunamadı. Parametreleri gevşetmeyi deneyin.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: gray;">
        <p>BIST TrendScout Pro v2.1 | Gelişmiş Teknik Analiz ve Tarama Sistemi</p>
        <p>© 2024 - Tüm hakları saklıdır.</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
