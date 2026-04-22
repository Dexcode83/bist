"""
BIST TrendScout Pro - Streamlit Cloud Versiyonu
"""

import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import json
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
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .main-header {
        background: rgba(255,255,255,0.95);
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
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

# Session state başlatma
if 'results' not in st.session_state:
    st.session_state.results = None

# Sidebar
with st.sidebar:
    st.header("⚙️ Parametreler")
    
    rsi_min = st.slider("Minimum RSI", 30, 80, 57)
    momentum_min = st.slider("Minimum Momentum", 90, 150, 105)
    hacim_artis_min = st.slider("Hacim Artış Oranı", 1.0, 5.0, 2.5, 0.1)
    
    st.markdown("---")
    st.info("💡 **Bilgi**: Bu uygulama demo modunda çalışmaktadır.")

# Ana içerik
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("📊 Hisse Sayısı", "100+")
with col2:
    st.metric("🎯 RSI Eşiği", rsi_min)
with col3:
    st.metric("📈 Momentum", momentum_min)

# Demo veri oluşturma
@st.cache_data
def get_demo_data():
    """Demo veri seti"""
    hisseler = [
        'THYAO', 'ASELS', 'GARAN', 'ISCTR', 'KCHOL', 
        'SISE', 'TUPRS', 'PETKM', 'EREGL', 'FROTO',
        'SAHOL', 'BIMAS', 'TTKOM', 'YKBNK', 'AKBNK'
    ]
    
    np.random.seed(42)
    data = []
    
    for hisse in hisseler:
        rsi = np.random.uniform(30, 80)
        momentum = np.random.uniform(90, 150)
        adx = np.random.uniform(10, 50)
        hacim = np.random.uniform(1, 5)
        
        # Trend belirleme
        if adx > 29 and rsi > rsi_min and momentum > momentum_min:
            trend = "Güçlü Trend 🔥"
            renk = "🟢"
        elif adx > 19 and rsi > rsi_min and momentum > momentum_min:
            trend = "Yeni Trend 📈"
            renk = "🟡"
        else:
            trend = "Zayıf ⚠️"
            renk = "🔴"
        
        data.append({
            "Hisse": hisse,
            "Fiyat": round(np.random.uniform(10, 500), 2),
            "RSI": round(rsi, 1),
            "Momentum": round(momentum, 1),
            "ADX": round(adx, 1),
            "Hacim Artış": round(hacim, 2),
            "Trend": f"{renk} {trend}"
        })
    
    return pd.DataFrame(data)

# Analiz butonu
if st.button("🔍 Analiz Başlat", type="primary", use_container_width=True):
    with st.spinner("Analiz yapılıyor..."):
        time.sleep(1)  # Demo bekleme
        st.session_state.results = get_demo_data()
    
    st.success("✅ Analiz tamamlandı!")

# Sonuçları göster
if st.session_state.results is not None:
    df = st.session_state.results
    
    # Filtreleme
    filtered_df = df[
        (df['RSI'] >= rsi_min) & 
        (df['Momentum'] >= momentum_min)
    ]
    
    st.subheader(f"📋 Taranan Hisseler ({len(filtered_df)} adet)")
    
    # Tablo
    st.dataframe(
        filtered_df,
        use_container_width=True,
        column_config={
            "Hisse": st.column_config.TextColumn("Hisse Kodu"),
            "Fiyat": st.column_config.NumberColumn("Fiyat (₺)", format="%.2f"),
            "RSI": st.column_config.NumberColumn("RSI", format="%.1f"),
            "Momentum": st.column_config.NumberColumn("Momentum", format="%.1f"),
            "ADX": st.column_config.NumberColumn("ADX", format="%.1f"),
            "Hacim Artış": st.column_config.NumberColumn("Hacim Artış", format="%.2f"),
            "Trend": st.column_config.TextColumn("Trend")
        },
        hide_index=True
    )
    
    # İstatistikler
    st.subheader("📊 İstatistikler")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        guclu_trend = filtered_df[filtered_df['Trend'].str.contains("Güçlü")].shape[0]
        st.metric("Güçlü Trend", guclu_trend)
    
    with col2:
        yeni_trend = filtered_df[filtered_df['Trend'].str.contains("Yeni")].shape[0]
        st.metric("Yeni Trend", yeni_trend)
    
    with col3:
        ort_rsi = filtered_df['RSI'].mean()
        st.metric("Ortalama RSI", f"{ort_rsi:.1f}")
    
    with col4:
        max_momentum = filtered_df['Momentum'].max()
        st.metric("Max Momentum", f"{max_momentum:.1f}")
    
    # CSV export
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 CSV İndir",
        data=csv,
        file_name=f"bist_tarama_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray; padding: 1rem;">
    <p>BIST TrendScout Pro v2.1 | © 2024</p>
</div>
""", unsafe_allow_html=True)
