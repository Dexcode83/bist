# app.py
import numpy as np
import pandas as pd
import requests
import matplotlib.pyplot as plt
from scipy import stats
import ssl
from urllib import request
import io
import base64

import dash
from dash import dcc, html
from dash.dependencies import Input, Output

# --- Veri Fonksiyonları ---
def Hisse_Temel_Veriler():
    url1="https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/Temel-Degerler-Ve-Oranlar.aspx#page-1"
    context = ssl._create_unverified_context()
    response = request.urlopen(url1, context=context)
    url1 = response.read()
    df = pd.read_html(url1,decimal=',', thousands='.')
    df=df[6]
    Hisseler=df['Kod'].values.tolist()
    return Hisseler

def Stock_Prices(Hisse):
    Bar = 1000
    url = f"https://www.isyatirim.com.tr/_Layouts/15/IsYatirim.Website/Common/ChartData.aspx/IntradayDelay?period=120&code={Hisse}.E.BIST&last={Bar}"
    r1 = requests.get(url).json()
    data = pd.DataFrame.from_dict(r1)
    data[['Volume', 'Close']] = pd.DataFrame(data['data'].tolist(), index=data.index)
    data.drop(columns=['data'], inplace=True)
    return data

def Trend_Channel(df):
    best_period = None
    best_r_value = 0
    periods = [100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200]
    for period in periods:
        close_data = df['Close'].tail(period)
        x = np.arange(len(close_data))
        slope, intercept, r_value, _, _ = stats.linregress(x, close_data)
        if abs(r_value) > abs(best_r_value):
            best_r_value = abs(r_value)
            best_period = period
    return best_period, best_r_value

def Plot_Trendlines(Hisse,data,best_period):
    plt.close()
    close_data = data['Close'].tail(best_period)
    x_best_period = np.arange(len(close_data))
    slope_best_period, intercept_best_period, r_value_best_period, _, _ = stats.linregress(x_best_period, close_data)
    trendline=slope_best_period * x_best_period + intercept_best_period
    upper_channel = trendline + (trendline.std() * 1.1)
    lower_channel = trendline - (trendline.std() * 1.1)

    plt.figure(figsize=(10, 6))
    plt.plot(data.index, data['Close'], label='Kapanış Fiyatı')
    plt.plot(data.index[-best_period:], trendline, 'g-', label=f'Trend Çizgisi (R={r_value_best_period:.2f})')
    plt.fill_between(data.index[-best_period:], upper_channel, trendline, color='lightgreen', alpha=0.3, label='Üst Kanal')
    plt.fill_between(data.index[-best_period:], trendline, lower_channel, color='lightcoral', alpha=0.3, label='Alt Kanal')
    plt.title(str(Hisse)+' Kapanış Fiyatı ve Trend Çizgisi')
    plt.xlabel('Tarih Endeksi')
    plt.ylabel('Kapanış Fiyatı')
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    return "data:image/png;base64," + encoded, r_value_best_period

# --- Dash Uygulaması ---
app = dash.Dash(__name__)
hisseler = Hisse_Temel_Veriler()

app.layout = html.Div([
    html.H1("📊 Hisse Trend Kanal Dashboard"),
    dcc.Dropdown(
        id='hisse-dropdown',
        options=[{'label': h, 'value': h} for h in hisseler],
        value=hisseler[0],
        style={'width':'50%'}
    ),
    html.Div(id='output-graph'),
    html.Div(id='output-info', style={'marginTop':'20px','fontSize':'18px'})
])

@app.callback(
    [Output('output-graph', 'children'),
     Output('output-info', 'children')],
    Input('hisse-dropdown', 'value')
)
def update_graph(selected_hisse):
    try:
        data = Stock_Prices(selected_hisse)
        best_period, best_r_value = Trend_Channel(data)
        img, r_val = Plot_Trendlines(selected_hisse, data, best_period)
        graph = html.Img(src=img, style={'width':'80%'})
        info = f"{selected_hisse} için en iyi periyot: {best_period}, R değeri: {r_val:.2f}"
        return graph, info
    except Exception as e:
        return html.Div("Hata oluştu"), str(e)

if __name__ == '__main__':
    app.run_server(debug=True)
