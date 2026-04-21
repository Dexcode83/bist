# =====================================================
# 🚀 BIST TEKNİK ANALİZ WEB DASHBOARD
# Streamlit + Plotly + Yahoo Finance Entegrasyonu
# =====================================================
# Çalıştırma: streamlit run app.py
# =====================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import yfinance as yf
import ta
from scipy import signal
import ssl
from urllib import request
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
import base64
from io import BytesIO

warnings.filterwarnings('ignore')
st.set_page_config(page_title="BIST Teknik Analiz", page_icon="📊", layout="wide")

# =====================================================
# 🎨 CSS STİL VE TEMALAR
# =====================================================
st.markdown("""
<style>
    .main-header { font-size: 2rem; font-weight: bold; color: #1f77b4; text-align: center; padding: 1rem; }
    .metric-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; color: white; text-align: center; }
    .metric-value { font-size: 2rem; font-weight: bold; }
    .metric-label { font-size: 0.9rem; opacity: 0.9; }
    .bull-signal { color: #22c55e; font-weight: bold; }
    .bear-signal { color: #ef4444; font-weight: bold; }
    .neutral-signal { color: #f59e0b; font-weight: bold; }
    .stDataFrame { font-size: 0.9rem; }
    div[data-testid="stMetricValue"] { font-size: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# =====================================================
# 🔄 CACHE FONKSİYONLARI (Performans Optimizasyonu)
# =====================================================
@st.cache_data(ttl=3600)
def get_bist_hisseleri():
    """İş Yatırım'dan BIST hisse kodlarını çeker (1 saat cache)"""
    url = "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/Temel-Degerler-Ve-Oranlar.aspx"
    try:
        context = ssl._create_unverified_context()
        html = request.urlopen(url, context=context, timeout=30).read()
        tablolar = pd.read_html(html, decimal=",", thousands=".")
        for t in tablolar:
            if "Kod" in t.columns:
                kodlar = t["Kod"].dropna().astype(str).str.strip().tolist()
                kodlar = [f"{k.strip()}.IS" for k in kodlar if len(k.strip()) >= 3 and k.strip() != 'Kod']
                return kodlar
    except:
        pass
    return _yedek_liste()

@st.cache_data(ttl=3600)
def _yedek_liste():
    """Yedek BIST 100 listesi"""
    return [
        'AKBNK.IS', 'ASELS.IS', 'BIMAS.IS', 'EREGL.IS', 'FROTO.IS', 'GARAN.IS',
        'HALKB.IS', 'ISCTR.IS', 'KCHOL.IS', 'KOZAL.IS', 'KRDMD.IS', 'PETKM.IS',
        'PGSUS.IS', 'SAHOL.IS', 'SISE.IS', 'TCELL.IS', 'THYAO.IS', 'TKFEN.IS',
        'TUPRS.IS', 'ULKER.IS', 'VAKBN.IS', 'YKBNK.IS', 'HEKTS.IS', 'MAVI.IS',
        'SOKM.IS', 'DOHOL.IS', 'AFYON.IS', 'AKCNS.IS', 'AKFGY.IS', 'AKGRT.IS',
        'AKSEN.IS', 'ALBRK.IS', 'ALCAR.IS', 'ALFAS.IS', 'ALGYO.IS', 'ANACM.IS',
        'ANSGR.IS', 'ARCLK.IS', 'ARSAN.IS', 'ASTOR.IS', 'AYGAZ.IS', 'BAGFS.IS',
        'BASGZ.IS', 'BAYRK.IS', 'BERA.IS', 'BESKT.IS', 'BIZIM.IS', 'BOLUC.IS',
        'BOMAP.IS', 'BRISA.IS', 'BRMEN.IS', 'BRYAT.IS', 'BUCIM.IS', 'CELHA.IS',
        'CEMTS.IS', 'CIMSA.IS', 'COSMO.IS', 'CRDFA.IS', 'CRMSN.IS', 'DENGE.IS',
        'DERIM.IS', 'DEVA.IS', 'DGGYO.IS', 'DITAS.IS', 'DOAS.IS', 'DOGU.IS',
        'DRHMA.IS', 'ECILC.IS', 'ECZYT.IS', 'EGGUB.IS', 'EGPRO.IS', 'EKGYO.IS',
        'EMKEL.IS', 'ERBOS.IS', 'ERCIS.IS', 'ERUHC.IS', 'ESCOM.IS', 'ESGBA.IS',
        'ETILR.IS', 'EUPWR.IS', 'FENER.IS', 'FINBN.IS', 'FLAP.IS', 'FONET.IS',
        'FORMT.IS', 'GOODY.IS', 'GOZDE.IS', 'GSDDE.IS', 'GUBRF.IS', 'HUBVC.IS',
        'IHEVA.IS', 'IHGZT.IS', 'IHLGM.IS', 'IHLAS.IS', 'IKGYO.IS', 'INDES.IS',
        'INFOP.IS', 'INGRM.IS', 'ISDMR.IS', 'ISFIN.IS', 'ISGYO.IS', 'ISKUR.IS',
        'ISMEN.IS', 'IZDEM.IS', 'IZMDC.IS', 'IZTAR.IS', 'JANTS.IS', 'KAREL.IS',
        'KARSN.IS', 'KATSN.IS', 'KAYA.IS', 'KCAER.IS', 'KENT.IS', 'KERVT.IS',
        'KLRHO.IS', 'KLSER.IS', 'KONTR.IS', 'KONYA.IS', 'KOZAA.IS', 'KRNVR.IS',
        'KUTPO.IS', 'KUYAS.IS', 'KZLBM.IS', 'LIDER.IS', 'LINKA.IS', 'LOGMA.IS',
        'LUXKM.IS', 'MAKTK.IS', 'MARTI.IS', 'MATAM.IS', 'MERKO.IS', 'MESYK.IS',
        'METUR.IS', 'MGROS.IS', 'MIATK.IS', 'MONDI.IS', 'MPARK.IS', 'NETAS.IS',
        'NIBAS.IS', 'NUHCM.IS', 'NUHCF.IS', 'OYLUM.IS', 'OYAKC.IS', 'OYPGY.IS',
        'PENGD.IS', 'PERGS.IS', 'PLTGG.IS', 'PNSUT.IS', 'POLTK.IS', 'POLHO.IS',
        'PRKAB.IS', 'PRKME.IS', 'PSDTC.IS', 'PSTIL.IS', 'QNBFL.IS', 'REYDR.IS',
        'ROTO.IS', 'SANKO.IS', 'SANFM.IS', 'SARDE.IS', 'SELEC.IS', 'SELSA.IS',
        'SKBNK.IS', 'SMRTG.IS', 'SODA.IS', 'SONME.IS', 'SSMEN.IS', 'TATGD.IS',
        'TEFAS.IS', 'TGBFB.IS', 'TKNSA.IS', 'TLMAN.IS', 'TOSTON.IS', 'TRCAS.IS',
        'TRGYO.IS', 'TRKCM.IS', 'TTRAK.IS', 'TUCLK.IS', 'TURSG.IS', 'UBAVS.IS',
        'UCLAS.IS', 'ULUUN.IS', 'UNYEC.IS', 'USAK.IS', 'UTPYA.IS', 'VAKIF.IS',
        'VESBE.IS', 'VKFYO.IS', 'VKING.IS', 'YATAS.IS', 'YGYO.IS', 'YKSLN.IS',
        'ZOREN.IS', 'ZPHLB.IS'
    ]

@st.cache_data(ttl=300)
def fetch_stock_data(symbol, period='6mo'):
    """Yahoo Finance'den hisse verisi çeker (5 dakika cache)"""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval='1d')
        if df.empty or len(df) < 30:
            return None
        required = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in df.columns for col in required):
            return None
        return df
    except:
        return None

