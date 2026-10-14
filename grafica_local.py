import os
from pathlib import Path
import pandas as pd
import plotly.express as px

# 1. Cargar archivo de órdenes
DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).parent / "data"))
FILE_PATH = DATA_DIR / "Órdenes del Punto de venta (pos.order)(2).xlsx"

print("Cargando datos...")
df = pd.read_excel(FILE_PATH)

# 2. Filtrar año 2026
df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
df_2026 = df[df['Fecha'].dt.year == 2026].copy()
df_2026['Importe'] = pd.to_numeric(df_2026['Total'], errors='coerce').fillna(0.0)
df_2026['Responsable'] = df_2026['Responsable'].fillna('Sin asignar')

# 3. Mes y Semana
meses_nombres = {
    1: '01. Enero', 2: '02. Febrero', 3: '03. Marzo', 4: '04. Abril',
    5: '05. Mayo', 6: '06. Junio', 7: '07. Julio', 8: '08. Agosto',
    9: '09. Septiembre', 10: '10. Octubre', 11: '11. Noviembre', 12: '12. Diciembre'
}
df_2026['Mes'] = df_2026['Fecha'].dt.month.map(meses_nombres)
df_2026['Semana'] = 'Sem ' + df_2026['Fecha'].dt.isocalendar().week.astype(str).str.zfill(2)

# ==========================================================
# Selecciona aquí el modo: 'mes' o 'semana'
# ==========================================================
MODO = 'mes'  # Cambia a 'semana' si quieres ver por semana

if MODO == 'mes':
    df_agrupado = df_2026.groupby(['Mes', 'Responsable'], as_index=False)['Importe'].sum()
    x_col = 'Mes'
    titulo = "Importe Total 2026 Agrupado por Mes y Responsable (Barras Agrupadas)"
else:
    df_agrupado = df_2026.groupby(['Semana', 'Responsable'], as_index=False)['Importe'].sum()
    x_col = 'Semana'
    titulo = "Importe Total 2026 Agrupado por Semana y Responsable (Barras Agrupadas)"

fig = px.bar(
    df_agrupado,
    x=x_col,
    y='Importe',
    color='Responsable',
    barmode='group',
    title=titulo,
    labels={'Importe': 'Importe ($ MXN)', x_col: x_col, 'Responsable': 'Responsable'},
    text_auto='.2s'
)

fig.update_layout(
    template='plotly_white',
    xaxis_title=x_col,
    yaxis_title="Importe Total ($ MXN)",
    bargap=0.15,
    bargroupgap=0.05
)

fig.show()
