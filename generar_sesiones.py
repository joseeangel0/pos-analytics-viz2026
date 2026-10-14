from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from anonimizar import seudonimo
from db_config import get_engine
from sqlalchemy import text

# =============================================================================
# 1. CONEXIÓN A BASE DE DATOS SQL CON SQLALCHEMY
# =============================================================================
engine = get_engine()

# =============================================================================
# 2. QUERY_VARIABLE (EXTRACCIÓN DE SESIONES DESDE MYSQL VIZ2026)
# =============================================================================
query_variable = """
SELECT 
    `ID de sesión`,
    `Punto de venta`,
    `Abierta por` AS usuario,
    `Fecha de apertura`,
    `Fecha de cierre`,
    `Estado`
FROM `Sesión de Punto de venta (pos.session)`
WHERE `Fecha de apertura` IS NOT NULL 
  AND `Fecha de cierre` IS NOT NULL
"""

print("-> Conectando a MySQL [Viz2026] con SQLAlchemy...")
print("-> Ejecutando consulta definida en 'query_variable'...")

with engine.connect() as conn:
    df_sesiones = pd.read_sql(text(query_variable), con=conn)

print(f"-> [OK] {len(df_sesiones):,} registros de sesiones extraídos.")

# =============================================================================
# 3. FILTRADO Y TRATAMIENTO DE RUIDO (UX DATA CLEANING)
# =============================================================================
df_sesiones['Fecha de apertura'] = pd.to_datetime(df_sesiones['Fecha de apertura'], errors='coerce')
df_sesiones['Fecha de cierre'] = pd.to_datetime(df_sesiones['Fecha de cierre'], errors='coerce')

# Calcular duración en horas
df_sesiones['Duracion_Horas'] = (df_sesiones['Fecha de cierre'] - df_sesiones['Fecha de apertura']).dt.total_seconds() / 3600.0

# Tratamiento de ruido 1: Filtrar anomalías (turnos menores a 30 mins o mayores a 24 horas por olvido de cierre)
df_valido = df_sesiones[(df_sesiones['Duracion_Horas'] >= 0.5) & (df_sesiones['Duracion_Horas'] <= 24.0)].copy()

# Tratamiento de ruido 2: Separar usuarios reales de cajas automáticas/genéricas
df_valido['usuario'] = df_valido['usuario'].fillna('Sin asignar')
usuarios_sistema = ['Buho PV', 'Caja PCD', 'Administrador']
df_valido['tipo_usuario'] = df_valido['usuario'].apply(lambda x: 'Sistema/Caja' if x in usuarios_sistema else 'Colaborador')
df_valido['usuario'] = df_valido['usuario'].map(seudonimo)

# Granularidades temporales
df_valido['Año'] = df_valido['Fecha de apertura'].dt.year
df_valido['Semana'] = df_valido['Fecha de apertura'].dt.isocalendar().year.astype(str) + '-W' + df_valido['Fecha de apertura'].dt.isocalendar().week.astype(str).str.zfill(2)
df_valido['Mes'] = df_valido['Fecha de apertura'].dt.strftime('%Y-%m')

# Identificar colaboradores principales (mínimo 10 sesiones) para evitar líneas cortadas de 1 sola aparición
conteo = df_valido[df_valido['tipo_usuario'] == 'Colaborador']['usuario'].value_counts()
top_colaboradores = conteo[conteo >= 10].index.tolist()

# Agrupaciones
# 1. Semanal por colaborador
df_sem_top = df_valido[df_valido['usuario'].isin(top_colaboradores)].groupby(
    ['Semana', 'usuario'], as_index=False
)['Duracion_Horas'].mean().round(2)

# 2. Mensual por colaborador (Mucho más suave, elimina el ruido de zigzag semanal)
df_mes_top = df_valido[df_valido['usuario'].isin(top_colaboradores)].groupby(
    ['Mes', 'usuario'], as_index=False
)['Duracion_Horas'].mean().round(2)

# 3. Promedio global semanal de todo el equipo (Línea de referencia macro)
df_sem_global = df_valido[df_valido['tipo_usuario'] == 'Colaborador'].groupby(
    'Semana', as_index=False
)['Duracion_Horas'].mean().round(2)

# Métricas rápidas
duracion_media_global = df_valido[df_valido['tipo_usuario'] == 'Colaborador']['Duracion_Horas'].mean()
total_sesiones_colab = len(df_valido[df_valido['tipo_usuario'] == 'Colaborador'])
total_colabs = len(top_colaboradores)