# =====================================================
# 📊 TEKNİK ANALİZ FONKSİYONLARI
# =====================================================
def calculate_indicators(df):
    """Teknik indikatörleri hesaplar"""
    df = df.copy()
    
    # Hareketli Ortalamalar
    df['SMA20'] = ta.trend.sma_indicator(df['Close'], window=20)
    df['SMA50'] = ta.trend.sma_indicator(df['Close'], window=50)
    df['SMA200'] = ta.trend.sma_indicator(df['Close'], window=200)
    df['EMA20'] = ta.trend.ema_indicator(df['Close'], window=20)
    
    # RSI, MACD, Bollinger
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    df['MACD'] = ta.trend.macd_diff(df['Close'])
    df['MACD_signal'] = ta.trend.macd_signal(df['Close'])
    df['BB_upper'] = ta.volatility.bollinger_hband(df['Close'])
    df['BB_lower'] = ta.volatility.bollinger_lband(df['Close'])
    
    # ATR, OBV, ADX
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
    df['OBV'] = ta.volume.on_balance_volume(df['Close'], df['Volume'])
    df['ADX'] = ta.trend.adx(df['High'], df['Low'], df['Close'], window=14)
    df['Volume_SMA20'] = ta.trend.sma_indicator(df['Volume'], window=20)
    
    return df

