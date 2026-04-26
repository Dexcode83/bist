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

# Başlık
st.markdown("""
<div class="main-header">
    <h1>🚀 BIST TrendScout Pro v2.1</h1>
    <p>Gelişmiş Teknik Analiz ve Hisse Tarama Sistemi</p>
</div>
""", unsafe_allow_html=True)

# BIST hisse listesi
BIST_HISSELER = [
    "A1CAP.IS", "A1YEN.IS", "ACSEL.IS", "ADEL.IS", "ADESE.IS", "ADGYO.IS", "AEFES.IS", "AFYON.IS", "AGESA.IS", "AGHOL.IS",
    "AGROT.IS", "AGYO.IS", "AHGAZ.IS", "AHSGY.IS", "AKBNK.IS", "AKCNS.IS", "AKENR.IS", "AKFGY.IS", "AKFIS.IS", "AKFYE.IS",
    "AKGRT.IS", "AKMGY.IS", "AKSA.IS", "AKSEN.IS", "AKSGY.IS", "AKSUE.IS", "AKYHO.IS", "ALARK.IS", "ALBRK.IS", "ALCAR.IS",
    "ALCTL.IS", "ALFAS.IS", "ALGYO.IS", "ALKA.IS", "ALKIM.IS", "ALKLC.IS", "ALTINS1.IS", "ALTNY.IS", "ALVES.IS", "ANELE.IS",
    "ANGEN.IS", "ANHYT.IS", "ANSGR.IS", "ARASE.IS", "ARCLK.IS", "ARDYZ.IS", "ARENA.IS", "ARMGD.IS", "ARSAN.IS", "ARTMS.IS",
    "ARZUM.IS", "ASELS.IS", "ASGYO.IS", "ASTOR.IS", "ASUZU.IS", "ATAGY.IS", "ATAKP.IS", "ATATP.IS", "ATEKS.IS", "ATLAS.IS",
    "ATSYH.IS", "AVGYO.IS", "AVHOL.IS", "AVOD.IS", "AVPGY.IS", "AVTUR.IS", "AYCES.IS", "AYDEM.IS", "AYEN.IS", "AYES.IS",
    "AYGAZ.IS", "AZTEK.IS", "BAGFS.IS", "BAHKM.IS", "BAKAB.IS", "BALAT.IS", "BALSU.IS", "BANVT.IS", "BARMA.IS", "BASCM.IS",
    "BASGZ.IS", "BAYRK.IS", "BEGYO.IS", "BERA.IS", "BEYAZ.IS", "BFREN.IS", "BIENY.IS", "BIGCH.IS", "BIGEN.IS", "BIMAS.IS",
    "BINBN.IS", "BINHO.IS", "BIOEN.IS", "BIZIM.IS", "BJKAS.IS", "BLCYT.IS", "BMSCH.IS", "BMSTL.IS", "BNTAS.IS", "BOBET.IS",
    "BORLS.IS", "BORSK.IS", "BOSSA.IS", "BRISA.IS", "BRKO.IS", "BRKSN.IS", "BRKVY.IS", "BRLSM.IS", "BRMEN.IS", "BRSAN.IS",
    "BRYAT.IS", "BSOKE.IS", "BTCIM.IS", "BUCIM.IS", "BULGS.IS", "BURCE.IS", "BURVA.IS", "BVSAN.IS", "BYDNR.IS", "CANTE.IS",
    "CASA.IS", "CATES.IS", "CCOLA.IS", "CELHA.IS", "CEMAS.IS", "CEMTS.IS", "CEMZY.IS", "CEOEM.IS", "CGCAM.IS", "CIMSA.IS",
    "CLEBI.IS", "CMBTN.IS", "CMENT.IS", "CONSE.IS", "COSMO.IS", "CRDFA.IS", "CRFSA.IS", "CUSAN.IS", "CVKMD.IS", "CWENE.IS",
    "DAGHL.IS", "DAGI.IS", "DAPGM.IS", "DARDL.IS", "DCTTR.IS", "DENGE.IS", "DERHL.IS", "DERIM.IS", "DESA.IS", "DESPC.IS",
    "DEVA.IS", "DGATE.IS", "DGGYO.IS", "DGNMO.IS", "DIRIT.IS", "DITAS.IS", "DMRGD.IS", "DMSAS.IS", "DNISI.IS", "DOAS.IS",
    "DOBUR.IS", "DOCO.IS", "DOFER.IS", "DOGUB.IS", "DOHOL.IS", "DOKTA.IS", "DSTKF.IS", "DURDO.IS", "DURKN.IS", "DYOBY.IS",
    "DZGYO.IS", "EBEBK.IS", "ECILC.IS", "ECZYT.IS", "EDATA.IS", "EDIP.IS", "EFORC.IS", "EGEEN.IS", "EGEGY.IS", "EGEPO.IS",
    "EGGUB.IS", "EGPRO.IS", "EGSER.IS", "EKGYO.IS", "EKIZ.IS", "EKOS.IS", "EKSUN.IS", "ELITE.IS", "EMKEL.IS", "EMNIS.IS",
    "ENDAE.IS", "ENERY.IS", "ENJSA.IS", "ENKAI.IS", "ENSRI.IS", "ENTRA.IS", "EPLAS.IS", "ERBOS.IS", "ERCB.IS", "EREGL.IS",
    "ERSU.IS", "ESCAR.IS", "ESCOM.IS", "ESEN.IS", "ETILR.IS", "ETYAT.IS", "EUHOL.IS", "EUKYO.IS", "EUPWR.IS", "EUREN.IS",
    "EUYO.IS", "EYGYO.IS", "FADE.IS", "FENER.IS", "FLAP.IS", "FMIZP.IS", "FONET.IS", "FORMT.IS", "FORTE.IS", "FRIGO.IS",
    "FROTO.IS", "FZLGY.IS", "GARAN.IS", "GARFA.IS", "GEDIK.IS", "GEDZA.IS", "GENIL.IS", "GENTS.IS", "GEREL.IS", "GESAN.IS",
    "GIPTA.IS", "GLBMD.IS", "GLCVY.IS", "GLRMK.IS", "GLRYH.IS", "GLYHO.IS", "GMTAS.IS", "GOKNR.IS", "GOLTS.IS", "GOODY.IS",
    "GOZDE.IS", "GRNYO.IS", "GRSEL.IS", "GRTHO.IS", "GSDDE.IS", "GSDHO.IS", "GSRAY.IS", "GUBRF.IS", "GUNDG.IS", "GWIND.IS",
    "GZNMI.IS", "HALKB.IS", "HATEK.IS", "HATSN.IS", "HDFGS.IS", "HEDEF.IS", "HEKTS.IS", "HKTM.IS", "HLGYO.IS", "HOROZ.IS",
    "HRKET.IS", "HTTBT.IS", "HUBVC.IS", "HUNER.IS", "HURGZ.IS", "ICBCT.IS", "ICUGS.IS", "IDGYO.IS", "IEYHO.IS", "IHAAS.IS",
    "IHEVA.IS", "IHGZT.IS", "IHLAS.IS", "IHLGM.IS", "IHYAY.IS", "IMASM.IS", "INDES.IS", "INFO.IS", "INGRM.IS", "INTEK.IS",
    "INTEM.IS", "INVEO.IS", "INVES.IS", "IPEKE.IS", "ISATR.IS", "ISBIR.IS", "ISBTR.IS", "ISCTR.IS", "ISDMR.IS", "ISFIN.IS",
    "ISGSY.IS", "ISGYO.IS", "ISKPL.IS", "ISKUR.IS", "ISMEN.IS", "ISSEN.IS", "ISYAT.IS", "IZENR.IS", "IZFAS.IS", "IZINV.IS",
    "IZMDC.IS", "JANTS.IS", "KAPLM.IS", "KAREL.IS", "KARSN.IS", "KARTN.IS", "KATMR.IS", "KAYSE.IS", "KBORU.IS", "KCAER.IS",
    "KCHOL.IS", "KENT.IS", "KERVN.IS", "KERVT.IS", "KFEIN.IS", "KGYO.IS", "KIMMR.IS", "KLGYO.IS", "KLKIM.IS", "KLMSN.IS",
    "KLNMA.IS", "KLRHO.IS", "KLSER.IS", "KLSYN.IS", "KLYPV.IS", "KMPUR.IS", "KNFRT.IS", "KOCMT.IS", "KONKA.IS", "KONTR.IS",
    "KONYA.IS", "KOPOL.IS", "KORDS.IS", "KOTON.IS", "KOZAA.IS", "KOZAL.IS", "KRDMA.IS", "KRDMB.IS", "KRDMD.IS", "KRGYO.IS",
    "KRONT.IS", "KRPLS.IS", "KRSTL.IS", "KRTEK.IS", "KRVGD.IS", "KSTUR.IS", "KTLEV.IS", "KTSKR.IS", "KUTPO.IS", "KUVVA.IS",
    "KUYAS.IS", "KZBGY.IS", "KZGYO.IS", "LIDER.IS", "LIDFA.IS", "LILAK.IS", "LINK.IS", "LKMNH.IS", "LMKDC.IS", "LOGO.IS",
    "LRSHO.IS", "LUKSK.IS", "LYDHO.IS", "LYDYE.IS", "MAALT.IS", "MACKO.IS", "MAGEN.IS", "MAKIM.IS", "MAKTK.IS", "MANAS.IS",
    "MARBL.IS", "MARKA.IS", "MARTI.IS", "MAVI.IS", "MEDTR.IS", "MEGAP.IS", "MEGMT.IS", "MEKAG.IS", "MEPET.IS", "MERCN.IS",
    "MERIT.IS", "MERKO.IS", "METRO.IS", "METUR.IS", "MGROS.IS", "MHRGY.IS", "MIATK.IS", "MMCAS.IS", "MNDRS.IS", "MNDTR.IS",
    "MOBTL.IS", "MOGAN.IS", "MOPAS.IS", "MPARK.IS", "MRGYO.IS", "MRSHL.IS", "MSGYO.IS", "MTRKS.IS", "MTRYO.IS", "MZHLD.IS",
    "NATEN.IS", "NETAS.IS", "NIBAS.IS", "NTGAZ.IS", "NTHOL.IS", "NUGYO.IS", "NUHCM.IS", "OBAMS.IS", "OBASE.IS", "ODAS.IS",
    "ODINE.IS", "OFSYM.IS", "ONCSM.IS", "ONRYT.IS", "ORCAY.IS", "ORGE.IS", "ORMA.IS", "OSMEN.IS", "OSTIM.IS", "OTKAR.IS",
    "OTTO.IS", "OYAKC.IS", "OYAYO.IS", "OYLUM.IS", "OYYAT.IS", "OZATD.IS", "OZGYO.IS", "OZKGY.IS", "OZRDN.IS", "OZSUB.IS",
    "OZYSR.IS", "PAGYO.IS", "PAMEL.IS", "PAPIL.IS", "PARSN.IS", "PASEU.IS", "PATEK.IS", "PCILT.IS", "PEHOL.IS", "PEKGY.IS",
    "PENGD.IS", "PENTA.IS", "PETKM.IS", "PETUN.IS", "PGSUS.IS", "PINSU.IS", "PKART.IS", "PKENT.IS", "PLTUR.IS", "PNLSN.IS",
    "PNSUT.IS", "POLHO.IS", "POLTK.IS", "PRDGS.IS", "PRKAB.IS", "PRKME.IS", "PRZMA.IS", "PSDTC.IS", "PSGYO.IS", "QNBFK.IS",
    "QNBTR.IS", "QUAGR.IS", "RALYH.IS", "RAYSG.IS", "REEDR.IS", "RGYAS.IS", "RNPOL.IS", "RODRG.IS", "RTALB.IS", "RUBNS.IS",
    "RUZYE.IS", "RYGYO.IS", "RYSAS.IS", "SAFKR.IS", "SAHOL.IS", "SAMAT.IS", "SANEL.IS", "SANFM.IS", "SANKO.IS", "SARKY.IS",
    "SASA.IS", "SAYAS.IS", "SDTTR.IS", "SEGMN.IS", "SEGYO.IS", "SEKFK.IS", "SEKUR.IS", "SELEC.IS", "SELGD.IS", "SELVA.IS",
    "SERNT.IS", "SEYKM.IS", "SILVR.IS", "SISE.IS", "SKBNK.IS", "SKTAS.IS", "SKYLP.IS", "SKYMD.IS", "SMART.IS", "SMRTG.IS",
    "SMRVA.IS", "SNGYO.IS", "SNICA.IS", "SNKRN.IS", "SNPAM.IS", "SODSN.IS", "SOKE.IS", "SOKM.IS", "SONME.IS", "SRVGY.IS",
    "SUMAS.IS", "SUNTK.IS", "SURGY.IS", "SUWEN.IS", "TABGD.IS", "TARKM.IS", "TATEN.IS", "TATGD.IS", "TAVHL.IS", "TBORG.IS",
    "TCELL.IS", "TCKRC.IS", "TDGYO.IS", "TEKTU.IS", "TERA.IS", "TEZOL.IS", "TGSAS.IS", "THYAO.IS", "TKFEN.IS", "TKNSA.IS",
    "TLMAN.IS", "TMPOL.IS", "TMSN.IS", "TNZTP.IS", "TOASO.IS", "TRCAS.IS", "TRGYO.IS", "TRILC.IS", "TSGYO.IS", "TSKB.IS",
    "TSPOR.IS", "TTKOM.IS", "TTRAK.IS", "TUCLK.IS", "TUKAS.IS", "TUPRS.IS", "TUREX.IS", "TURGG.IS", "TURSG.IS", "UFUK.IS",
    "ULAS.IS", "ULKER.IS", "ULUFA.IS", "ULUSE.IS", "ULUUN.IS", "UMPAS.IS", "UNLU.IS", "USAK.IS", "VAKBN.IS", "VAKFN.IS",
    "VAKKO.IS", "VANGD.IS", "VBTYZ.IS", "VERTU.IS", "VERUS.IS", "VESBE.IS", "VESTL.IS", "VKFYO.IS", "VKGYO.IS", "VKING.IS",
    "VRGYO.IS", "VSNMD.IS", "YAPRK.IS", "YATAS.IS", "YAYLA.IS", "YBTAS.IS", "YEOTK.IS", "YESIL.IS", "YGGYO.IS", "YGYO.IS",
    "YIGIT.IS", "YKBNK.IS", "YKSLN.IS", "YONGA.IS", "YUNSA.IS", "YYAPI.IS", "YYLGD.IS", "ZEDUR.IS", "ZOREN.IS", "ZRGYO.IS"
]

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
            time.sleep(0.05)  # Rate limiting
        
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
    
    # Renklendirme fonksiyonu - DÜZELTİLDİ
    def color_trend(val):
        """Trend değerine göre renk döndür"""
        if 'Güçlü' in str(val):
            return 'background-color: #90EE9044'
        elif 'Yeni' in str(val):
            return 'background-color: #FFD70044'
        return 'background-color: #FFB6C144'
    
    # Stil uygulama - pandas 2.0+ uyumlu
    try:
        styled_df = df_results.style.map(color_trend, subset=['Trend'])
    except AttributeError:
        # Eski pandas versiyonları için alternatif
        def highlight_trend(row):
            if 'Güçlü' in str(row['Trend']):
                return ['background-color: #90EE9044'] * len(row)
            elif 'Yeni' in str(row['Trend']):
                return ['background-color: #FFD70044'] * len(row)
            return ['background-color: #FFB6C144'] * len(row)
        styled_df = df_results.style.apply(highlight_trend, axis=1)
    
    st.dataframe(styled_df, use_container_width=True, height=400)
    
    # İstatistikler
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Toplam Hisseler", len(df_results))
    with col2:
        guclu_sayisi = len(df_results[df_results['Trend'].str.contains('Güçlü', na=False)])
        st.metric("Güçlü Trend", guclu_sayisi)
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
    if len(df_results) > 0:
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
    else:
        st.info("Detaylı analiz için hisse bulunamadı.")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray;">
    <p>BIST TrendScout Pro v2.1 | Veri kaynağı: Yahoo Finance</p>