# Paleta cromática accesible
PALETA = [
    '#2dd4bf', '#4ade80', '#93a1f8', '#fbbf24', '#f472b6',
    '#a78bfa', '#38bdf8', '#fb923c', '#e879f9', '#60a5fa'
]
color_map = {u: PALETA[i % len(PALETA)] for i, u in enumerate(top_colaboradores)}

# =============================================================================
# 4. CONSTRUCCIÓN DE LA VISUALIZACIÓN INTERACTIVA ANTIRRUIDO
# =============================================================================
fig = go.Figure()

# CONJUNTO 1: VISTA MENSUAL SUAVE (Anti-ruido, vista por defecto más limpia)
for u in top_colaboradores:
    sub = df_mes_top[df_mes_top['usuario'] == u].sort_values('Mes')
    fig.add_trace(go.Scatter(
        name=u,
        x=sub['Mes'],
        y=sub['Duracion_Horas'],
        mode='lines+markers',
        line=dict(color=color_map[u], width=2.5),
        marker=dict(size=7),
        visible=True,
        hovertemplate=f"<b>{u}</b><br>Mes: %{{x}}<br>Promedio: %{{y:.2f}} hrs<extra></extra>"
    ))

# CONJUNTO 2: VISTA SEMANAL DETALLADA
for u in top_colaboradores:
    sub = df_sem_top[df_sem_top['usuario'] == u].sort_values('Semana')
    fig.add_trace(go.Scatter(
        name=u,
        x=sub['Semana'],
        y=sub['Duracion_Horas'],
        mode='lines+markers',
        line=dict(color=color_map[u], width=1.8),
        marker=dict(size=4),
        visible=False,
        hovertemplate=f"<b>{u}</b><br>Semana: %{{x}}<br>Promedio: %{{y:.2f}} hrs<extra></extra>"
    ))

# CONJUNTO 3: BARRAS AGRUPADAS POR MES
for u in top_colaboradores:
    sub = df_mes_top[df_mes_top['usuario'] == u].sort_values('Mes')
    fig.add_trace(go.Bar(
        name=u,
        x=sub['Mes'],
        y=sub['Duracion_Horas'],
        marker_color=color_map[u],
        visible=False,
        hovertemplate=f"<b>{u}</b><br>Mes: %{{x}}<br>Promedio: %{{y:.2f}} hrs<extra></extra>"
    ))

M = len(top_colaboradores)
vis_mes = [True]*M + [False]*M + [False]*M
vis_sem = [False]*M + [True]*M + [False]*M
vis_barras = [False]*M + [False]*M + [True]*M

fig.update_layout(
    paper_bgcolor='#131a2a',
    plot_bgcolor='#131a2a',
    font=dict(color='#9aa5b8', family='-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', size=12),
    xaxis=dict(
        categoryorder='category ascending',
        title=dict(text="<b>Período Mensual (Evolución Suavizada)</b>", font=dict(color="#f8fafc")),
        gridcolor='#1e293b',
        showgrid=True,
        tickfont=dict(color='#cbd5e1'),
        rangeslider=dict(visible=False)  # Control deslizante opcional
    ),
    yaxis=dict(
        title=dict(text="<b>Duración Promedio (Horas por Turno)</b>", font=dict(color="#f8fafc")),
        gridcolor='#1e293b',
        showgrid=True,
        tickfont=dict(color='#cbd5e1'),
        ticksuffix=' hrs',
        range=[0, 16]  # Escala fija para evitar saltos bruscos
    ),
    legend=dict(
        title=dict(text="<b>Colaboradores (Clic para ocultar/aislar)</b>", font=dict(color="#f8fafc", size=13)),
        font=dict(color="#e2e8f0", size=11),
        bgcolor='rgba(19, 26, 42, 0.85)',
        bordercolor='#334155',
        borderwidth=1,
        orientation="h",
        yanchor="bottom",
        y=-0.38,
        xanchor="center",
        x=0.5
    ),
    hoverlabel=dict(
        bgcolor='#0c1322',
        bordercolor='#2dd4bf',
        font=dict(color='#f8fafc', size=13)
    ),
    margin=dict(l=70, r=40, t=110, b=130),
    height=670,
    barmode='group',
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
                    label="  🗓️ Vista Mensual (Suave / Sin Ruido)  ",
                    method="update",
                    args=[
                        {"visible": vis_mes},
                        {
                            "xaxis.title.text": "<b>Período Mensual (Evolución Suavizada)</b>",
                            "title.text": "<b>Duración Promedio de Sesiones por Mes x Colaborador (Tendencia Limpia)</b>"
                        }
                    ]
                ),
                dict(
                    label="  📆 Vista Semanal Detallada  ",
                    method="update",
                    args=[
                        {"visible": vis_sem},
                        {
                            "xaxis.title.text": "<b>Semana del Año (Cronológico)</b>",
                            "title.text": "<b>Duración Promedio de Sesiones por Semana x Colaborador</b>"
                        }
                    ]
                ),
                dict(
                    label="  📊 Comparativa en Barras  ",
                    method="update",
                    args=[
                        {"visible": vis_barras},
                        {
                            "xaxis.title.text": "<b>Período Mensual</b>",
                            "title.text": "<b>Comparativa en Barras de Horas por Turno</b>"
                        }
                    ]
                )
            ]
        )
    ],
    title=dict(
        text="<b>Duración Promedio de Sesiones por Mes x Colaborador (Tendencia Limpia)</b>",
        font=dict(color="#f8fafc", size=18),
        x=0.02,
        y=0.98
    )
)