def find_support_resistance(df, window=20):
    """Destek ve direnç seviyelerini bulur"""
    highs = df['High'].rolling(window=window).max()
    lows = df['Low'].rolling(window=window).min()
    
    resistance = highs.iloc[-window:].max()
    support = lows.iloc[-window:].min()
    
    # Fibonacci
    high_60 = df['High'].rolling(window=60).max().iloc[-1]
    low_60 = df['Low'].rolling(window=60).min().iloc[-1]
    diff = high_60 - low_60
    
    fib = {
        '0%': low_60,
        '23.6%': low_60 + diff * 0.236,
        '38.2%': low_60 + diff * 0.382,
        '50%': low_60 + diff * 0.5,
        '61.8%': low_60 + diff * 0.618,
        '100%': high_60
    }
    
    return {
        'resistance': resistance,
        'support': support,
        'pivot': (resistance + support) / 2,
        'fibonacci': fib
    }

def detect_patterns(df):
    """Formasyon tespiti"""
    if len(df) < 40:
        return {}
    
    patterns = {}
    son = df.tail(40)
    
    # İkili Dip
    dips = signal.find_peaks(-son['Low'].values, distance=10)[0]
    if len(dips) >= 2:
        d1, d2 = son['Low'].iloc[dips[-2]], son['Low'].iloc[dips[-1]]
        if abs(d1 - d2) / d1 < 0.05:
            patterns['ikili_dip'] = True
    
    # İkili Tepe
    peaks = signal.find_peaks(son['High'].values, distance=10)[0]
    if len(peaks) >= 2:
        t1, t2 = son['High'].iloc[peaks[-2]], son['High'].iloc[peaks[-1]]
        if abs(t1 - t2) / t1 < 0.05:
            patterns['ikili_tepe'] = True
    
    # Çanak-Kulp (basit)
    if len(df) >= 60:
        son60 = df.tail(60)
        ort = son60['Close'].mean()
        std = son60['Close'].std()
        trend_up = son60['Close'].iloc[-1] > son60['Close'].iloc[-20]
        if abs(ort - son60['Close'].iloc[-1]) < std * 1.5 and trend_up:
            patterns['canak_kulp'] = True
    
    return patterns

def calculate_score(df):
    """Teknik analiz puanı (0-100)"""
    score = 50
    rsi = df['RSI'].iloc[-1]
    
    # RSI scoring
    if rsi < 30: score += 15
    elif rsi < 40: score += 5
    elif rsi > 70: score -= 15
    elif rsi > 60: score -= 5
    
    # MA scoring
    close = df['Close'].iloc[-1]
    if close > df['SMA20'].iloc[-1]: score += 10
    else: score -= 10
    if close > df['SMA50'].iloc[-1]: score += 10
    else: score -= 10
    if df['SMA20'].iloc[-1] > df['SMA50'].iloc[-1]: score += 10
    else: score -= 10
    
    # MACD
    if df['MACD'].iloc[-1] > df['MACD_signal'].iloc[-1]: score += 10
    else: score -= 10
    
    # Volume
    if df['Volume'].iloc[-1] > df['Volume_SMA20'].iloc[-1]: score += 5
    
    # ADX
    if df['ADX'].iloc[-1] > 25: score += 5
    
    return max(0, min(100, score))

