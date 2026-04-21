# =====================================================
# 📊 BIST TEKNİK ANALİZ DASHBOARD v1.0.0
# Streamlit + Plotly + Yahoo Finance + bistpy
# =====================================================
# Kurulum: pip install streamlit pandas numpy plotly yfinance ta scipy bistpy lxml html5lib
# Çalıştırma: streamlit run app.py
# =====================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import ta
from scipy import signal
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings

warnings.filterwarnings('ignore')
st.set_page_config(page_title="BIST Teknik Analiz", page_icon="📊", layout="wide")

__version__ = "1.0.0"

# =====================================================
# 🔄 VERİ KATMANI (CACHE + API)
# =====================================================
@st.cache_data(ttl=3600)
def get_bist_symbols():
    """bistpy ile tüm aktif BIST hisselerini çeker"""
    try:
        from bistpy import Bistpy
        bp = Bistpy()
        df = bp.get_stock_list()
        col = next((c for c in df.columns if c.lower() in ['kod', 'symbol', 'sembol']), df.columns[0])
        symbols = df[col].dropna().astype(str).str.strip().unique()
        return [f"{s}.IS" for s in symbols if len(s) >= 2 and s.replace('.', '').isalnum()]
    except ImportError:
        st.error("❌ `bistpy` kurulu değil. `pip install bistpy` çalıştırın.")
        return []
    except Exception as e:
        st.error(f"❌ Sembol çekme hatası: {e}")
        return []

@st.cache_data(ttl=300)
def fetch_stock_data(symbol: str, period: str = '6mo'):
    """Yahoo Finance'den OHLCV verisi çeker"""
    try:
        df = yf.Ticker(symbol).history(period=period, interval='1d')
        if df.empty or len(df) < 30:
            return None
        required = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(c in df.columns for c in required):
            return None
        return df
    except Exception:
        return None

# =====================================================
# 🧮 TEKNİK ANALİZ MOTORU
# =====================================================
def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['SMA20'] = ta.trend.sma_indicator(df['Close'], window=20)
    df['SMA50'] = ta.trend.sma_indicator(df['Close'], window=50)
    df['SMA200'] = ta.trend.sma_indicator(df['Close'], window=200)
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    df['MACD'] = ta.trend.macd_diff(df['Close'])
    df['MACD_signal'] = ta.trend.macd_signal(df['Close'])
    df['BB_upper'] = ta.volatility.bollinger_hband(df['Close'])
    df['BB_lower'] = ta.volatility.bollinger_lband(df['Close'])
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
    df['OBV'] = ta.volume.on_balance_volume(df['Close'], df['Volume'])
    df['ADX'] = ta.trend.adx(df['High'], df['Low'], df['Close'], window=14)
    df['Volume_SMA20'] = ta.trend.sma_indicator(df['Volume'], window=20)
    return df

def find_levels(df: pd.DataFrame, window: int = 20) -> dict:
    res = df['High'].rolling(window).max().iloc[-window:].max()
    sup = df['Low'].rolling(window).min().iloc[-window:].min()
    h60, l60 = df['High'].rolling(60).max().iloc[-1], df['Low'].rolling(60).min().iloc[-1]
    diff = h60 - l60
    fib = {k: l60 + diff * v for k, v in [('0%', 0), ('23.6%', 0.236), ('38.2%', 0.382), 
                                           ('50%', 0.5), ('61.8%', 0.618), ('100%', 1)]}
    return {'resistance': res, 'support': sup, 'pivot': (res + sup) / 2, 'fibonacci': fib}

