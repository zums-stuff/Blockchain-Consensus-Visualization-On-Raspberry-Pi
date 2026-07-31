import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from plotly.subplots import make_subplots

def build_figure(df, title):
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=(
            '1. Energía Consumida (kWh)', 
            '2. Potencia del Hardware (W)',
            '3. Emisiones de CO₂ (kg)'
        )
    )

    # ---- Gráfico 1: Energía ----
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['energy_consumed'], mode='lines+markers', name='Energía Total', line=dict(color='#00e5ff', width=2)), row=1, col=1)
    if 'cpu_energy' in df.columns:
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['cpu_energy'], mode='lines', name='Energía CPU', line=dict(color='#2196f3', width=1, dash='dot')), row=1, col=1)
    if 'ram_energy' in df.columns:
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['ram_energy'], mode='lines', name='Energía RAM', line=dict(color='#4caf50', width=1, dash='dot')), row=1, col=1)

    # ---- Gráfico 2: Potencia ----
    if 'cpu_power' in df.columns:
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['cpu_power'], mode='lines+markers', name='Potencia CPU (W)', line=dict(color='#ff9800', width=2)), row=2, col=1)
    if 'ram_power' in df.columns:
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['ram_power'], mode='lines+markers', name='Potencia RAM (W)', line=dict(color='#cddc39', width=2)), row=2, col=1)

    # ---- Gráfico 3: Emisiones ----
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['emissions'], mode='lines+markers', name='CO₂ Total (kg)', line=dict(color='#ff5252', width=3)), row=3, col=1)
    if 'emissions_rate' in df.columns:
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['emissions_rate'], mode='lines', name='Tasa CO₂ (kg/s)', line=dict(color='#e91e63', width=1, dash='dash')), row=3, col=1)

    fig.update_layout(
        title_text=title,
        height=1000,
        template="plotly_dark",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_yaxes(title_text="kWh", row=1, col=1)
    fig.update_yaxes(title_text="Watts (W)", row=2, col=1)
    fig.update_yaxes(title_text="kg CO₂", row=3, col=1)
    fig.update_xaxes(title_text="Marca de Tiempo", row=3, col=1)
    
    return fig

def generate_report():
    if not os.path.exists('emissions.csv'):
        print("No se encontró emissions.csv. No se puede generar el reporte.")
        return

    try:
        df = pd.read_csv('emissions.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # 1. Reporte General (todo el histórico)
        fig_general = build_figure(df, "Dashboard Histórico Completo de Energía (Todas las pruebas)")
        fig_general.write_html('reporte_energia_general.html')
        print("Reporte general generado: reporte_energia_general.html")
        
        # 2. Reporte Actual (solo el último test)
        if 'run_id' in df.columns:
            last_run_id = df['run_id'].iloc[-1]
            df_actual = df[df['run_id'] == last_run_id]
        else:
            df_actual = df
            
        fig_actual = build_figure(df_actual, "Dashboard de Energía del Nodo (Última prueba)")
        fig_actual.write_html('reporte_energia_actual.html')
        print("Reporte actual generado: reporte_energia_actual.html")

    except Exception as e:
        print(f"Error generando gráfica: {e}")

if __name__ == "__main__":
    generate_report()
