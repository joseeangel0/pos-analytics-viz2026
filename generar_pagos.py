from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import text
from anonimizar import seudonimo_metodo
from db_config import get_engine

# =============================================================================
# 1. CONEXIÓN A BASE DE DATOS SQL CON SQLALCHEMY
# =============================================================================
engine = get_engine()

# =============================================================================
# 2. QUERY_VARIABLE (EXTRACCIÓN DE PAGOS ÚNICAMENTE 2025-2026)
# =============================================================================
query_variable = """
SELECT 
    `Fecha`,
    `Método de pago` AS metodo_pago,
    `Importe`
FROM `Pagos en Punto de venta (pos.payment)(1)`
WHERE `Fecha` >= '2025-01-01' AND `Fecha` < '2027-01-01'
"""

print("-> Conectando a MySQL [Viz2026] con SQLAlchemy...")
print("-> Ejecutando consulta definida en 'query_variable'...")

with engine.connect() as conn:
    df_pagos = pd.read_sql(text(query_variable), con=conn)

print(f"-> [OK] {len(df_pagos):,} registros de pagos extraídos para el período 2025-2026.")

# Normalización de datos
df_pagos['Fecha'] = pd.to_datetime(df_pagos['Fecha'], errors='coerce')
df_pagos['Importe'] = pd.to_numeric(df_pagos['Importe'], errors='coerce').fillna(0.0)
df_pagos['metodo_pago'] = df_pagos['metodo_pago'].fillna('Otro').map(seudonimo_metodo)

total_recaudado = df_pagos['Importe'].sum()
total_transacciones = len(df_pagos)

# =============================================================================
# 3. ENRIQUECIMIENTO TEMPORAL: DÍA, SEMANA, MES Y TRIMESTRE
# =============================================================================
df_pagos['Dia'] = df_pagos['Fecha'].dt.strftime('%Y-%m-%d')
df_pagos['Semana'] = df_pagos['Fecha'].dt.isocalendar().year.astype(str) + '-W' + df_pagos['Fecha'].dt.isocalendar().week.astype(str).str.zfill(2)
df_pagos['Mes'] = df_pagos['Fecha'].dt.strftime('%Y-%m')
df_pagos['Trimestre'] = df_pagos['Fecha'].dt.year.astype(str) + '-Q' + df_pagos['Fecha'].dt.quarter.astype(str)

# Identificar los principales métodos de pago para mantener un diseño visual limpio
top_metodos = df_pagos.groupby('metodo_pago')['Importe'].sum().sort_values(ascending=False).index.tolist()
# Tomamos los 8 principales métodos y agrupamos los menores en 'Otros métodos' para legibilidad óptima
principales = top_metodos[:8]
df_pagos['metodo_grafica'] = df_pagos['metodo_pago'].apply(lambda x: x if x in principales else 'Otros métodos')
metodos_unicos = principales + ['Otros métodos']

# Paleta cromática accesible y contrastada para modo oscuro
PALETA = [
    '#2dd4bf',  # Turquesa
    '#4ade80',  # Esmeralda menta
    '#93a1f8',  # Indigo suave
    '#fbbf24',  # Ámbar dorado
    '#f472b6',  # Rosa vibrante
    '#a78bfa',  # Violeta
    '#38bdf8',  # Cyan eléctrico
    '#fb923c',  # Naranja coral
    '#94a3b8'   # Gris neutro para 'Otros métodos'
]
color_map = {m: PALETA[i % len(PALETA)] for i, m in enumerate(metodos_unicos)}

# Agrupaciones
grp_mes = df_pagos.groupby(['Mes', 'metodo_grafica'], as_index=False)['Importe'].sum()
grp_qtr = df_pagos.groupby(['Trimestre', 'metodo_grafica'], as_index=False)['Importe'].sum()
grp_sem = df_pagos.groupby(['Semana', 'metodo_grafica'], as_index=False)['Importe'].sum()
grp_dia = df_pagos.groupby(['Dia', 'metodo_grafica'], as_index=False)['Importe'].sum()