def detect_patterns(df: pd.DataFrame) -> dict:
    if len(df) < 40:
        return {}
    patterns = {}
    s = df.tail(40)
    
    # İkili Dip
    dips = signal.find_peaks(-s['Low'].values, distance=10)[0]
    if len(dips) >= 2 and abs(s['Low'].iloc[dips[-2]] - s['Low'].iloc[dips[-1]]) / s['Low'].iloc[dips[-2]] < 0.05:
        patterns['İkili Dip'] = True
        
    # İkili Tepe
    peaks = signal.find_peaks(s['High'].values, distance=10)[0]
    if len(peaks) >= 2 and abs(s['High'].iloc[peaks[-2]] - s['High'].iloc[peaks[-1]]) / s['High'].iloc[peaks[-2]] < 0.05:
        patterns['İkili Tepe'] = True
        
    # Çanak-Kulp (Basit)
    if len(df) >= 60:
        s60 = df.tail(60)
        trend_up = s60['Close'].iloc[-1] > s60['Close'].iloc[-20]
        mean_close = s60['Close'].mean()
        std_close = s60['Close'].std()
        if trend_up and abs(mean_close - s60['Close'].iloc[-1]) < std_close * 1.5:
            patterns['Çanak-Kulp'] = True
            
    return patterns

def calculate_score(df: pd.DataFrame) -> int:
    score = 50
    rsi = df['RSI'].iloc[-1]
    if rsi < 30: score += 15
    elif rsi < 40: score += 5
    elif rsi > 70: score -= 15
    elif rsi > 60: score -= 5
    
    c = df['Close'].iloc[-1]
    if c > df['SMA20'].iloc[-1]: score += 10
    else: score -= 10
    if c > df['SMA50'].iloc[-1]: score += 10
    else: score -= 10
    if df['SMA20'].iloc[-1] > df['SMA50'].iloc[-1]: score += 10
    else: score -= 10
    
    if df['MACD'].iloc[-1] > df['MACD_signal'].iloc[-1]: score += 10
    else: score -= 10
    if df['Volume'].iloc[-1] > df['Volume_SMA20'].iloc[-1]: score += 5
    if df['ADX'].iloc[-1] > 25: score += 5
    
    return max(0, min(100, score))

def analyze_stock(symbol: str) -> dict | None:
    df = fetch_stock_data(symbol)
    if df is None:
        return None
    
    df = calculate_indicators(df)
    levels = find_levels(df)
    patterns = detect_patterns(df)
    score = calculate_score(df)
    
    s30 = df.tail(30)
    vol_ratio = s30['Volume'].iloc[-1] / s30['Volume'].mean()
    price_range = (s30['High'].max() - s30['Low'].min()) / s30['Low'].min()
    obv_up = s30['OBV'].iloc[-1] > s30['OBV'].iloc[0]
    acc_score = sum([vol_ratio > 1.2, price_range < 0.15, obv_up])
    
    rec = 'GÜÇLÜ AL' if score >= 70 else 'AL' if score >= 55 else 'İZLE' if score >= 45 else 'BEKLE'
    
    return {
        'symbol': symbol.replace('.IS', ''),
        'price': df['Close'].iloc[-1],
        'change': ((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100,
        'score': score,
        'rsi': df['RSI'].iloc[-1],
        'adx': df['ADX'].iloc[-1],
        'atr': df['ATR'].iloc[-1],
        'levels': levels,
        'patterns': patterns,
        'acc_score': acc_score,
        'rec': rec,
        'df': df
    }

# =====================================================
# 📈 GÖRSELLEŞTİRME
# =====================================================
def create_chart(df: pd.DataFrame, symbol: str, levels: dict) -> go.Figure:
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.6, 0.2, 0.2])
    
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Fiyat'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA20'], name='SMA20', line=dict(color='#f59e0b', width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], name='SMA50', line=dict(color='#3b82f6', width=1.5)), row=1, col=1)
    fig.add_hline(y=levels['resistance'], line_dash="dash", line_color="#ef4444", row=1, col=1)
    fig.add_hline(y=levels['support'], line_dash="dash", line_color="#22c55e", row=1, col=1)
    
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI', line=dict(color='#9333ea', width=2)), row=2, col=1)
    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(239,68,68,0.1)", line_width=0, row=2, col=1)
    fig.add_hrect(y0=0, y1=30, fillcolor="rgba(34,197,94,0.1)", line_width=0, row=2, col=1)
    
    colors = ['#22c55e' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#ef4444' for i in range(len(df))]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Hacim', marker_color=colors, opacity=0.7), row=3, col=1)
    
    fig.update_layout(
        height=650, hovermode='x unified', xaxis_rangeslider_visible=False,
        template='plotly_white', showlegend=False, margin=dict(l=40, r=40, t=30, b=40)
    )
    return fig

# =====================================================
# 🔄 PARALEL TARAMA
# =====================================================
def scan_stocks(symbols: list, criteria: dict, progress_cb) -> list:
    results, failed = [], 0
    total = len(symbols)
    
    def worker(sym):
        try:
            res = analyze_stock(sym)
            if not res: return None
            if res['score'] < criteria['min_score']: return None
            if res['rsi'] > criteria['max_rsi']: return None
            return res
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(worker, s): s for s in symbols}
        for i, f in enumerate(as_completed(futures), 1):
            try:
                r = f.result(timeout=15)
                if r: results.append(r)
                else: failed += 1
            except Exception:
                failed += 1
            if i % 10 == 0 or i == total:
                progress_cb(i, total, failed, len(results))
                
    return sorted(results, key=lambda x: x['score'], reverse=True)

