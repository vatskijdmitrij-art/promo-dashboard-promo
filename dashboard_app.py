import pandas as pd
import numpy as np
import re
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output
import os

# Загрузка данных
df = pd.read_excel("Для Дашборда.xlsx")

# --- Функции очистки остаются прежними ---
def clean_money(x):
    if pd.isna(x): return 0
    if isinstance(x, (int, float)): return x
    x = str(x).lower().replace('промо активно', '').replace('руб.', '').replace('\n', ' ').replace(',', '.')
    match = re.search(r'[\d\s]+', x)
    return float(match.group(0).replace(' ', '')) if match else 0

def clean_slots(x):
    if pd.isna(x): return 0
    if isinstance(x, (int, float)): return x
    match = re.search(r'(\d+)', str(x))
    return int(match.group(1)) if match else 0

def clean_au(x):
    if pd.isna(x): return 0
    if isinstance(x, (int, float)): return x
    parts = str(x).split('\\')
    if len(parts) > 1:
        match = re.search(r'(\d+)', parts[1])
        if match: return int(match.group(1))
    match = re.search(r'(\d+)', str(x))
    return int(match.group(1)) if match else 0

for col in ['План бюджет', 'Факт бюджет']: df[col] = df[col].apply(clean_money)
for col in ['Занято слотов', 'Заказали товар, АУ']: df[col] = df[col].apply(clean_slots)
df['Всего АУ'] = df['Заказали товар, АУ'].apply(clean_au)
df['Производитель'] = df['Производитель'].ffill()
df = df[df['Производитель'].notna() & (df['Производитель'] != '') & (df['Производитель'] != 'Итого · 28 промо')]

# --- Инициализация приложения ---
server = app = Flask(__name__) # Это необходимо для Heroku

app = Dash(__name__)

app.layout = html.Div([
    html.H1("Дашборд промо-активностей", style={'textAlign': 'center', 'padding': '20px'}),
    
    html.Div([
        html.Div([
            html.Label("Выберите производителей:"),
            dcc.Dropdown(
                id='producer-filter',
                options=[{'label': p, 'value': p} for p in sorted(df['Производитель'].unique())],
                value=[sorted(df['Производитель'].unique())[0]], multi=True
            )
        ], style={'width': '30%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px'}),
        
        html.Div([
            html.Label("Показатель АУ:"),
            dcc.RadioItems(
                id='au-metric-type',
                options=[
                    {'label': 'Заказали товар (бронь)', 'value': 'Заказали товар, АУ'},
                    {'label': 'АУ (закупка)', 'value': 'Всего АУ'}
                ],
                value='Заказали товар, АУ',
                labelStyle={'display': 'inline-block', 'margin-right': '15px'}
            )
        ], style={'width': '25%', 'display': 'inline-block', 'padding': '10px'})
    ]),
    
    dcc.Graph(id='main-trend-graph'),
    
    html.Div(id='kpi-cards', style={'display': 'flex', 'justify-content': 'space-around', 'padding': '20px'})
])

@app.callback(
    [Output('main-trend-graph', 'figure'), Output('kpi-cards', 'children')],
    [Input('producer-filter', 'value'), Input('au-metric-type', 'value')]
)
def update_graph(selected_producers, au_metric):
    if not selected_producers:
        return go.Figure(), []
    
    dff = df[df['Производитель'].isin(selected_producers)]
    trend = dff.groupby(['Дата (неделя)', 'Производитель']).agg({
        'План бюджет': 'sum', 'Факт бюджет': 'sum', 'Занято слотов': 'sum',
        'Заказали товар, АУ': 'sum', 'Всего АУ': 'sum'
    }).reset_index()
    
    kpi_budget = trend['Факт бюджет'].sum()
    kpi_slots = trend['Занято слотов'].sum()
    kpi_au = trend[au_metric].sum()
    
    kpi_cards = [
        html.Div([html.H3("Факт бюджет"), html.P(f"{kpi_budget:,.0f} ₽".replace(',', ' '))], 
                 style={'border': '1px solid #ccc', 'padding': '15px', 'borderRadius': '8px', 'minWidth': '150px'}),
        html.Div([html.H3("Занято слотов"), html.P(f"{kpi_slots:,}".replace(',', ' '))], 
                 style={'border': '1px solid #ccc', 'padding': '15px', 'borderRadius': '8px', 'minWidth': '150px'}),
        html.Div([html.H3("АУ"), html.P(f"{kpi_au:,}".replace(',', ' '))], 
                 style={'border': '1px solid #ccc', 'padding': '15px', 'borderRadius': '8px', 'minWidth': '150px'})
    ]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=trend['Дата (неделя)'], y=trend['Занято слотов'], mode='lines+markers', name='Занято слотов', line=dict(color='royalblue', width=3)))
    fig.add_trace(go.Scatter(x=trend['Дата (неделя)'], y=trend[au_metric], mode='lines+markers', name=au_metric, line=dict(color='firebrick', width=3, dash='dot')))
    
    fig.update_layout(title="Динамика слотов и аптечных учреждений", xaxis_title="Неделя", yaxis_title="Количество", hovermode="x unified")
    
    return fig, kpi_cards

# Запуск через порт окружения (важно для облака)
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run_server(host='0.0.0.0', port=port)
Пошаговый план развертывания (Deployment)

Вам понадобится аккаунт на GitHub и на Heroku.

Подготовка файлов. В папке с вашим проектом должны лежать три файла:

dashboard_app.py (код выше).
Для Дашборда.xlsx.
requirements.txt. Создайте этот текстовый файл и напишите внутри:
Копировать
pandas==2.2.2
numpy==2.0.0
plotly==5.22.0
dash==2.17.0
openpyxl==3.1.2
gunicorn==22.0.0
flask==3.0.3
