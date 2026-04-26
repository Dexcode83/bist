"""
BIST TrendScout Pro v2.1 - Web Arayüzü (yfinance versiyonu)
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import requests  # 🆕 TradingView API için eklendi

# Sayfa yapılandırması
st.set_page_config(
    page_title="BIST TrendScout Pro",
    page_icon="📈",
    layout="wide"
)

# CSS
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
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# 🆕 TradingView'den BIST hisse listesi çekme fonksiyonu
@st.cache_data(ttl=3600)
def bist_tum_hisseler():
    """TradingView'den tüm BIST hisselerini çeker"""
    url = "https://scanner.tradingview.com/turkey/scan"
    
    payload = {
        "filter": [
            {"left": "exchange", "operation": "equal", "right": "BIST"}
        ],
        "options": {"lang": "tr"},
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": ["name"]
    }
    
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        hisseler = []
        for item in data["data"]:
            name = item["d"][0].replace("BIST:", "").strip().upper()
            if 3 <= len(name) <= 5 and name.isalpha():
                hisseler.append(f"{name}.IS")
        
        return list(set(hisseler))
    except Exception as e:
        st.warning(f"TradingView'den hisse listesi çekilemedi: {e}")
        # Yedek liste
        return [
            'THYAO.IS', 'ASELS.IS', 'GARAN.IS', 'ISCTR.IS', 'KCHOL.IS',
            'SISE.IS', 'TUPRS.IS', 'PETKM.IS', 'EREGL.IS', 'FROTO.IS',
            'SAHOL.IS', 'BIMAS.IS', 'TTKOM.IS', 'YKBNK.IS', 'AKBNK.IS',
            'KOZAL.IS', 'EKGYO.IS', 'TOASO.IS', 'OTKAR.IS', 'DOHOL.IS'
        ]

# Başlık
st.markdown("""
<div class="main-header">
    <h1>🚀 BIST TrendScout Pro v2.1</h1>
    <p>Gelişmiş Teknik Analiz ve Hisse Tarama Sistemi</p>
</div>
""", unsafe_allow_html=True)

# 🆕 Dinamik BIST hisse listesi (ESKİ sabit liste yerine)
with st.spinner("📊 BIST hisse listesi güncelleniyor..."):
    BIST_HISSELER = bist_tum_hisseler()
    if not BIST_HISSELER:
        st.error("Hisse listesi çekilemedi!")
        st.stop()

# Teknik göstergeler
def calculate_rsi(data, period=14):
    """RSI hesaplama"""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_momentum(data, period=10):
    """Momentum hesaplama"""
    return (data / data.shift(period)) * 100

def calculate_adx(df, period=14):
    """ADX hesaplama"""
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    tr = pd.concat([
        high - low,
        abs(high - close.shift()),
        abs(low - close.shift())
    ], axis=1).max(axis=1)
    
    atr = tr.rolling(window=period).mean()
    plus_dm = high.diff()
    plus_dm = plus_dm.where(plus_dm > 0, 0)
    minus_dm = -low.diff()
    minus_dm = minus_dm.where(minus_dm > 0, 0)
    
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx = dx.rolling(window=period).mean()
    
    return adx

def calculate_volume_spike(df, multiplier=2.5):
    """Hacim patlaması hesaplama"""
    volume_ma = df['Volume'].rolling(window=20).mean()
    return df['Volume'] > (volume_ma * multiplier)

@st.cache_data(ttl=300)
def fetch_stock_data(symbol, period="3mo"):
    """Hisse verisi çekme"""
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period=period)
        if df.empty:
            return None
        return df
    except Exception as e:
        st.warning(f"Veri çekilemedi {symbol}: {str(e)}")
        return None

def analyze_stock(symbol, params):
    """Tek hisse analizi"""
    df = fetch_stock_data(symbol)
    if df is None or len(df) < 30:
        return None
    
    # Göstergeleri hesapla
    df['RSI'] = calculate_rsi(df['Close'], params['rsi_period'])
    df['Momentum'] = calculate_momentum(df['Close'], params['momentum_period'])
    df['ADX'] = calculate_adx(df, params['adx_period'])
    df['Volume_Spike'] = calculate_volume_spike(df, params['hacim_artis_min'])
    df['Volume_Ratio'] = df['Volume'] / df['Volume'].rolling(20).mean()
    
    # Son gün verileri
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # Hacim kontrolü
    volume_ratio = last['Volume_Ratio']
    volume_spike = last['Volume_Spike']
    
    # Kriter kontrolü
    if (volume_ratio >= params['hacim_artis_min'] and
        volume_spike and
        last['RSI'] > params['rsi_min'] and
        last['Momentum'] > params['momentum_min']):
        
        adx = last['ADX']
        if adx > params['adx_guclu_min']:
            trend = "Güçlü Trend 🔥"
            trend_class = "strong"
        elif adx > params['adx_trend_min']:
            trend = "Yeni Trend 📈"
            trend_class = "new"
        else:
            trend = "Zayıf ⚠️"
            trend_class = "weak"
        
        return {
            'Hisse': symbol.replace('.IS', ''),
            'Fiyat': round(last['Close'], 2),
            'RSI': round(last['RSI'], 2),
            'Momentum': round(last['Momentum'], 2),
            'ADX': round(adx, 2),
            'Hacim_Artis': round(volume_ratio, 2),
            'Trend': trend,
            'Trend_Class': trend_class
        }
    return None