def analyze_stock(symbol):
    """Tek hisse için tam analiz"""
    df = fetch_stock_data(symbol)
    if df is None:
        return None
    
    df = calculate_indicators(df)
    levels = find_support_resistance(df)
    patterns = detect_patterns(df)
    score = calculate_score(df)
    
    # Accumulation analysis
    son30 = df.tail(30)
    vol_ratio = son30['Volume'].iloc[-1] / son30['Volume'].mean()
    price_range = (son30['High'].max() - son30['Low'].min()) / son30['Low'].min()
    obv_trend = son30['OBV'].iloc[-1] > son30['OBV'].iloc[0]
    acc_score = sum([vol_ratio > 1.2, price_range < 0.15, obv_trend])
    
    # Recommendation
    if score >= 70: rec = 'GÜÇLÜ AL'
    elif score >= 55: rec = 'AL'
    elif score >= 45: rec = 'İZLE'
    else: rec = 'BEKLE'
    
    return {
        'symbol': symbol.replace('.IS', ''),
        'price': df['Close'].iloc[-1],
        'change': ((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100,
        'score': score,
        'rsi': df['RSI'].iloc[-1],
        'macd': df['MACD'].iloc[-1],
        'adx': df['ADX'].iloc[-1],
        'atr': df['ATR'].iloc[-1],
        'levels': levels,
        'patterns': patterns,
        'accumulation': {'score': acc_score, 'vol_ratio': vol_ratio, 'obv_up': obv_trend},
        'recommendation': rec,
        'df': df
    }

# =====================================================
# 📈 PLOTLY GRAFİK FONKSİYONLARI
# =====================================================
def create_candlestick_chart(df, symbol, levels):
    """Interaktif mum grafik oluşturur"""
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, row_heights=[0.6, 0.2, 0.2],
                        subplot_titles=[f'{symbol} - Fiyat', 'RSI', 'Hacim'])
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='Fiyat', increasing_line_color='#22c55e', decreasing_line_color='#ef4444'
    ), row=1, col=1)
    
    # Moving Averages
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA20'], name='SMA20', line=dict(color='#f59e0b', width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], name='SMA50', line=dict(color='#3b82f6', width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA200'], name='SMA200', line=dict(color='#8b5cf6', width=1.5)), row=1, col=1)
    
    # Bollinger Bands
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_upper'], name='BB Upper', line=dict(color='gray', width=1, dash='dot'), showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_lower'], name='BB Lower', line=dict(color='gray', width=1, dash='dot'), fill='tonexty', fillcolor='rgba(128,128,128,0.1)'), row=1, col=1)
    
    # Support/Resistance
    fig.add_hline(y=levels['resistance'], line_dash="dash", line_color="red", annotation_text=f"Direnç: {levels['resistance']:.2f}", row=1, col=1)
    fig.add_hline(y=levels['support'], line_dash="dash", line_color="green", annotation_text=f"Destek: {levels['support']:.2f}", row=1, col=1)
    
    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI', line=dict(color='#9333ea', width=2)), row=2, col=1)
    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(239,68,68,0.1)", line_width=0, row=2, col=1)
    fig.add_hrect(y0=0, y1=30, fillcolor="rgba(34,197,94,0.1)", line_width=0, row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
    
    # Volume
    colors = ['#22c55e' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#ef4444' for i in range(len(df))]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Hacim', marker_color=colors, opacity=0.7), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Volume_SMA20'], name='Hacim SMA20', line=dict(color='#f59e0b', width=1.5)), row=3, col=1)
    
    # Layout
    fig.update_layout(
        height=700, hovermode='x unified',
        xaxis_rangeslider_visible=False,
        template='plotly_white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    
    fig.update_xaxes(title='Tarih', row=3, col=1)
    fig.update_yaxes(title='Fiyat (TL)', row=1, col=1)
    fig.update_yaxes(title='RSI', range=[0, 100], row=2, col=1)
    fig.update_yaxes(title='Hacim', row=3, col=1)
    
    return fig

def create_score_gauge(score):
    """Teknik puan için gauge chart"""
    color = '#22c55e' if score >= 70 else '#f59e0b' if score >= 55 else '#ef4444'
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "TEKNİK PUAN", 'font': {'size': 16}},
        delta={'reference': 50, 'increasing': {'color': '#22c55e'}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 45], 'color': 'rgba(239,68,68,0.1)'},
                {'range': [45, 70], 'color': 'rgba(245,158,11,0.1)'},
                {'range': [70, 100], 'color': 'rgba(34,197,94,0.1)'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 70
            }
        }
    ))
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
    return fig

