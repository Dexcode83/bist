# =====================================================
# 🚀 BIST SINIRSIZ TEKNİK ANALİZ DASHBOARD v3.0
# Streamlit + Plotly + Yahoo Finance
# =====================================================
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
import ssl
from urllib import request
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
import traceback

warnings.filterwarnings('ignore')
st.set_page_config(page_title="BIST Sınırsız Analiz", page_icon="📊", layout="wide")

# =====================================================
# 🎨 CSS & TEMALAR
# =====================================================
st.markdown("""
<style>
    .main-header { font-size: 2rem; font-weight: bold; color: #1f77b4; text-align: center; padding: 1rem; }
    .metric-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; color: white; text-align: center; }
    .stDataFrame { font-size: 0.85rem; }
    .bull { color: #22c55e; font-weight: bold; }
    .bear { color: #ef4444; font-weight: bold; }
    .neutral { color: #f59e0b; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# =====================================================
# 🔄 CACHE & VERİ ÇEKME
# =====================================================
@st.cache_data(ttl=3600)
def get_bist_hisseleri():
    url = "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/Temel-Degerler-Ve-Oranlar.aspx"
    try:
        context = ssl._create_unverified_context()
        html = request.urlopen(url, context=context, timeout=30).read()
        tablolar = pd.read_html(html, decimal=",", thousands=".")
        for t in tablolar:
            if "Kod" in t.columns:
                kodlar = t["Kod"].dropna().astype(str).str.strip().tolist()
                return [f"{k}.IS" for k in kodlar if len(k.strip()) >= 3 and k.strip() != 'Kod']
    except:
        pass
    return _yedek_liste()

@st.cache_data(ttl=3600)
def _yedek_liste():
    return [
        'AKBNK.IS', 'ASELS.IS', 'BIMAS.IS', 'EREGL.IS', 'FROTO.IS', 'GARAN.IS', 'HALKB.IS', 'ISCTR.IS',
        'KCHOL.IS', 'KOZAL.IS', 'KRDMD.IS', 'PETKM.IS', 'PGSUS.IS', 'SAHOL.IS', 'SISE.IS', 'TCELL.IS',
        'THYAO.IS', 'TKFEN.IS', 'TUPRS.IS', 'ULKER.IS', 'VAKBN.IS', 'YKBNK.IS', 'HEKTS.IS', 'MAVI.IS',
        'SOKM.IS', 'DOHOL.IS', 'AFYON.IS', 'AKCNS.IS', 'AKFGY.IS', 'AKGRT.IS', 'AKSEN.IS', 'ALBRK.IS',
        'ALCAR.IS', 'ALFAS.IS', 'ALGYO.IS', 'ANACM.IS', 'ANSGR.IS', 'ARCLK.IS', 'ARSAN.IS', 'ASTOR.IS',
        'AYGAZ.IS', 'BAGFS.IS', 'BASGZ.IS', 'BAYRK.IS', 'BERA.IS', 'BESKT.IS', 'BIZIM.IS', 'BOLUC.IS',
        'BOMAP.IS', 'BRISA.IS', 'BRMEN.IS', 'BRYAT.IS', 'BUCIM.IS', 'CELHA.IS', 'CEMTS.IS', 'CIMSA.IS',
        'COSMO.IS', 'CRDFA.IS', 'CRMSN.IS', 'DENGE.IS', 'DERIM.IS', 'DEVA.IS', 'DGGYO.IS', 'DITAS.IS',
        'DOAS.IS', 'DOGU.IS', 'DRHMA.IS', 'ECILC.IS', 'ECZYT.IS', 'EGGUB.IS', 'EGPRO.IS', 'EKGYO.IS',
        'EMKEL.IS', 'ERBOS.IS', 'ERCIS.IS', 'ERUHC.IS', 'ESCOM.IS', 'ESGBA.IS', 'ETILR.IS', 'EUPWR.IS',
        'FENER.IS', 'FINBN.IS', 'FLAP.IS', 'FONET.IS', 'FORMT.IS', 'GOODY.IS', 'GOZDE.IS', 'GSDDE.IS',
        'GUBRF.IS', 'HUBVC.IS', 'IHEVA.IS', 'IHGZT.IS', 'IHLGM.IS', 'IHLAS.IS', 'IKGYO.IS', 'INDES.IS',
        'INFOP.IS', 'INGRM.IS', 'ISDMR.IS', 'ISFIN.IS', 'ISGYO.IS', 'ISKUR.IS', 'ISMEN.IS', 'IZDEM.IS',
        'IZMDC.IS', 'IZTAR.IS', 'JANTS.IS', 'KAREL.IS', 'KARSN.IS', 'KATSN.IS', 'KAYA.IS', 'KCAER.IS',
        'KENT.IS', 'KERVT.IS', 'KLRHO.IS', 'KLSER.IS', 'KONTR.IS', 'KONYA.IS', 'KOZAA.IS', 'KRNVR.IS',
        'KUTPO.IS', 'KUYAS.IS', 'KZLBM.IS', 'LIDER.IS', 'LINKA.IS', 'LOGMA.IS', 'LUXKM.IS', 'MAKTK.IS',
        'MARTI.IS', 'MATAM.IS', 'MERKO.IS', 'MESYK.IS', 'METUR.IS', 'MGROS.IS', 'MIATK.IS', 'MONDI.IS',
        'MPARK.IS', 'NETAS.IS', 'NIBAS.IS', 'NUHCM.IS', 'NUHCF.IS', 'OYLUM.IS', 'OYAKC.IS', 'OYPGY.IS',
        'PENGD.IS', 'PERGS.IS', 'PLTGG.IS', 'PNSUT.IS', 'POLTK.IS', 'POLHO.IS', 'PRKAB.IS', 'PRKME.IS',
        'PSDTC.IS', 'PSTIL.IS', 'QNBFL.IS', 'REYDR.IS', 'ROTO.IS', 'SANKO.IS', 'SANFM.IS', 'SARDE.IS',
        'SELEC.IS', 'SELSA.IS', 'SKBNK.IS', 'SMRTG.IS', 'SODA.IS', 'SONME.IS', 'SSMEN.IS', 'TATGD.IS',
        'TEFAS.IS', 'TGBFB.IS', 'TKNSA.IS', 'TLMAN.IS', 'TOSTON.IS', 'TRCAS.IS', 'TRGYO.IS', 'TRKCM.IS',
        'TTRAK.IS', 'TUCLK.IS', 'TURSG.IS', 'UBAVS.IS', 'UCLAS.IS', 'ULUUN.IS', 'UNYEC.IS', 'USAK.IS',
        'UTPYA.IS', 'VAKIF.IS', 'VESBE.IS', 'VKFYO.IS', 'VKING.IS', 'YATAS.IS', 'YGYO.IS', 'YKSLN.IS',
        'ZOREN.IS', 'ZPHLB.IS'
    ]

@st.cache_data(ttl=300)
def fetch_stock_data(symbol, period='6mo'):
    try:
        df = yf.Ticker(symbol).history(period=period, interval='1d')
        if df.empty or len(df) < 30: return None
        if not all(col in df.columns for col in ['Open','High','Low','Close','Volume']): return None
        return df
    except:
        return None

# =====================================================
# 📊 TEKNİK ANALİZ MOTORU
# =====================================================
def calculate_indicators(df):
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

def find_levels(df, window=20):
    res = df['High'].rolling(window).max().iloc[-window:].max()
    sup = df['Low'].rolling(window).min().iloc[-window:].min()
    h60, l60 = df['High'].rolling(60).max().iloc[-1], df['Low'].rolling(60).min().iloc[-1]
    diff = h60 - l60
    fib = {k: l60 + diff * v for k, v in [('0%',0), ('23.6%',0.236), ('38.2%',0.382), ('50%',0.5), ('61.8%',0.618), ('100%',1)]}
    return {'resistance': res, 'support': sup, 'pivot': (res+sup)/2, 'fibonacci': fib}

def detect_patterns(df):
    if len(df) < 40: return {}
    p = {}
    s = df.tail(40)
    dips = signal.find_peaks(-s['Low'].values, distance=10)[0]
    if len(dips) >= 2 and abs(s['Low'].iloc[dips[-2]] - s['Low'].iloc[dips[-1]])/s['Low'].iloc[dips[-2]] < 0.05:
        p['İkili Dip'] = True
    peaks = signal.find_peaks(s['High'].values, distance=10)[0]
    if len(peaks) >= 2 and abs(s['High'].iloc[peaks[-2]] - s['High'].iloc[peaks[-1]])/s['High'].iloc[peaks[-2]] < 0.05:
        p['İkili Tepe'] = True
    if len(df) >= 60:
        s60 = df.tail(60)
        if s60['Close'].iloc[-1] > s60['Close'].iloc[-20] and abs(s60['Close'].mean() - s60['Close'].iloc[-1]) < s60['Close'].std()*1.5:
            p['Çanak-Kulp'] = True
    return p

def calc_score(df):
    sc = 50
    rsi = df['RSI'].iloc[-1]
    if rsi < 30: sc += 15
    elif rsi < 40: sc += 5
    elif rsi > 70: sc -= 15
    elif rsi > 60: sc -= 5
    c = df['Close'].iloc[-1]
    if c > df['SMA20'].iloc[-1]: sc += 10
    else: sc -= 10
    if c > df['SMA50'].iloc[-1]: sc += 10
    else: sc -= 10
    if df['SMA20'].iloc[-1] > df['SMA50'].iloc[-1]: sc += 10
    else: sc -= 10
    if df['MACD'].iloc[-1] > df['MACD_signal'].iloc[-1]: sc += 10
    else: sc -= 10
    if df['Volume'].iloc[-1] > df['Volume_SMA20'].iloc[-1]: sc += 5
    if df['ADX'].iloc[-1] > 25: sc += 5
    return max(0, min(100, sc))

def analyze_stock(symbol):
    df = fetch_stock_data(symbol)
    if df is None: return None
    df = calculate_indicators(df)
    levels = find_levels(df)
    patterns = detect_patterns(df)
    score = calc_score(df)
    s30 = df.tail(30)
    vr = s30['Volume'].iloc[-1] / s30['Volume'].mean()
    pr = (s30['High'].max() - s30['Low'].min()) / s30['Low'].min()
    obvt = s30['OBV'].iloc[-1] > s30['OBV'].iloc[0]
    acc = sum([vr > 1.2, pr < 0.15, obvt])
    rec = 'GÜÇLÜ AL' if score >= 70 else 'AL' if score >= 55 else 'İZLE' if score >= 45 else 'BEKLE'
    return {
        'symbol': symbol.replace('.IS', ''), 'price': df['Close'].iloc[-1],
        'change': ((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100,
        'score': score, 'rsi': df['RSI'].iloc[-1], 'adx': df['ADX'].iloc[-1], 'atr': df['ATR'].iloc[-1],
        'levels': levels, 'patterns': patterns, 'acc_score': acc, 'rec': rec, 'df': df
    }

# =====================================================
# 📈 PLOTLY GRAFİKLER
# =====================================================
def create_chart(df, sym, levels):
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.6, 0.2, 0.2])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Fiyat'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA20'], name='SMA20', line=dict(color='#f59e0b', width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], name='SMA50', line=dict(color='#3b82f6', width=1.5)), row=1, col=1)
    fig.add_hline(y=levels['resistance'], line_dash="dash", line_color="red", row=1, col=1)
    fig.add_hline(y=levels['support'], line_dash="dash", line_color="green", row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI', line=dict(color='#9333ea', width=2)), row=2, col=1)
    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(239,68,68,0.1)", line_width=0, row=2, col=1)
    fig.add_hrect(y0=0, y1=30, fillcolor="rgba(34,197,94,0.1)", line_width=0, row=2, col=1)
    colors = ['#22c55e' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#ef4444' for i in range(len(df))]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Hacim', marker_color=colors, opacity=0.7), row=3, col=1)
    fig.update_layout(height=650, hovermode='x unified', xaxis_rangeslider_visible=False, template='plotly_white', showlegend=False)
    return fig

# =====================================================
# 🔄 PARALEL TARAMA (SINIRSIZ)
# =====================================================
def scan_stocks(symbols, criteria, progress_cb):
    results, failed = [], 0
    total = len(symbols)
    
    def worker(sym):
        try:
            res = analyze_stock(sym)
            if not res: return None
            if res['score'] < criteria['min_score']: return None
            if res['rsi'] > criteria['max_rsi']: return None
            return res
        except:
            return None

    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = {ex.submit(worker, s): s for s in symbols}
        for i, f in enumerate(as_completed(futures), 1):
            try:
                r = f.result(timeout=15)
                if r: results.append(r)
                else: failed += 1
            except:
                failed += 1
            if i % 10 == 0 or i == total:
                progress_cb(i, total, failed, len(results))
                
    return sorted(results, key=lambda x: x['score'], reverse=True)

# =====================================================
# 🎨 SIDEBAR & UI
# =====================================================
def render_sidebar():
    with st.sidebar:
        st.header("⚙️ Tarama Ayarları")
        min_sc = st.slider("Min Teknik Puan", 0, 100, 55)
        max_rsi = st.slider("Max RSI", 30, 100, 75)
        period = st.selectbox("Periyot", ['1mo','3mo','6mo','1y'], index=2)
        
        st.divider()
        st.subheader("📋 Hisse Seçimi")
        all_sym = get_bist_hisseleri()
        search = st.text_input("Hisse Ara", placeholder="örn: CGCAM")
        
        filtered = [s for s in all_sym if search.upper() in s.replace('.IS','')] if search else all_sym
        default_sel = st.session_state.get('sel_syms', all_sym)
        
        selected = st.multiselect("Seçili Hisseler", all_sym, default=default_sel)
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Tümünü Seç", use_container_width=True):
                st.session_state.sel_syms = all_sym
                st.rerun()
        with c2:
            if st.button("🗑️ Temizle", use_container_width=True):
                st.session_state.sel_syms = []
                st.rerun()
                
        st.session_state.sel_syms = selected
        scan = st.button("🚀 SINIRSIZ TARAMAYI BAŞLAT", type="primary", use_container_width=True)
        
        st.divider()
        st.caption("⚠️ Yahoo Finance limitleri nedeniyle 400+ hisse ~3-5 dk sürebilir. Sabırlı olun.")
        return {'min_score': min_sc, 'max_rsi': max_rsi, 'period': period, 'symbols': selected, 'scan': scan}

# =====================================================
# 🚀 ANA UYGULAMA
# =====================================================
def main():
    st.markdown('<div class="main-header">📊 BIST SINIRSIZ TEKNİK ANALİZ DASHBOARD</div>', unsafe_allow_html=True)
    
    if 'results' not in st.session_state: st.session_state.results = None
    if 'scan_done' not in st.session_state: st.session_state.scan_done = False
    
    settings = render_sidebar()
    
    if settings['scan']:
        with st.status("🔄 Tarama başlatılıyor...", expanded=True) as status:
            pb = st.progress(0)
            txt = st.empty()
            
            def cb(done, total, fail, ok):
                pct = done/total
                pb.progress(pct)
                txt.text(f"📊 Tarandı: {done}/{total} | ✅ Uygun: {ok} | ❌ Başarısız: {fail}")
                
            crit = {'min_score': settings['min_score'], 'max_rsi': settings['max_rsi']}
            syms = settings['symbols']
            
            if not syms:
                st.warning("⚠️ Lütfen en az 1 hisse seçin!")
                return
                
            start = time.time()
            res = scan_stocks(syms, crit, cb)
            elapsed = time.time() - start
            
            st.session_state.results = res
            st.session_state.scan_done = True
            status.update(label=f"✅ Tamamlandı! {len(res)} hisse bulundu. ({elapsed:.1f} sn)", state="complete", expanded=False)
            st.rerun()
            
    if st.session_state.scan_done and st.session_state.results is not None:
        res = st.session_state.results
        st.divider()
        
        # Özet
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📈 Toplam Taranan", len(settings['symbols']))
        c2.metric("✅ Kriterlere Uyan", len(res))
        c3.metric("🎯 Ortalama Puan", f"{np.mean([r['score'] for r in res]):.1f}" if res else "-")
        c4.metric("⏱️ Süre", f"{(time.time() - (st.session_state.get('last_start', time.time()))):.1f} sn")
        
        # Filtre & Tablo
        st.subheader("🏆 Sonuçlar")
        search_res = st.text_input("🔍 Sonuçlarda Ara", placeholder="Hisse kodu veya öneri yazın...")
        
        data = []
        for r in res:
            pat = ', '.join(r['patterns'].keys()) if r['patterns'] else '-'
            data.append({'Hisse': r['symbol'], 'Fiyat': f"{r['price']:.2f}", 'Değ. %': f"{r['change']:+.2f}", 
                         'Puan': r['score'], 'RSI': f"{r['rsi']:.1f}", 'ADX': f"{r['adx']:.1f}", 
                         'Formasyon': pat, 'Aküm': f"{r['acc_score']}/3", 'Öneri': r['rec']})
            
        df = pd.DataFrame(data)
        if search_res:
            df = df[df.apply(lambda row: row.astype(str).str.contains(search_res.upper(), case=False).any(), axis=1)]
            
        def color_rec(val):
            if 'AL' in val: return 'background-color: #dcfce7; color: #166534; font-weight: bold'
            elif 'İZLE' in val: return 'background-color: #fef3c7; color: #92400e; font-weight: bold'
            return 'background-color: #fee2e2; color: #991b1b; font-weight: bold'
            
        styled = df.style.map(color_rec, subset=['Öneri'])
        st.dataframe(styled, use_container_width=True, height=450)
        
        # CSV & Detay
        colA, colB = st.columns([3, 1])
        with colA:
            sel_sym = st.selectbox("🔍 Detaylı İncele", df['Hisse'].tolist() if not df.empty else [])
        with colB:
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button("📥 CSV İndir", csv, file_name=f"bist_tarama_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv")
            
        if sel_sym:
            r = next((x for x in res if x['symbol'] == sel_sym), None)
            if r:
                st.divider()
                st.subheader(f"🔍 {sel_sym} Detaylı Analiz")
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("💰 Fiyat", f"{r['price']:.2f} TL", f"{r['change']:+.2f}%")
                c2.metric("⭐ Puan", r['score'])
                c3.metric("📊 RSI", f"{r['rsi']:.1f}")
                c4.metric("📈 ADX", f"{r['adx']:.1f}")
                c5.metric("🎯 Öneri", r['rec'])
                
                cc1, cc2 = st.columns(2)
                with cc1:
                    st.markdown(f"**📐 Seviyeler:**\n🔴 Direnç: {r['levels']['resistance']:.2f}\n🟢 Destek: {r['levels']['support']:.2f}")
                    st.markdown(f"**📦 Akümülasyon:** {r['acc_score']}/3")
                with cc2:
                    if r['patterns']:
                        for p in r['patterns']: st.success(f"✅ {p}")
                    else: st.info("Formasyon yok")
                    
                st.plotly_chart(create_chart(r['df'], sel_sym, r['levels']), use_container_width=True)
                
    # Footer
    st.divider()
    st.caption("⚠️ Yapay zeka analizi. Yatırım tavsiyesi değildir. Veriler 15-60 dk gecikmeli olabilir.")

if __name__ == "__main__":
    main()
