import pandas as pd
import plotly.express as px
from sqlalchemy import text
from anonimizar import seudonimo, seudonimo_metodo
from db_config import get_engine, DB_NAME
from dash import Dash, html, dcc, Input, Output

# =============================================================================
# 1. CONEXIÓN A BASE DE DATOS MEDIANTE SQLALCHEMY
# =============================================================================
engine = get_engine()
is_mysql = "mysql" in str(engine.url)
db_status = f"MySQL Server 8.0: {DB_NAME}" if is_mysql else f"SQLite Local: {DB_NAME}.db"
print(f"-> [UX App] Conectado a {db_status}.")

# =============================================================================
# 2. CONSULTAS SQL (UNA POR VISUALIZACIÓN)
# =============================================================================
query_ordenes = """
SELECT `Mes`, `Semana`, `Responsable`, `Total`
FROM `Órdenes del Punto de venta (pos.order)(2)`
WHERE `Año` = 2026
"""

query_pagos = """
SELECT `Fecha`, `Método de pago` AS metodo_pago, `Importe`
FROM `Pagos en Punto de venta (pos.payment)(1)`
WHERE `Fecha` >= '2025-01-01' AND `Fecha` < '2027-01-01'
"""

query_sesiones = """
SELECT `Abierta por` AS usuario, `Fecha de apertura`, `Fecha de cierre`
FROM `Sesión de Punto de venta (pos.session)`
WHERE `Fecha de apertura` IS NOT NULL
  AND `Fecha de cierre` IS NOT NULL
"""

with engine.connect() as conn:
    df_ordenes = pd.read_sql(text(query_ordenes), con=conn)
    df_pagos = pd.read_sql(text(query_pagos), con=conn)
    df_sesiones = pd.read_sql(text(query_sesiones), con=conn)

print(f"-> [UX App] Órdenes: {len(df_ordenes):,} | Pagos: {len(df_pagos):,} | Sesiones: {len(df_sesiones):,}")

# =============================================================================
# 3. LIMPIEZA Y PREPARACIÓN DE CADA CONJUNTO
# =============================================================================
# Órdenes 2026
df_ordenes['Importe'] = pd.to_numeric(df_ordenes['Total'], errors='coerce').fillna(0.0)
df_ordenes['Responsable'] = df_ordenes['Responsable'].fillna('Sin asignar').map(seudonimo)

# Pagos 2025-2026 (top 8 métodos + 'Otros métodos')
df_pagos['Fecha'] = pd.to_datetime(df_pagos['Fecha'], errors='coerce')
df_pagos['Importe'] = pd.to_numeric(df_pagos['Importe'], errors='coerce').fillna(0.0)
df_pagos['metodo_pago'] = df_pagos['metodo_pago'].fillna('Otro').map(seudonimo_metodo)
iso_pagos = df_pagos['Fecha'].dt.isocalendar()
df_pagos['Mes'] = df_pagos['Fecha'].dt.strftime('%Y-%m')
df_pagos['Trimestre'] = df_pagos['Fecha'].dt.year.astype(str) + '-Q' + df_pagos['Fecha'].dt.quarter.astype(str)
df_pagos['Semana'] = iso_pagos.year.astype(str) + '-W' + iso_pagos.week.astype(str).str.zfill(2)
df_pagos['Día'] = df_pagos['Fecha'].dt.strftime('%Y-%m-%d')
principales = df_pagos.groupby('metodo_pago')['Importe'].sum().nlargest(8).index
df_pagos['Método'] = df_pagos['metodo_pago'].where(df_pagos['metodo_pago'].isin(principales), 'Otros métodos')

