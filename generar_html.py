from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import text
from anonimizar import seudonimo
from db_config import get_engine

# =============================================================================
# 1. CONEXIÓN A BASE DE DATOS SQL CON SQLALCHEMY
# =============================================================================
engine = get_engine()

# =============================================================================
# 2. QUERY VARIABLE (REQUERIMIENTO: EXTRAER DATOS VÍA VARIABLE SQL)
# =============================================================================
query_variable = """
SELECT 
    `Mes`,
    `Semana`,
    `Responsable`,
    `Total`
FROM `Órdenes del Punto de venta (pos.order)(2)`
WHERE `Año` = 2026
"""

print("-> Conectando a MySQL [Viz2026] con SQLAlchemy...")
print(f"-> Ejecutando consulta definida en 'query_variable'...")

with engine.connect() as conn:
    df_2026 = pd.read_sql(text(query_variable), con=conn)

print(f"-> [OK] {len(df_2026):,} filas extraídas de la Base de Datos.")

# Normalización de datos
df_2026['Importe'] = pd.to_numeric(df_2026['Total'], errors='coerce').fillna(0.0)
df_2026['Responsable'] = df_2026['Responsable'].fillna('Sin asignar').map(seudonimo)

total_facturado = df_2026['Importe'].sum()
total_tickets = len(df_2026)

# =============================================================================
# 3. PREPARACIÓN DE DATOS AGRUPADOS (MES Y SEMANA)
# =============================================================================
# Agrupación por Mes y Responsable
df_mes = df_2026.groupby(['Mes', 'Responsable'], as_index=False)['Importe'].sum()
meses_orden = sorted(df_mes['Mes'].unique())
responsables_lista = sorted(df_2026['Responsable'].unique())

# Agrupación por Semana y Responsable
df_sem = df_2026.groupby(['Semana', 'Responsable'], as_index=False)['Importe'].sum()
semanas_orden = sorted(df_sem['Semana'].unique())

# Paleta cromática de alta distinción para modo oscuro
PALETA = [
    '#2dd4bf', '#93a1f8', '#4ade80', '#fbbf24', '#f472b6',
    '#a78bfa', '#38bdf8', '#fb923c', '#e879f9', '#60a5fa'
]

# =============================================================================
# 4. CONSTRUCCIÓN DE LA FIGURA PLOTLY CON BOTONES INTERACTIVOS (MES / SEMANA)
# =============================================================================
fig = go.Figure()

# Trazas de Mes (Visibles por defecto)
for i, resp in enumerate(responsables_lista):
    sub = df_mes[df_mes['Responsable'] == resp]
    color = PALETA[i % len(PALETA)]
    fig.add_trace(go.Bar(
        name=resp,
        x=sub['Mes'],
        y=sub['Importe'],
        marker_color=color,
        visible=True,
        hovertemplate=f"<b>{resp}</b><br>Mes: %{{x}}<br>Importe: $%{{y:,.2f}} MXN<extra></extra>"
    ))

# Trazas de Semana (Inicialmente ocultas)
for i, resp in enumerate(responsables_lista):
    sub = df_sem[df_sem['Responsable'] == resp]
    color = PALETA[i % len(PALETA)]
    fig.add_trace(go.Bar(
        name=resp,
        x=sub['Semana'],
        y=sub['Importe'],
        marker_color=color,
        visible=False,
        hovertemplate=f"<b>{resp}</b><br>Semana: %{{x}}<br>Importe: $%{{y:,.2f}} MXN<extra></extra>"
    ))

n_traces = len(responsables_lista)
visible_mes = [True] * n_traces + [False] * n_traces
visible_sem = [False] * n_traces + [True] * n_traces

