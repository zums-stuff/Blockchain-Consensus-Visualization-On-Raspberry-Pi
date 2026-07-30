import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import sys

def main():
    if not os.path.exists("tx_metrics.csv"):
        print("No tx_metrics.csv found. Skip analyzing packets.")
        return

    # 1. Leer los datos
    try:
        df = pd.read_csv("tx_metrics.csv")
    except Exception as e:
        print(f"Error al leer tx_metrics.csv: {e}")
        return

    if df.empty:
        print("El archivo tx_metrics.csv está vacío.")
        return

    # Convertir a datetime si queremos mostrar hora, sino usar índice o time_sent relativo
    # time_sent es un timestamp epoch (ej. 1655000000.123)
    df['time_sent_dt'] = pd.to_datetime(df['time_sent'], unit='s')
    df['time_mined_dt'] = pd.to_datetime(df['time_mined'], unit='s')
    
    # Tiempo relativo al inicio del experimento (en segundos)
    start_time = df['time_sent'].min()
    df['relative_time_sec'] = df['time_sent'] - start_time

    # 2. Generar Gráfico de Tiempo de Terminación
    fig1 = px.line(df, x='relative_time_sec', y='completion_time_sec', 
                  markers=True,
                  title="Tiempo de Terminación de Paquete (Transacción) a lo largo del tiempo",
                  labels={
                      'relative_time_sec': 'Tiempo del experimento (segundos)',
                      'completion_time_sec': 'Tiempo de Terminación (Segundos)'
                  },
                  template='plotly_dark')

    fig1.update_traces(line=dict(color='#00ffcc', width=2), marker=dict(size=8, color='#ff00ff'))

    # Agregar promedio
    avg_completion = df['completion_time_sec'].mean()
    fig1.add_hline(y=avg_completion, line_dash="dash", line_color="orange",
                  annotation_text=f"Promedio: {avg_completion:.2f}s", 
                  annotation_position="bottom right")

    # 3. Guardar gráfico como HTML independiente
    try:
        fig1.write_html("reporte_paquetes.html")
        print("Gráfico generado exitosamente en reporte_paquetes.html")
    except Exception as e:
        print(f"Error generando gráfica de paquetes: {e}")

if __name__ == "__main__":
    main()