# Sesiones: duración del turno, sin anomalías (< 30 min o > 24 h) ni usuarios del sistema
df_sesiones['Fecha de apertura'] = pd.to_datetime(df_sesiones['Fecha de apertura'], errors='coerce')
df_sesiones['Fecha de cierre'] = pd.to_datetime(df_sesiones['Fecha de cierre'], errors='coerce')
df_sesiones['Horas'] = (df_sesiones['Fecha de cierre'] - df_sesiones['Fecha de apertura']).dt.total_seconds() / 3600.0
df_sesiones = df_sesiones[df_sesiones['Horas'].between(0.5, 24.0)].copy()
df_sesiones = df_sesiones[~df_sesiones['usuario'].isin(['Buho PV', 'Caja PCD', 'Administrador'])]
df_sesiones['usuario'] = df_sesiones['usuario'].fillna('Sin asignar').map(seudonimo)
conteo = df_sesiones['usuario'].value_counts()
df_sesiones = df_sesiones[df_sesiones['usuario'].isin(conteo[conteo >= 10].index)]
iso_ses = df_sesiones['Fecha de apertura'].dt.isocalendar()
df_sesiones['Mes'] = df_sesiones['Fecha de apertura'].dt.strftime('%Y-%m')
df_sesiones['Semana'] = iso_ses.year.astype(str) + '-W' + iso_ses.week.astype(str).str.zfill(2)

# Métricas rápidas para contexto analítico
total_facturado_2026 = df_ordenes['Importe'].sum()
total_recaudado = df_pagos['Importe'].sum()
promedio_turno = df_sesiones['Horas'].mean()

# Paleta accesible de alta distinción cromática para modo oscuro
PALETA = [
    '#2dd4bf',  # Turquesa
    '#93a1f8',  # Indigo suave
    '#4ade80',  # Esmeralda menta
    '#fbbf24',  # Ámbar dorado
    '#f472b6',  # Rosa vibrante
    '#a78bfa',  # Violeta
    '#38bdf8',  # Cyan eléctrico
    '#fb923c',  # Naranja coral
    '#e879f9',  # Fucsia pastel
    '#60a5fa'   # Azul cielo
]

# Configuración visual común de las gráficas (Sin choques de fondo)
UX_CHART_THEME = dict(
    paper_bgcolor='#131a2a',
    plot_bgcolor='#131a2a',
    font=dict(color='#9aa5b8', family='-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', size=12),
    xaxis=dict(
        categoryorder='category ascending',
        gridcolor='#1e293b',
        showgrid=True,
        zerolinecolor='#334155',
        tickfont=dict(color='#cbd5e1')
    ),
    yaxis=dict(
        gridcolor='#1e293b',
        showgrid=True,
        zerolinecolor='#334155',
        tickfont=dict(color='#cbd5e1')
    ),
    legend=dict(
        font=dict(color="#e2e8f0", size=12),
        bgcolor='rgba(19, 26, 42, 0.8)',
        bordercolor='#334155',
        borderwidth=1
    ),
    hoverlabel=dict(
        bgcolor='#0c1322',
        bordercolor='#2dd4bf',
        font=dict(color='#f8fafc', size=13, family='Arial')
    ),
    margin=dict(l=70, r=40, t=70, b=70),
    height=560
)


def aplicar_tema(fig, titulo_x, titulo_y, titulo_leyenda, moneda=True):
    fig.update_layout(**UX_CHART_THEME)
    fig.update_layout(
        xaxis_title=f"<b>{titulo_x}</b>",
        yaxis_title=f"<b>{titulo_y}</b>",
        legend_title_text=f"<b>{titulo_leyenda}</b>",
        title_font=dict(color='#f8fafc', size=17)
    )
    if moneda:
        fig.update_yaxes(tickprefix='$', tickformat=',.0f')
    else:
        fig.update_yaxes(ticksuffix=' h')
    return fig


# =============================================================================
# 4. INICIALIZACIÓN DE LA APLICACIÓN DASH
# =============================================================================
app = Dash(
    __name__,
    title="Analytics POS | Dash + SQL",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
)

ESTILO_LABEL = {'color': '#f8fafc', 'fontWeight': '700', 'fontSize': '0.92rem', 'marginBottom': '8px', 'display': 'block'}
ESTILO_TARJETA = {'marginBottom': '24px'}