# =============================================================================
# 5. GENERACIÓN DEL HTML FINAL (SESIONES.HTML) CON PLANTILLA UX
# =============================================================================
grafica_html = fig.to_html(include_plotlyjs='cdn', full_html=False)

plantilla_ux = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sesiones | Duración Promedio Semanal</title>
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
      flex-wrap: wrap;
    }}
    .nav-link {{
      display: inline-flex;
      align-items: center;
      padding: 9px 18px;
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
    .tip-box {{
      background-color: #0c1322;
      border: 1px solid #1e293b;
      border-left: 4px solid var(--accent-teal);
      border-radius: 8px;
      padding: 14px 18px;
      margin-bottom: 20px;
      font-size: 0.88rem;
      line-height: 1.5;
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
    <!-- Barra de Navegación del Suite Completo -->
    <nav class="nav-bar">
      <a href="ordenes.html" class="nav-link inactive">📋 Reporte de Órdenes</a>
      <a href="pagos.html" class="nav-link inactive">💳 Reporte de Pagos</a>
      <a href="sesiones.html" class="nav-link active">⏱️ Duración de Sesiones (Activo)</a>
    </nav>

    <header class="header">
      <div>
        <span class="badge">🟢 BASE DE DATOS MYSQL: VIZ2026 • ANÁLISIS DE TURNOS DE CAJA</span>
        <h1 class="title">Duración Promedio de Sesiones</h1>
        <p class="subtitle">Horas laboradas promedio por período temporal y colaborador (pos.session)</p>
      </div>
      <div class="metrics">
        <div class="metric-item">
          <span class="metric-label">Turno Promedio Global</span>
          <div class="metric-value">{duracion_media_global:.2f} hrs</div>
        </div>
        <div class="metric-item" style="border-left: 1px solid var(--border-default); padding-left: 20px;">
          <span class="metric-label">Sesiones de Colaboradores</span>
          <div class="metric-value" style="color: var(--text-main);">{total_sesiones_colab:,}</div>
        </div>
        <div class="metric-item" style="border-left: 1px solid var(--border-default); padding-left: 20px;">
          <span class="metric-label">Colaboradores Clave</span>
          <div class="metric-value" style="color: #4ade80;">{total_colabs}</div>
        </div>
      </div>
    </header>

    <div class="tip-box">
      <strong style="color: var(--text-main);">💡 Control de Ruido Visual (Tip UX):</strong> 
      <span style="color: var(--text-muted);">
        Para eliminar el efecto "espagueti" de semanas discontinuas, puedes alternar entre la <strong>Vista Mensual (Suave)</strong> y la <strong>Vista Semanal</strong> con los botones de arriba. 
        También puedes <strong>hacer clic en cualquier colaborador en la leyenda</strong> para aislarlo o apagarlo individualmente.
      </span>
    </div>

    <main class="card">
      {grafica_html}
    </main>
  </div>
</body>
</html>
"""

output_path = Path(__file__).parent / "sesiones.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(plantilla_ux)

print(f"\n=======================================================")
print(f"-> ¡Archivo HTML 'sesiones.html' optimizado exitosamente!")
print(f"-> Ruta: {output_path.resolve()}")
print(f"=======================================================")