# =============================================================================
# 4. CONSTRUCCIÓN DE LA GRÁFICA MULTI-TEMPORAL CON BOTONES EN PLOTLY
# =============================================================================
fig = go.Figure()

# 1. Trazas por MES (Visibles por defecto)
for m in metodos_unicos:
    sub = grp_mes[grp_mes['metodo_grafica'] == m]
    fig.add_trace(go.Bar(
        name=m,
        x=sub['Mes'],
        y=sub['Importe'],
        marker_color=color_map[m],
        visible=True,
        hovertemplate=f"<b>{m}</b><br>Mes: %{{x}}<br>Importe: $%{{y:,.2f}} MXN<extra></extra>"
    ))

# 2. Trazas por TRIMESTRE
for m in metodos_unicos:
    sub = grp_qtr[grp_qtr['metodo_grafica'] == m]
    fig.add_trace(go.Bar(
        name=m,
        x=sub['Trimestre'],
        y=sub['Importe'],
        marker_color=color_map[m],
        visible=False,
        hovertemplate=f"<b>{m}</b><br>Trimestre: %{{x}}<br>Importe: $%{{y:,.2f}} MXN<extra></extra>"
    ))

# 3. Trazas por SEMANA
for m in metodos_unicos:
    sub = grp_sem[grp_sem['metodo_grafica'] == m]
    fig.add_trace(go.Bar(
        name=m,
        x=sub['Semana'],
        y=sub['Importe'],
        marker_color=color_map[m],
        visible=False,
        hovertemplate=f"<b>{m}</b><br>Semana: %{{x}}<br>Importe: $%{{y:,.2f}} MXN<extra></extra>"
    ))

# 4. Trazas por DÍA
for m in metodos_unicos:
    sub = grp_dia[grp_dia['metodo_grafica'] == m]
    fig.add_trace(go.Bar(
        name=m,
        x=sub['Dia'],
        y=sub['Importe'],
        marker_color=color_map[m],
        visible=False,
        hovertemplate=f"<b>{m}</b><br>Día: %{{x}}<br>Importe: $%{{y:,.2f}} MXN<extra></extra>"
    ))

K = len(metodos_unicos)
vis_mes = [True]*K + [False]*K + [False]*K + [False]*K
vis_qtr = [False]*K + [True]*K + [False]*K + [False]*K
vis_sem = [False]*K + [False]*K + [True]*K + [False]*K
vis_dia = [False]*K + [False]*K + [False]*K + [True]*K