def metrica(etiqueta, valor, color='#2dd4bf', borde=True):
    return html.Div([
        html.Span(etiqueta, style={'fontSize': '0.75rem', 'color': '#9aa5b8', 'textTransform': 'uppercase', 'fontWeight': '600'}),
        html.Div(valor, style={'fontSize': '1.25rem', 'fontWeight': '800', 'color': color})
    ], style={'textAlign': 'right', 'padding': '0 16px', 'borderRight': '1px solid #334155' if borde else 'none'})


def tarjeta_grafica(numero, titulo, selector_id, opciones, grafica_id, query):
    return html.Div([
        html.H2(f"{numero}. {titulo}", style={'fontSize': '1.25rem', 'color': '#f8fafc', 'margin': '0 0 16px 0'}),
        html.Div([
            html.Div([
                html.Label("Granularidad temporal:", style=ESTILO_LABEL),
                dcc.Dropdown(id=selector_id, options=opciones, value=opciones[0]['value'], clearable=False)
            ], style={'flex': '1', 'minWidth': '280px'}),
            html.Pre(query.strip(), style={
                'backgroundColor': '#0c1322', 'border': '1px solid #1e293b', 'borderLeft': '4px solid #2dd4bf',
                'borderRadius': '8px', 'padding': '10px 14px', 'margin': '0', 'color': '#2dd4bf',
                'fontSize': '0.78rem', 'whiteSpace': 'pre-wrap', 'flex': '1', 'minWidth': '280px'
            })
        ], style={'display': 'flex', 'gap': '20px', 'flexWrap': 'wrap', 'alignItems': 'flex-start', 'marginBottom': '16px'}),
        dcc.Graph(id=grafica_id, config={'displayModeBar': True, 'displaylogo': False, 'responsive': True})
    ], className="ux-card", style=ESTILO_TARJETA)


# =============================================================================
# 5. LAYOUT CON ARQUITECTURA DE INFORMACIÓN Y ALTO CONTRASTE
# =============================================================================
app.layout = html.Div([
    # Encabezado
    html.Header([
        html.Div([
            html.Span(f"🟢 MOTOR ACTIVO: {db_status}", style={
                'fontSize': '0.72rem',
                'fontWeight': '700',
                'letterSpacing': '0.08em',
                'color': '#4ade80',
                'backgroundColor': 'rgba(34, 197, 94, 0.15)',
                'border': '1px solid rgba(34, 197, 94, 0.3)',
                'padding': '4px 10px',
                'borderRadius': '6px',
                'display': 'inline-block',
                'marginBottom': '8px'
            }),
            html.H1("Analítica de Punto de Venta", style={
                'fontSize': '2rem',
                'fontWeight': '800',
                'color': '#f8fafc',
                'margin': '0 0 8px 0',
                'letterSpacing': '-0.025em'
            }),
            html.P("Tres visualizaciones alimentadas por consultas SQL a la base de datos Viz2026", style={
                'fontSize': '0.95rem',
                'color': '#9aa5b8',
                'margin': '0'
            })
        ]),

        # Micro-tarjetas de métricas contextuales
        html.Div([
            metrica("Ventas 2026", f"${total_facturado_2026:,.0f}"),
            metrica("Pagos 2025–2026", f"${total_recaudado:,.0f}", color='#93a1f8'),
            metrica("Turno promedio", f"{promedio_turno:.1f} h", color='#f8fafc', borde=False)
        ], style={'display': 'flex', 'alignItems': 'center', 'flexWrap': 'wrap', 'rowGap': '12px'})

    ], style={
        'display': 'flex',
        'justifyContent': 'space-between',
        'alignItems': 'center',
        'flexWrap': 'wrap',
        'gap': '20px',
        'paddingBottom': '24px',
        'marginBottom': '24px',
        'borderBottom': '1px solid #1e293b'
    }),

    tarjeta_grafica(
        1, "Ventas 2026 por responsable", 'selector-ordenes',
        [{'label': '📅 Por mes', 'value': 'Mes'}, {'label': '📆 Por semana', 'value': 'Semana'}],
        'grafica-ordenes', query_ordenes
    ),
    tarjeta_grafica(
        2, "Pagos por método de pago (2025–2026)", 'selector-pagos',
        [{'label': '🗓️ Por mes', 'value': 'Mes'}, {'label': '📊 Por trimestre', 'value': 'Trimestre'},
         {'label': '📆 Por semana', 'value': 'Semana'}, {'label': '📅 Por día', 'value': 'Día'}],
        'grafica-pagos', query_pagos
    ),
    tarjeta_grafica(
        3, "Duración promedio de los turnos de caja", 'selector-sesiones',
        [{'label': '🗓️ Mensual (líneas)', 'value': 'Mes'}, {'label': '📆 Semanal (líneas)', 'value': 'Semana'},
         {'label': '📊 Mensual (barras)', 'value': 'Barras'}],
        'grafica-sesiones', query_sesiones
    )

], style={'padding': '32px 36px', 'maxWidth': '1440px', 'margin': '0 auto'})