# Configuración de diseño UX de alto contraste con botones interactivos
fig.update_layout(
    barmode='group',
    paper_bgcolor='#131a2a',
    plot_bgcolor='#131a2a',
    font=dict(color='#9aa5b8', family='-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', size=12),
    xaxis=dict(
        categoryorder='category ascending',
        title=dict(text="<b>Mes del Año (2026)</b>", font=dict(color="#f8fafc")),
        gridcolor='#1e293b',
        showgrid=True,
        tickfont=dict(color='#cbd5e1')
    ),
    yaxis=dict(
        title=dict(text="<b>Importe Total ($ MXN)</b>", font=dict(color="#f8fafc")),
        gridcolor='#1e293b',
        showgrid=True,
        tickfont=dict(color='#cbd5e1'),
        tickprefix='$',
        tickformat=',.0f'
    ),
    legend=dict(
        title=dict(text="<b>Responsable</b>", font=dict(color="#f8fafc", size=13)),
        font=dict(color="#e2e8f0", size=11),
        bgcolor='rgba(19, 26, 42, 0.85)',
        bordercolor='#334155',
        borderwidth=1,
        orientation="h",
        yanchor="bottom",
        y=-0.35,
        xanchor="center",
        x=0.5
    ),
    hoverlabel=dict(
        bgcolor='#0c1322',
        bordercolor='#2dd4bf',
        font=dict(color='#f8fafc', size=13)
    ),
    margin=dict(l=70, r=40, t=110, b=120),
    bargap=0.15,
    bargroupgap=0.04,
    height=650,
    # Menú de botones para alternar entre Mes y Semana dentro del HTML
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
                    label="  📅 Agrupar por Mes  ",
                    method="update",
                    args=[
                        {"visible": visible_mes},
                        {
                            "xaxis.title.text": "<b>Mes del Año (2026)</b>",
                            "title.text": "<b>Importe Total 2026 Agrupado por Mes y Responsable</b>"
                        }
                    ]
                ),
                dict(
                    label="  📆 Agrupar por Semana  ",
                    method="update",
                    args=[
                        {"visible": visible_sem},
                        {
                            "xaxis.title.text": f"<b>Semana del Año ({semanas_orden[0]} — {semanas_orden[-1]} de 2026)</b>",
                            "title.text": "<b>Importe Total 2026 Agrupado por Semana y Responsable</b>"
                        }
                    ]
                )
            ]
        )
    ],
    title=dict(
        text="<b>Importe Total 2026 Agrupado por Mes y Responsable</b>",
        font=dict(color="#f8fafc", size=18),
        x=0.02,
        y=0.98
    )
)

# =============================================================================
# 5. GENERACIÓN DEL ARCHIVO HTML FINAL (ORDENES.HTML) CON PLANTILLA UX
# =============================================================================
# Renderizar gráfica interactiva a snippet HTML
grafica_html = fig.to_html(include_plotlyjs='cdn', full_html=False)

plantilla_ux = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Órdenes 2026 | Visualización SQL</title>
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
      <a href="ordenes.html" class="nav-link active">📋 Reporte de Órdenes (Activo)</a>
      <a href="pagos.html" class="nav-link inactive">💳 Ver Reporte de Pagos</a>
      <a href="sesiones.html" class="nav-link inactive">⏱️ Ver Duración de Sesiones</a>
    </nav>

    <header class="header">
      <div>
        <span class="badge">🟢 BASE DE DATOS MYSQL: VIZ2026 • REPORTE SQL</span>
        <h1 class="title">Visualización de Órdenes 2026</h1>
        <p class="subtitle">Datos alimentados directamente desde MySQL mediante SQLAlchemy</p>
      </div>
      <div class="metrics">
        <div class="metric-item">
          <span class="metric-label">Facturación 2026</span>
          <div class="metric-value">${total_facturado:,.2f} MXN</div>
        </div>
        <div class="metric-item" style="border-left: 1px solid var(--border-default); padding-left: 20px;">
          <span class="metric-label">Registros Extraídos</span>
          <div class="metric-value" style="color: var(--text-main);">{total_tickets:,}</div>
        </div>
      </div>
    </header>

    <div class="query-banner">
      <span style="color: var(--text-muted); display: block; margin-bottom: 4px;">Variable de Consulta Utilizada:</span>
      <code class="query-code">query_variable = "SELECT `Mes`, `Semana`, `Responsable`, `Total` FROM `Órdenes del Punto de venta (pos.order)(2)` WHERE `Año` = 2026"</code>
    </div>

    <main class="card">
      {grafica_html}
    </main>
  </div>
</body>
</html>
"""

output_path = Path(__file__).parent / "ordenes.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(plantilla_ux)

print(f"\n=======================================================")
print(f"-> ¡Archivo HTML generado exitosamente!")
print(f"-> Ruta: {output_path.resolve()}")
print(f"=======================================================")