# =====================================================
# 🎨 ARAYÜZ BİLEŞENLERİ
# =====================================================
def render_sidebar():
    with st.sidebar:
        st.header(f"⚙️ Ayarlar v{__version__}")
        min_score = st.slider("Minimum Teknik Puan", 0, 100, 55)
        max_rsi = st.slider("Maksimum RSI", 30, 100, 75)
        
        st.divider()
        if st.button("🔄 Verileri & Cache'i Yenile", use_container_width=True):
            st.cache_data.clear()
            st.session_state.pop('results', None)
            st.session_state.pop('scan_done', None)
            st.rerun()
            
        with st.spinner("📡 Semboller yükleniyor..."):
            symbols = get_bist_symbols()
            
        if not symbols:
            st.error("⚠️ Sembol listesi boş. `bistpy` kurulumunu kontrol edin.")
            return {'symbols': [], 'min_score': min_score, 'max_rsi': max_rsi, 'scan': False}
            
        st.success(f"✅ {len(symbols)} hisse hazır")
        
        search = st.text_input("Hisse Ara", placeholder="örn: CGCAM")
        filtered = [s for s in symbols if search.upper() in s.replace('.IS', '')] if search else symbols
        default = st.session_state.get('sel_symbols', symbols)
        selected = st.multiselect("Seçili Hisseler", symbols, default=default)
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Tümünü Seç", use_container_width=True):
                st.session_state.sel_symbols = symbols
                st.rerun()
        with c2:
            if st.button("🗑️ Temizle", use_container_width=True):
                st.session_state.sel_symbols = []
                st.rerun()
                
        st.session_state.sel_symbols = selected
        scan_btn = st.button("🚀 TARAMAYI BAŞLAT", type="primary", use_container_width=True)
        
        return {'symbols': selected, 'min_score': min_score, 'max_rsi': max_rsi, 'scan': scan_btn}

def render_results(results: list):
    if not results:
        st.info("📊 Henüz tarama yapılmadı. Sol menüden ayarları seçip başlatın.")
        return pd.DataFrame()
        
    data = []
    for r in results:
        pat = ', '.join(r['patterns'].keys()) if r['patterns'] else '-'
        data.append({
            'Hisse': r['symbol'], 'Fiyat': f"{r['price']:.2f}", 'Değ. %': f"{r['change']:+.2f}",
            'Puan': r['score'], 'RSI': f"{r['rsi']:.1f}", 'ADX': f"{r['adx']:.1f}",
            'Formasyon': pat, 'Aküm': f"{r['acc_score']}/3", 'Öneri': r['rec']
        })
        
    df = pd.DataFrame(data)
    search = st.text_input("🔍 Sonuçlarda Ara", placeholder="Kod, öneri veya formasyon yazın...")
    if search:
        df = df[df.apply(lambda row: row.astype(str).str.contains(search.upper(), case=False).any(), axis=1)]
        
    def color_rec(val):
        if 'AL' in val: return 'background-color: #dcfce7; color: #166534; font-weight: bold'
        elif 'İZLE' in val: return 'background-color: #fef3c7; color: #92400e; font-weight: bold'
        return 'background-color: #fee2e2; color: #991b1b; font-weight: bold'
        
    st.dataframe(df.style.map(color_rec, subset=['Öneri']), use_container_width=True, height=450)
    return df

