from pathlib import Path
import pandas as pd
import plotly.express as px
from sqlalchemy import text
from anonimizar import seudonimo
from db_config import get_engine, DB_NAME
from dash import Dash, html, dcc, Input, Output

# =============================================================================
# 1. CONEXIÓN A BASE DE DATOS MEDIANTE SQLALCHEMY
# =============================================================================
engine = get_engine()
is_mysql = "mysql" in str(engine.url)
db_status = f"MySQL Server 8.0: {DB_NAME}" if is_mysql else f"SQLite Local: {DB_NAME}.db"
tabla_ordenes = "`Órdenes del Punto de venta (pos.order)(2)`" if is_mysql else '"Órdenes del Punto de venta (pos.order)(2)"'
col_anio = "`Año`" if is_mysql else '"Año"'
print(f"-> [UX App] Conectado a {db_status}.")

# Carga de datos filtrados mediante consulta SQL directa
query_sql = f"SELECT * FROM {tabla_ordenes} WHERE {col_anio} = 2026"
with engine.connect() as conn:
    df_2026 = pd.read_sql(text(query_sql), con=conn)

print(f"-> [UX App] {len(df_2026):,} registros cargados directamente desde la base de datos.")

# Normalización de importes y responsables
df_2026['Importe'] = pd.to_numeric(df_2026['Total'], errors='coerce').fillna(0.0)
df_2026['Responsable'] = df_2026['Responsable'].fillna('Sin asignar').map(seudonimo)

# Métricas rápidas para contexto analítico
total_facturado_2026 = df_2026['Importe'].sum()
total_tickets_2026 = len(df_2026)
total_colaboradores = df_2026['Responsable'].nunique()

# Paleta accesible de alta distinción cromática para modo oscuro
PALETA_RESPONSABLES = [
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

# Configuración visual de la gráfica integrada (Sin choques de fondo)
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
        tickfont=dict(color='#cbd5e1'),
        tickprefix='$',
        tickformat=',.0f'
    ),
    legend=dict(
        title=dict(text="<b>Responsable</b>", font=dict(color="#f8fafc", size=13)),
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
    margin=dict(l=70, r=40, t=70, b=70)
)

# =============================================================================
# 2. INICIALIZACIÓN DE LA APLICACIÓN DASH
# =============================================================================
app = Dash(
    __name__,
    title="Analytics POS 2026 | MySQL Engine",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
)

# =============================================================================
# 3. LAYOUT CON ARQUITECTURA DE INFORMACIÓN Y ALTO CONTRASTE
# =============================================================================
app.layout = html.Div([
    # Encabezado
    html.Header([
        html.Div([
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
            ]),
            html.H1("Reporte de Ventas por Responsable", style={
                'fontSize': '2rem',
                'fontWeight': '800',
                'color': '#f8fafc',
                'margin': '0 0 8px 0',
                'letterSpacing': '-0.025em'
            }),
            html.P("Consultando en tiempo real la tabla 'órdenes del punto de venta (pos.order)(2)' en Viz2026", style={
                'fontSize': '0.95rem',
                'color': '#9aa5b8',
                'margin': '0'
            })
        ]),

        # Micro-tarjetas de métricas contextuales
        html.Div([
            html.Div([
                html.Span("Facturación 2026", style={'fontSize': '0.75rem', 'color': '#9aa5b8', 'textTransform': 'uppercase', 'fontWeight': '600'}),
                html.Div(f"${total_facturado_2026:,.2f} MXN", style={'fontSize': '1.25rem', 'fontWeight': '800', 'color': '#2dd4bf'})
            ], style={'textAlign': 'right', 'padding': '0 16px', 'borderRight': '1px solid #334155'}),

            html.Div([
                html.Span("Registros SQL", style={'fontSize': '0.75rem', 'color': '#9aa5b8', 'textTransform': 'uppercase', 'fontWeight': '600'}),
                html.Div(f"{total_tickets_2026:,}", style={'fontSize': '1.25rem', 'fontWeight': '800', 'color': '#f8fafc'})
            ], style={'textAlign': 'right', 'paddingLeft': '16px'})
        ], style={'display': 'flex', 'alignItems': 'center'})

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

    # Barra de Control y Selector Temporal
    html.Div([
        html.Div([
            html.Label("Granularidad Temporal:", style={
                'color': '#f8fafc',
                'fontWeight': '700',
                'fontSize': '0.92rem',
                'marginBottom': '8px',
                'display': 'flex',
                'alignItems': 'center',
                'gap': '8px'
            }),
            dcc.Dropdown(
                id='selector-temporal',
                options=[
                    {'label': '📅 Agrupación por Mes (Enero — Septiembre 2026)', 'value': 'mes'},
                    {'label': '📆 Agrupación por Semana (Semana 01 — Semana 40)', 'value': 'semana'}
                ],
                value='mes',
                clearable=False,
                style={'width': '100%'}
            )
        ], style={'flex': '1', 'minWidth': '300px'}),

        html.Div([
            html.Span("⚡ Motor de Datos:", style={'fontWeight': '600', 'color': '#e2e8f0', 'display': 'block', 'fontSize': '0.85rem', 'marginBottom': '4px'}),
            html.Span(
                "Base de datos 'Viz2026' conectada con SQLAlchemy. Datos transformados con dataTransform.py.",
                style={'color': '#9aa5b8', 'fontSize': '0.85rem', 'lineHeight': '1.4'}
            )
        ], style={
            'backgroundColor': '#0c1322',
            'border': '1px solid #1e293b',
            'borderRadius': '10px',
            'padding': '12px 16px',
            'maxWidth': '460px'
        })

    ], className="ux-card", style={
        'display': 'flex',
        'justifyContent': 'space-between',
        'alignItems': 'center',
        'flexWrap': 'wrap',
        'gap': '20px',
        'marginBottom': '24px'
    }),

    # Contenedor Principal de la Gráfica
    html.Div([
        dcc.Graph(
            id='grafica-barras-agrupadas',
            config={'displayModeBar': True, 'displaylogo': False, 'responsive': True}
        )
    ], className="ux-card")

], style={'padding': '32px 36px', 'maxWidth': '1440px', 'margin': '0 auto'})