</div>
""", unsafe_allow_html=True)

bu kodum var  degsıtırmeden gelsımesını ıstıyorum 

# =========================================
# 🚀 BIST TrendScout PRO v3.5 FULL SİSTEM
# =========================================

!pip install git+https://github.com/rongardF/tvdatafeed pandas_ta tqdm requests

import pandas as pd
import pandas_ta as ta
from tvDatafeed import TvDatafeed, Interval
from tqdm import tqdm
import requests
import json

tv = TvDatafeed()

# =========================================
# ⚙️ AYARLAR
# =========================================
N_BARS = 100

RSI_MIN = 55
ADX_MIN = 20
VOLUME_Z_MIN = 2

# =========================================
# 📊 TÜM BIST HİSSELERİ
# =========================================
def bist_tum_hisseler():
    url = "https://scanner.tradingview.com/turkey/scan"

    payload = {
        "filter": [
            {"left": "exchange", "operation": "equal", "right": "BIST"}
        ],
        "options": {"lang": "tr"},
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": ["name"]
    }

    r = requests.post(url, json=payload)
    data = r.json()

    hisseler = [item["d"][0].replace("BIST:", "") for item in data["data"]]

    # temizle
    hisseler = [h.strip().upper() for h in hisseler if len(h) <= 5]

    return list(set(hisseler))

# =========================================
# 📈 VERİ ÇEKME
# =========================================
def get_data(symbol, interval):
    try:
        df = tv.get_hist(symbol=symbol, exchange="BIST", interval=interval, n_bars=N_BARS)
        if df is None or len(df) < 50:
            return None
        return df
    except:
        return None

# =========================================
# 📊 GÖSTERGELER
# =========================================
def add_indicators(df):
    df["RSI"] = ta.rsi(df["close"], length=14)
    df["ADX"] = ta.adx(df["high"], df["low"], df["close"])["ADX_14"]
    df["EMA50"] = ta.ema(df["close"], length=50)
    df["ROC"] = ta.roc(df["close"], length=10)

    df["CMF"] = ta.cmf(df["high"], df["low"], df["close"], df["volume"])

    df["VOL_MEAN"] = df["volume"].rolling(20).mean()
    df["VOL_STD"] = df["volume"].rolling(20).std()
    df["VOL_Z"] = (df["volume"] - df["VOL_MEAN"]) / df["VOL_STD"]

    df["HH20"] = df["high"].rolling(20).max()

    return df

# =========================================
# ⚡ HIZLI ÖN FİLTRE
# =========================================
def hizli_filtre(symbol):
    df = get_data(symbol, Interval.in_daily)
    if df is None:
        return False

    df["EMA20"] = df["close"].ewm(span=20).mean()

    return df["close"].iloc[-1] > df["EMA20"].iloc[-1]

# =========================================
# 🤖 AI YORUM
# =========================================
def ai_yorum(row):
    yorum = []

    if row["RSI"] > 60:
        yorum.append("Momentum güçlü")
    if row["ADX"] > 25:
        yorum.append("Trend kuvvetli")
    if row["CMF"] > 0:
        yorum.append("Para girişi var")
    if row["VOL_Z"] > 2:
        yorum.append("Hacim patlaması")

    return " | ".join(yorum)

# =========================================
# 🧠 ANALİZ
# =========================================
def analyze_symbol(symbol):
    df_d = get_data(symbol, Interval.in_daily)
    df_4h = get_data(symbol, Interval.in_4_hour)

    if df_d is None or df_4h is None:
        return None

    df_d = add_indicators(df_d)
    df_4h = add_indicators(df_4h)

    d = df_d.iloc[-1]
    h4 = df_4h.iloc[-1]

    # şartlar
    trend = d["close"] > d["EMA50"]
    rsi = d["RSI"] > RSI_MIN
    adx = d["ADX"] > ADX_MIN
    volume = d["VOL_Z"] > VOLUME_Z_MIN
    para = d["CMF"] > 0
    breakout = d["close"] > df_d["HH20"].iloc[-2]

    mtf = h4["RSI"] > 50 and h4["close"] > h4["EMA50"]

    if trend and rsi and adx and volume and para and breakout and mtf:
        return {
            "Hisse": symbol,
            "Fiyat": round(d["close"], 2),
            "RSI": round(d["RSI"], 2),
            "ADX": round(d["ADX"], 2),
            "Hacim Skor": round(d["VOL_Z"], 2),
            "AI Yorum": ai_yorum(d)
        }

    return None

# =========================================
# 🚀 ANA ÇALIŞMA
# =========================================
def run():
    hisseler = bist_tum_hisseler()
    print(f"Toplam hisse: {len(hisseler)}")

    results = []

    for h in tqdm(hisseler):
        # ⚡ hızlı eleme
        if not hizli_filtre(h):
            continue

        res = analyze_symbol(h)
        if res:
            results.append(res)

    # kaydet
    with open("pro_sinyaller.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n🔥 {len(results)} adet PRO sinyal bulundu\n")

    for r in results:
        print(r)

# =========================================
# ▶️ BAŞLAT
# =========================================
run()