# =====================================================
# 🔄 PARALEL TARAMA FONKSİYONU
# =====================================================
def scan_stocks(symbols, criteria, progress_callback=None):
    """Tüm hisseleri paralel tarar"""
    results = []
    total = len(symbols)
    
    def analyze_one(symbol):
        try:
            result = analyze_stock(symbol)
            if result is None:
                return None
            
            # Kriter kontrolü
            if result['score'] < criteria['min_score']:
                return None
            if result['rsi'] > criteria['max_rsi']:
                return None
            if result['accumulation']['vol_ratio'] < criteria['min_volume']:
                return None
            
            return result
        except:
            return None
    
    with ThreadPoolExecutor(max_workers=15) as executor:
        future_to_symbol = {executor.submit(analyze_one, sym): sym for sym in symbols}
        
        for i, future in enumerate(as_completed(future_to_symbol), 1):
            result = future.result()
            if result:
                results.append(result)
            if progress_callback and i % 50 == 0:
                progress_callback(i, total)
    
    return sorted(results, key=lambda x: x['score'], reverse=True)

# =====================================================
# 🎨 SIDEBAR - FİLTRELER VE AYARLAR
# =====================================================
def render_sidebar():
    """Sidebar bileşenlerini render eder"""
    with st.sidebar:
        st.header("⚙️ Ayarlar")
        
        # Tarama Kriterleri
        st.subheader("🔍 Tarama Filtreleri")
        min_score = st.slider("Minimum Teknik Puan", 0, 100, 55)
        max_rsi = st.slider("Maksimum RSI", 30, 100, 75)
        min_volume = st.slider("Min Hacim Artışı (x)", 0.5, 3.0, 1.0, 0.1)
        
        # Periyot Seçimi
        period = st.selectbox("Veri Periyodu", ['1mo', '3mo', '6mo', '1y', '2y'], index=2)
        
        # Hisse Seçici
        st.subheader("📋 Hisse Seçimi")
        all_symbols = get_bist_hisseleri()
        search = st.text_input("Hisse Ara", placeholder="örn: CGCAM")
        
        if search:
            filtered = [s for s in all_symbols if search.upper() in s]
            selected = st.multiselect("Seçili Hisseler", filtered, default=filtered[:10] if filtered else [])
        else:
            selected = st.multiselect("Seçili Hisseler", all_symbols, default=all_symbols[:50])
        
        # Aksiyon Butonları
        st.subheader("🚀 İşlemler")
        scan_btn = st.button("🔍 Taramayı Başlat", type="primary", use_container_width=True)
        
        if st.button("🔄 Verileri Yenile"):
            st.cache_data.clear()
            st.rerun()
        
        # Yardım
        with st.expander("ℹ️ Yardım"):
            st.markdown("""
            **Teknik Puan Yorumu:**
            - 🟢 70-100: GÜÇLÜ AL
            - 🟡 55-69: AL
            - 🟠 45-54: İZLE
            - 🔴 0-44: BEKLE
            
            **İpuçları:**
            - RSI < 30: Aşırı satım (alım fırsatı)
            - RSI > 70: Aşırı alım (dikkat)
            - MACD > Signal: Yükseliş momentumu
            """)
        
        return {
            'min_score': min_score,
            'max_rsi': max_rsi,
            'min_volume': min_volume,
            'period': period,
            'symbols': selected if selected else all_symbols[:50],
            'scan': scan_btn
        }

# =====================================================
# 📊 ANA DASHBOARD BİLEŞENLERİ
# =====================================================
def render_header():
    """Üst başlık ve özet kartları"""
    st.markdown('<div class="main-header">📊 BIST TEKNİK ANALİZ DASHBOARD</div>', unsafe_allow_html=True)
    
    # Özet Metrikler (placeholder - tarama sonrası güncellenir)
    cols = st.columns(4)
    with cols[0]:
        st.metric("📈 Toplam Hisse", "-", delta=None)
    with cols[1]:
        st.metric("✅ Uygun Hisse", "-", delta=None)
    with cols[2]:
        st.metric("🎯 Ort. Puan", "-", delta=None)
    with cols[3]:
        st.metric("⏱️ Süre", "-", delta=None)