fig.update_layout(
    barmode='stack',
    paper_bgcolor='#131a2a',
    plot_bgcolor='#131a2a',
    font=dict(color='#9aa5b8', family='-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', size=12),
    xaxis=dict(
        categoryorder='category ascending',
        title=dict(text="<b>Período Mensual (2025 — 2026)</b>", font=dict(color="#f8fafc")),
        gridcolor='#1e293b',
        showgrid=True,
        tickfont=dict(color='#cbd5e1')
    ),
    yaxis=dict(
        title=dict(text="<b>Importe Total Recaudado ($ MXN)</b>", font=dict(color="#f8fafc")),
        gridcolor='#1e293b',
        showgrid=True,
        tickfont=dict(color='#cbd5e1'),
        tickprefix='$',
        tickformat=',.0f'
    ),
    legend=dict(
        title=dict(text="<b>Método de Pago</b>", font=dict(color="#f8fafc", size=13)),
        font=dict(color="#e2e8f0", size=11),
        bgcolor='rgba(19, 26, 42, 0.85)',
        bordercolor='#334155',
        borderwidth=1,
        orientation="h",
        yanchor="bottom",
        y=-0.32,
        xanchor="center",
        x=0.5
    ),
    hoverlabel=dict(
        bgcolor='#0c1322',
        bordercolor='#2dd4bf',
        font=dict(color='#f8fafc', size=13)
    ),
    margin=dict(l=70, r=40, t=110, b=120),
    height=660,
    updatemenus=[
        dict(
            type="buttons",
            direction="right",
            active=0,
            x=0.5,
            xanchor="center",
            y=1.16,
            yanchor="top",
            bgcolor="#1e293b",
            bordercolor="#2dd4bf",
            borderwidth=1,
            font=dict(color="#f8fafc", size=13),
            buttons=[
                dict(
                    label="  🗓️ Por Mes  ",
                    method="update",
                    args=[
                        {"visible": vis_mes},
                        {
                            "xaxis.title.text": "<b>Período Mensual (2025 — 2026)</b>",
                            "title.text": "<b>Importe de Pagos por Mes (2025 — 2026)</b>",
                            "barmode": "stack"
                        }
                    ]
                ),
                dict(
                    label="  📊 Por Trimestre  ",
                    method="update",
                    args=[
                        {"visible": vis_qtr},
                        {
                            "xaxis.title.text": "<b>Trimestre (2025Q1 — 2026Q3)</b>",
                            "title.text": "<b>Importe de Pagos por Trimestre (2025 — 2026)</b>",
                            "barmode": "stack"
                        }
                    ]
                ),
                dict(
                    label="  📆 Por Semana  ",
                    method="update",
                    args=[
                        {"visible": vis_sem},
                        {
                            "xaxis.title.text": "<b>Semana del Año (2025 — 2026)</b>",
                            "title.text": "<b>Importe de Pagos por Semana (2025 — 2026)</b>",
                            "barmode": "stack"
                        }
                    ]
                ),
                dict(
                    label="  📅 Por Día  ",
                    method="update",
                    args=[
                        {"visible": vis_dia},
                        {
                            "xaxis.title.text": "<b>Fecha Diaria (2025 — 2026)</b>",
                            "title.text": "<b>Importe de Pagos por Día (2025 — 2026)</b>",
                            "barmode": "stack"
                        }
                    ]
                )
            ]
        )
    ],
    title=dict(
        text="<b>Importe de Pagos por Mes (2025 — 2026)</b>",
        font=dict(color="#f8fafc", size=18),
        x=0.02,
        y=0.98
    )
)

# =============================================================================
# 5. GENERACIÓN DEL ARCHIVO HTML FINAL (PAGOS.HTML) CON PLANTILLA UX
# =============================================================================
grafica_html = fig.to_html(include_plotlyjs='cdn', full_html=False)