# =============================================================================
# 6. CALLBACKS DE RENDERIZADO DINÁMICO
# =============================================================================
@app.callback(Output('grafica-ordenes', 'figure'), Input('selector-ordenes', 'value'))
def actualizar_ordenes(periodo):
    df = df_ordenes.groupby([periodo, 'Responsable'], as_index=False)['Importe'].sum()
    fig = px.bar(
        df, x=periodo, y='Importe', color='Responsable', barmode='group',
        title=f"<b>Importe total 2026 por {periodo.lower()} y responsable</b>",
        color_discrete_sequence=PALETA
    )
    fig.update_traces(hovertemplate="<b>%{data.name}</b><br>%{x}<br>Importe: $%{y:,.2f} MXN<extra></extra>")
    return aplicar_tema(fig, f"{periodo} (2026)", "Importe total ($ MXN)", "Responsable")


@app.callback(Output('grafica-pagos', 'figure'), Input('selector-pagos', 'value'))
def actualizar_pagos(periodo):
    df = df_pagos.groupby([periodo, 'Método'], as_index=False)['Importe'].sum()
    fig = px.bar(
        df, x=periodo, y='Importe', color='Método', barmode='stack',
        title=f"<b>Importe cobrado por {periodo.lower()} y método de pago</b>",
        color_discrete_sequence=PALETA
    )
    fig.update_traces(hovertemplate="<b>%{data.name}</b><br>%{x}<br>Importe: $%{y:,.2f} MXN<extra></extra>")
    return aplicar_tema(fig, f"{periodo} (2025–2026)", "Importe cobrado ($ MXN)", "Método de pago")


@app.callback(Output('grafica-sesiones', 'figure'), Input('selector-sesiones', 'value'))
def actualizar_sesiones(vista):
    periodo = 'Mes' if vista == 'Barras' else vista
    df = df_sesiones.groupby([periodo, 'usuario'], as_index=False)['Horas'].mean().round(2).sort_values(periodo)
    titulo = f"<b>Horas promedio por turno, por {periodo.lower()} y colaborador</b>"
    if vista == 'Barras':
        fig = px.bar(df, x=periodo, y='Horas', color='usuario', barmode='group', title=titulo, color_discrete_sequence=PALETA)
    else:
        fig = px.line(df, x=periodo, y='Horas', color='usuario', markers=True, title=titulo, color_discrete_sequence=PALETA)
    fig.update_traces(hovertemplate="<b>%{data.name}</b><br>%{x}<br>Promedio: %{y:.2f} h<extra></extra>")
    fig = aplicar_tema(fig, periodo, "Horas promedio por turno", "Colaborador", moneda=False)
    fig.update_yaxes(range=[0, 16])
    return fig


if __name__ == '__main__':
    app.run(debug=True)