def create_chart(symbol, df):
    """Grafik oluşturma"""
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=("Fiyat", "RSI", "ADX"),
        row_heights=[0.5, 0.25, 0.25]
    )
    
    # Fiyat grafiği
    fig.add_trace(
        go.Candlestick(
            x=df.index, 
            open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'],
            name="Fiyat"
        ),
        row=1, col=1
    )
    
    # RSI
    fig.add_trace(
        go.Scatter(x=df.index, y=df['RSI'], mode='lines', name='RSI'),
        row=2, col=1
    )
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
    
    # ADX
    fig.add_trace(
        go.Scatter(x=df.index, y=df['ADX'], mode='lines', name='ADX'),
        row=3, col=1
    )
    fig.add_hline(y=25, line_dash="dash", line_color="gray", row=3, col=1)
    
    fig.update_layout(
        title=f"{symbol} - Teknik Analiz",
        height=800,
        xaxis_title="Tarih"
    )
    
    return fig

# Sidebar
with st.sidebar:
    st.header("⚙️ Analiz Parametreleri")
    
    # 🆕 Hisse sayısı bilgisi
    st.info(f"📊 Toplam {len(BIST_HISSELER)} hisse taranacak")
    
    params = {
        'rsi_min': st.slider("Minimum RSI", 30, 80, 57),
        'momentum_min': st.slider("Minimum Momentum", 90, 150, 105),
        'hacim_artis_min': st.slider("Hacim Artış Katsayısı", 1.0, 5.0, 2.5, 0.1),
        'adx_trend_min': st.slider("ADX Trend Eşiği", 10, 40, 19),
        'adx_guclu_min': st.slider("ADX Güçlü Trend Eşiği", 20, 50, 29),
        'rsi_period': 14,
        'momentum_period': 10,
        'adx_period': 14
    }
    
    st.markdown("---")
    analyze_btn = st.button("🔍 Analiz Başlat", type="primary", use_container_width=True)
    
    # 🆕 Manuel yenileme butonu
    if st.button("🔄 Hisse Listesini Yenile", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Ana içerik
if analyze_btn:
    with st.spinner("Analiz yapılıyor..."):
        progress_bar = st.progress(0)
        results = []
        
        for i, symbol in enumerate(BIST_HISSELER):
            progress_bar.progress((i + 1) / len(BIST_HISSELER), f"Analiz: {symbol}")
            result = analyze_stock(symbol, params)
            if result:
                results.append(result)
        
        progress_bar.empty()
        
        if results:
            df_results = pd.DataFrame(results)
            st.session_state.results = df_results
            st.success(f"✅ Analiz tamamlandı! {len(results)} hisse bulundu.")
        else:
            st.warning("⚠️ Kriterleri karşılayan hisse bulunamadı.")

# Sonuçları göster
if 'results' in st.session_state and st.session_state.results is not None:
    df_results = st.session_state.results
    
    # Tablo
    st.subheader("📋 Taranan Hisseler")
    
    # Renklendirme
    def color_trend(val):
        if 'Güçlü' in val:
            return 'background-color: #00ff0044'
        elif 'Yeni' in val:
            return 'background-color: #ffa50044'
        return 'background-color: #ff444444'
    
    styled_df = df_results.style.applymap(color_trend, subset=['Trend'])
    st.dataframe(styled_df, use_container_width=True, height=400)
    
    # İstatistikler
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Toplam Hisseler", len(df_results))
    with col2:
        st.metric("Güçlü Trend", len(df_results[df_results['Trend'].str.contains('Güçlü')]))
    with col3:
        st.metric("Ortalama RSI", round(df_results['RSI'].mean(), 1))
    with col4:
        st.metric("Ortalama Momentum", round(df_results['Momentum'].mean(), 1))
    
    # CSV export
    csv = df_results.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 CSV İndir",
        data=csv,
        file_name=f"bist_tarama_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
    
    # Detaylı grafik
    st.subheader("📈 Detaylı Analiz")
    selected = st.selectbox("Hisse seçin:", df_results['Hisse'].tolist())
    
    if selected:
        symbol = f"{selected}.IS"
        df = fetch_stock_data(symbol, period="3mo")
        if df is not None:
            # Göstergeleri ekle
            df['RSI'] = calculate_rsi(df['Close'], 14)
            df['ADX'] = calculate_adx(df, 14)
            
            fig = create_chart(symbol, df)
            st.plotly_chart(fig, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray;">
    <p>BIST TrendScout Pro v2.1 | Veri kaynağı: Yahoo Finance & TradingView</p>
</div>
""", unsafe_allow_html=True)