def render_detail(selected: str, results: list):
    if not selected:
        return
    item = next((r for r in results if r['symbol'] == selected), None)
    if not item:
        return
        
    st.divider()
    st.subheader(f"🔍 {selected} Detaylı Analiz")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("💰 Fiyat", f"{item['price']:.2f} TL", f"{item['change']:+.2f}%")
    c2.metric("⭐ Puan", item['score'])
    c3.metric("📊 RSI", f"{item['rsi']:.1f}")
    c4.metric("📈 ADX", f"{item['adx']:.1f}")
    c5.metric("🎯 Öneri", item['rec'])
    
    colA, colB = st.columns(2)
    with colA:
        st.markdown(f"**📐 Seviyeler**\n🔴 Direnç: `{item['levels']['resistance']:.2f}`\n🟢 Destek: `{item['levels']['support']:.2f}`")
        st.markdown(f"**📦 Akümülasyon:** `{item['acc_score']}/3`")
    with colB:
        if item['patterns']:
            for p in item['patterns']: st.success(f"✅ {p}")
        else:
            st.info("Belirgin formasyon tespit edilmedi")
            
    st.plotly_chart(create_chart(item['df'], selected, item['levels']), use_container_width=True)

# =====================================================
# 🚀 ANA UYGULAMA
# =====================================================
def main():
    st.markdown(f'<div style="text-align:center;font-size:1.8rem;font-weight:bold;color:#1f77b4;padding:1rem;">📊 BIST TEKNİK ANALİZ DASHBOARD v{__version__}</div>', unsafe_allow_html=True)
    
    if 'results' not in st.session_state: st.session_state.results = None
    if 'scan_done' not in st.session_state: st.session_state.scan_done = False
    
    settings = render_sidebar()
    if not settings['symbols']:
        return

    if settings['scan']:
        with st.status("⏳ Tarama başlatılıyor...", expanded=True) as status:
            pb = st.progress(0)
            txt = st.empty()
            
            def cb(done, total, fail, ok):
                pb.progress(done / total)
                txt.text(f"📊 Tarandı: {done}/{total} | ✅ Uygun: {ok} | ❌ Başarısız: {fail}")
                
            criteria = {'min_score': settings['min_score'], 'max_rsi': settings['max_rsi']}
            start = time.time()
            res = scan_stocks(settings['symbols'], criteria, cb)
            elapsed = time.time() - start
            
            st.session_state.results = res
            st.session_state.scan_done = True
            status.update(label=f"✅ Tamamlandı! {len(res)} hisse bulundu. ({elapsed:.1f} sn)", state="complete", expanded=False)
            st.rerun()

    if st.session_state.scan_done and st.session_state.results is not None:
        res = st.session_state.results
        st.divider()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("📈 Taranan", len(settings['symbols']))
        c2.metric("✅ Uygun", len(res))
        c3.metric("🎯 Ort. Puan", f"{np.mean([r['score'] for r in res]):.1f}" if res else "-")
        
        df = render_results(res)
        if not df.empty:
            col1, col2 = st.columns([3, 1])
            with col1:
                sel = st.selectbox("🔍 Detaylı İncele", df['Hisse'].tolist())
            with col2:
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button("📥 CSV İndir", csv, file_name=f"bist_tarama_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
            render_detail(sel, res)
            
    st.divider()
    st.caption("⚠️ Bu analizler bilgilendirme amaçlıdır. Yatırım tavsiyesi değildir. Veriler 15-60 dk gecikmeli olabilir.")

if __name__ == "__main__":
    main()