def render_results_table(results):
    """Sonuçları interaktif tablo olarak gösterir"""
    if not results:
        st.info("🔍 Henüz tarama yapılmadı. Ayarlardan filtreleri belirleyip 'Taramayı Başlat' butonuna tıklayın.")
        return
    
    # DataFrame hazırla
    data = []
    for r in results:
        patterns = ', '.join([k.replace('_', ' ').title() for k, v in r['patterns'].items() if v]) or '-'
        data.append({
            'Hisse': r['symbol'],
            'Fiyat': f"{r['price']:.2f}",
            'Değişim %': f"{r['change']:+.2f}",
            'Puan': r['score'],
            'RSI': f"{r['rsi']:.1f}",
            'ADX': f"{r['adx']:.1f}",
            'Formasyon': patterns,
            'Aküm': f"{r['accumulation']['score']}/3",
            'Öneri': r['recommendation']
        })
    
    df = pd.DataFrame(data)
    
    # Renklendirme fonksiyonları
    def color_score(val):
        color = '#22c55e' if val >= 70 else '#f59e0b' if val >= 55 else '#ef4444'
        return f'color: {color}; font-weight: bold'
    
    def color_rec(val):
        if 'AL' in val:
            return 'background-color: #dcfce7; color: #166534; font-weight: bold'
        elif 'İZLE' in val:
            return 'background-color: #fef3c7; color: #92400e; font-weight: bold'
        else:
            return 'background-color: #fee2e2; color: #991b1b; font-weight: bold'
    
    # Tabloyu göster
    st.subheader(f"🏆 Sonuçlar ({len(results)} hisse)")
    
    styled = df.style.map(color_score, subset=['Puan']).map(color_rec, subset=['Öneri'])
    st.dataframe(styled, use_container_width=True, height=400)
    
    # CSV İndirme
    csv = df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button("📥 CSV Olarak İndir", csv, file_name=f"bist_tarama_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
    
    return df

def render_detail_view(symbol, results_df):
    """Seçili hisse için detaylı görünüm"""
    if not symbol or symbol not in results_df['Hisse'].values:
        return
    
    # Hisse verisini al
    result = analyze_stock(f"{symbol}.IS")
    if result is None:
        st.error(f"❌ {symbol} için veri alınamadı!")
        return
    
    st.divider()
    st.subheader(f"🔍 {symbol} - Detaylı Analiz")
    
    # Üst Bilgi Kartları
    cols = st.columns(5)
    with cols[0]:
        st.metric("💰 Fiyat", f"{result['price']:.2f} TL", f"{result['change']:+.2f}%")
    with cols[1]:
        st.metric("⭐ Teknik Puan", result['score'])
    with cols[2]:
        st.metric("📊 RSI", f"{result['rsi']:.1f}")
    with cols[3]:
        st.metric("📈 ADX", f"{result['adx']:.1f}")
    with cols[4]:
        st.metric("🎯 Öneri", result['recommendation'])
    
    # Gauge Chart
    col1, col2 = st.columns([1, 2])
    with col1:
        st.plotly_chart(create_score_gauge(result['score']), use_container_width=True)
    
    with col2:
        st.markdown("### 📐 Kritik Seviyeler")
        levels = result['levels']
        st.markdown(f"""
        | Seviye | Fiyat (TL) |
        |--------|-----------|
        | 🔴 Direnç | **{levels['resistance']:.2f}** |
        | 🟡 Pivot | {levels['pivot']:.2f} |
        | 🟢 Destek | **{levels['support']:.2f}** |
        """)
        
        st.markdown("### 📊 Fibonacci Seviyeleri")
        fib_data = pd.DataFrame([
            {'Seviye': k, 'Fiyat': f"{v:.2f} TL"} for k, v in levels['fibonacci'].items()
        ])
        st.dataframe(fib_data, hide_index=True, use_container_width=True)
    
    # Formasyonlar ve Akümülasyon
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📈 Tespit Edilen Formasyonlar")
        patterns = result['patterns']
        if patterns:
            for p, detected in patterns.items():
                if detected:
                    st.success(f"✅ {p.replace('_', ' ').title()}")
        else:
            st.info("Belirgin formasyon tespit edilmedi")
    
    with col2:
        st.markdown("### 📦 Akümülasyon Analizi")
        acc = result['accumulation']
        st.markdown(f"""
        - **Skor:** {acc['score']}/3
        - **Hacim Artışı:** %{(acc['vol_ratio']-1)*100:.1f}
        - **OBV Trend:** {'🟢 Yükseliyor' if acc['obv_up'] else '🔴 Düşüyor'}
        """)
    
    # İhtimaller Tablosu
    st.markdown("### 📋 Senaryo Analizi")
    atr = result['atr']
    supp = levels['support']
    res = levels['resistance']
    
    scenarios = pd.DataFrame([
        {'Senaryo': '🐂 Güçlü Yükseliş', 'Tetikleyici': f'{res:.2f} TL kırılımı', 'Hedef': f'{res + atr*2:.2f} TL', 'Stop': f'{res*0.97:.2f} TL', 'Olasılık': '35%'},
        {'Senaryo': '🐂 Orta Yükseliş', 'Tetikleyici': 'Mevcut seviyede kalıcılık', 'Hedef': f'{res:.2f} TL', 'Stop': f'{supp*0.98:.2f} TL', 'Olasılık': '40%'},
        {'Senaryo': '🐻 Düzeltme', 'Tetikleyici': f'{supp:.2f} TL altı kapanış', 'Hedef': f"{levels['fibonacci']['0%']:.2f} TL", 'Stop': f'{supp*1.03:.2f} TL', 'Olasılık': '15%'},
        {'Senaryo': '🐻 Sert Düşüş', 'Tetikleyici': 'Negatif haber akışı', 'Hedef': f"{levels['fibonacci']['0%']*0.95:.2f} TL", 'Stop': 'N/A', 'Olasılık': '10%'}
    ])
    st.dataframe(scenarios, hide_index=True, use_container_width=True)
    
    # Interaktif Grafik
    st.markdown("### 📊 Teknik Analiz Grafiği")
    fig = create_candlestick_chart(result['df'], symbol, levels)
    st.plotly_chart(fig, use_container_width=True)

# =====================================================
# 🚀 ANA UYGULAMA
# =====================================================
def main():
    # Header
    render_header()
    
    # Sidebar
    settings = render_sidebar()
    
    # Session state initialization
    if 'results' not in st.session_state:
        st.session_state.results = None
    if 'scan_time' not in st.session_state:
        st.session_state.scan_time = None
    
    # Tarama işlemi
    if settings['scan'] or st.session_state.results is None:
        with st.spinner(f"🔍 {len(settings['symbols'])} hisse taranıyor..."):
            start_time = time.time()
            progress_bar = st.progress(0)
            
            def update_progress(done, total):
                progress_bar.progress(min(done / total, 1.0))
            
            criteria = {
                'min_score': settings['min_score'],
                'max_rsi': settings['max_rsi'],
                'min_volume': settings['min_volume']
            }
            
            results = scan_stocks(settings['symbols'], criteria, update_progress)
            elapsed = time.time() - start_time
            
            st.session_state.results = results
            st.session_state.scan_time = elapsed
            progress_bar.empty()
            
            # Özet metrikleri güncelle
            st.rerun()
    
    # Sonuçları göster
    if st.session_state.results is not None:
        results = st.session_state.results
        elapsed = st.session_state.scan_time
        
        # Özet kartlarını güncelle
        cols = st.columns(4)
        with cols[0]:
            st.metric("📈 Toplam Hisse", len(settings['symbols']))
        with cols[1]:
            st.metric("✅ Uygun Hisse", len(results))
        with cols[2]:
            avg_score = np.mean([r['score'] for r in results]) if results else 0
            st.metric("🎯 Ort. Puan", f"{avg_score:.1f}")
        with cols[3]:
            st.metric("⏱️ Süre", f"{elapsed:.1f} sn")
        
        # Sonuç tablosu
        df = render_results_table(results)
        
        # Detaylı görünüm için hisse seçici
        if df is not None and not df.empty:
            st.divider()
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_symbol = st.selectbox("🔍 Detaylı İncelemek İçin Hisse Seçin", df['Hisse'].tolist())
            with col2:
                if st.button("📊 Grafiği Göster", use_container_width=True):
                    render_detail_view(selected_symbol, df)
            
            # Otomatik detay göster
            if selected_symbol:
                render_detail_view(selected_symbol, df)
    
    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: gray; font-size: 0.9rem; padding: 1rem;">
        ⚠️ Bu analizler yapay zeka tarafından oluşturulmuştur. 
        Yatırım tavsiyesi DEĞİLDİR. Kararlarınızı kendi araştırmanız ve SPK lisanslı danışmanlarla veriniz.<br>
        Veri Kaynakları: İş Yatırım, Yahoo Finance | Güncelleme: 15-60 dk gecikmeli
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()