# =============================================================================
# 4. CALLBACK DE RENDERIZADO DINÁMICO
# =============================================================================
@app.callback(
    Output('grafica-barras-agrupadas', 'figure'),
    Input('selector-temporal', 'value')
)
def actualizar_grafica(tipo_agrupacion):
    if tipo_agrupacion == 'mes':
        df_agrupado = df_2026.groupby(['Mes', 'Responsable'], as_index=False)['Importe'].sum()
        
        fig = px.bar(
            df_agrupado,
            x='Mes',
            y='Importe',
            color='Responsable',
            barmode='group',
            title="<b>Importe Total 2026 Agrupado por Mes y Responsable</b>",
            labels={
                'Importe': 'Importe Total ($ MXN)',
                'Mes': 'Mes (Año 2026)',
                'Responsable': 'Colaborador'
            },
            color_discrete_sequence=PALETA_RESPONSABLES
        )
        
        fig.update_traces(
            hovertemplate="<b>%{data.name}</b><br>Mes: %{x}<br>Importe: $%{y:,.2f} MXN<extra></extra>"
        )

        fig.update_layout(
            **UX_CHART_THEME,
            xaxis_title="<b>Mes del Año (2026)</b>",
            yaxis_title="<b>Importe Total Facturado ($ MXN)</b>",
            bargap=0.18,
            bargroupgap=0.06,
            height=640
        )

    else:
        df_agrupado = df_2026.groupby(['Semana', 'Responsable'], as_index=False)['Importe'].sum()
        
        fig = px.bar(
            df_agrupado,
            x='Semana',
            y='Importe',
            color='Responsable',
            barmode='group',
            title="<b>Importe Total 2026 Agrupado por Semana y Responsable (Sem 01 — Sem 40)</b>",
            labels={
                'Importe': 'Importe Total ($ MXN)',
                'Semana': 'Semana del Año (2026)',
                'Responsable': 'Colaborador'
            },
            color_discrete_sequence=PALETA_RESPONSABLES
        )

        fig.update_traces(
            hovertemplate="<b>%{data.name}</b><br>Semana: %{x}<br>Importe: $%{y:,.2f} MXN<extra></extra>"
        )

        fig.update_layout(
            **UX_CHART_THEME,
            xaxis_title="<b>Semana del Año (2026)</b>",
            yaxis_title="<b>Importe Total Facturado ($ MXN)</b>",
            bargap=0.12,
            bargroupgap=0.03,
            height=640
        )

    return fig


if __name__ == '__main__':
    app.run(debug=True)