plantilla_ux = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Pagos 2025-2026 | Visualización SQL</title>
  <style>
    :root {{
      --bg-app: #0a0f1c;
      --bg-surface: #131a2a;
      --bg-card: #0c1322;
      --border-default: #1e293b;
      --border-accent: #2dd4bf;
      --text-main: #f8fafc;
      --text-muted: #9aa5b8;
      --accent-teal: #2dd4bf;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 32px 24px;
      background-color: var(--bg-app);
      color: var(--text-main);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      -webkit-font-smoothing: antialiased;
    }}
    .container {{
      max-width: 1400px;
      margin: 0 auto;
    }}
    .nav-bar {{
      display: flex;
      gap: 12px;
      margin-bottom: 24px;
    }}
    .nav-link {{
      display: inline-flex;
      align-items: center;
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 0.88rem;
      font-weight: 600;
      text-decoration: none;
      transition: all 0.2s ease;
    }}
    .nav-link.active {{
      background-color: rgba(45, 212, 191, 0.15);
      color: var(--accent-teal);
      border: 1px solid rgba(45, 212, 191, 0.35);
    }}
    .nav-link.inactive {{
      background-color: var(--bg-surface);
      color: var(--text-muted);
      border: 1px solid var(--border-default);
    }}
    .nav-link.inactive:hover {{
      color: var(--text-main);
      border-color: #475569;
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 20px;
      padding-bottom: 24px;
      margin-bottom: 24px;
      border-bottom: 1px solid var(--border-default);
    }}
    .badge {{
      display: inline-block;
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      color: #4ade80;
      background-color: rgba(34, 197, 94, 0.12);
      border: 1px solid rgba(34, 197, 94, 0.28);
      padding: 4px 10px;
      border-radius: 6px;
      margin-bottom: 8px;
    }}
    .title {{
      font-size: 2rem;
      font-weight: 800;
      color: var(--text-main);
      margin: 0 0 6px 0;
      letter-spacing: -0.02em;
    }}
    .subtitle {{
      font-size: 0.95rem;
      color: var(--text-muted);
      margin: 0;
    }}
    .metrics {{
      display: flex;
      align-items: center;
      gap: 20px;
    }}
    .metric-item {{
      text-align: right;
    }}
    .metric-label {{
      font-size: 0.75rem;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 600;
      display: block;
    }}
    .metric-value {{
      font-size: 1.35rem;
      font-weight: 800;
      color: var(--accent-teal);
    }}
    .card {{
      background-color: var(--bg-surface);
      border: 1px solid var(--border-default);
      border-radius: 14px;
      padding: 24px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
      margin-bottom: 24px;
    }}
    .query-banner {{
      background-color: var(--bg-card);
      border: 1px solid var(--border-default);
      border-left: 4px solid var(--border-accent);
      border-radius: 8px;
      padding: 14px 18px;
      margin-bottom: 20px;
      font-size: 0.88rem;
    }}
    .query-code {{
      font-family: Consolas, "Courier New", monospace;
      color: var(--accent-teal);
      font-weight: 600;
    }}
  </style>
</head>
<body>
  <div class="container">
    <!-- Barra de Navegación Rápida -->
    <nav class="nav-bar">
      <a href="ordenes.html" class="nav-link inactive">📋 Ver Reporte de Órdenes</a>
      <a href="pagos.html" class="nav-link active">💳 Reporte de Pagos (Activo)</a>
      <a href="sesiones.html" class="nav-link inactive">⏱️ Ver Duración de Sesiones</a>
    </nav>

    <header class="header">
      <div>
        <span class="badge">🟢 BASE DE DATOS MYSQL: VIZ2026 • REPORTE MULTI-TEMPORAL</span>
        <h1 class="title">Visualización de Pagos (2025 — 2026)</h1>
        <p class="subtitle">Importe por Método de Pago analizable por Día, Semana, Mes y Trimestre</p>
      </div>
      <div class="metrics">
        <div class="metric-item">
          <span class="metric-label">Recaudación (2025-2026)</span>
          <div class="metric-value">${total_recaudado:,.2f} MXN</div>
        </div>
        <div class="metric-item" style="border-left: 1px solid var(--border-default); padding-left: 20px;">
          <span class="metric-label">Pagos Registrados</span>
          <div class="metric-value" style="color: var(--text-main);">{total_transacciones:,}</div>
        </div>
      </div>
    </header>

    <div class="query-banner">
      <span style="color: var(--text-muted); display: block; margin-bottom: 4px;">Variable de Consulta Utilizada:</span>
      <code class="query-code">query_variable = "SELECT `Fecha`, `Método de pago` AS metodo_pago, `Importe` FROM `Pagos en Punto de venta (pos.payment)(1)` WHERE `Fecha` >= '2025-01-01' AND `Fecha` < '2027-01-01'"</code>
    </div>

    <main class="card">
      {grafica_html}
    </main>
  </div>
</body>
</html>
"""

output_path = Path(__file__).parent / "pagos.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(plantilla_ux)

print(f"\n=======================================================")
print(f"-> ¡Archivo HTML generado exitosamente!")
print(f"-> Ruta: {output_path.resolve()}")
print(f"=======================================================")
