import os
import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import text
from db_config import get_engine, get_server_engine, DB_NAME, DB_HOST, DB_PORT

# =============================================================================
# CONFIGURACIÓN DE CONEXIÓN
# =============================================================================
DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).parent / "data"))

# =============================================================================
# FUNCIONES MODULARES DE TRANSFORMACIÓN
# =============================================================================
def transformar_ordenes(ruta_archivo: Path) -> pd.DataFrame:
    """Limpia y transforma los datos de órdenes de venta (pos.order)."""
    print(f"-> Procesando: {ruta_archivo.name}")
    df = pd.read_excel(ruta_archivo)
    
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0.0)
    df['Responsable'] = df['Responsable'].fillna('Sin asignar')
    
    meses_es = {
        1: '01. Enero', 2: '02. Febrero', 3: '03. Marzo', 4: '04. Abril',
        5: '05. Mayo', 6: '06. Junio', 7: '07. Julio', 8: '08. Agosto',
        9: '09. Septiembre', 10: '10. Octubre', 11: '11. Noviembre', 12: '12. Diciembre'
    }
    df['Año'] = df['Fecha'].dt.year
    df['Mes'] = df['Fecha'].dt.month.map(meses_es)
    df['Semana_Num'] = df['Fecha'].dt.isocalendar().week
    df['Semana'] = 'Sem ' + df['Semana_Num'].astype(str).str.zfill(2)
    return df


def transformar_pagos(ruta_archivo: Path) -> pd.DataFrame:
    """Limpia y normaliza los pagos (pos.payment)."""
    print(f"-> Procesando: {ruta_archivo.name}")
    df = pd.read_excel(ruta_archivo)
    df = df.dropna(subset=['Método de pago']).copy()
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    df['Importe'] = pd.to_numeric(df['Importe'], errors='coerce').fillna(0.0)
    return df


def transformar_sesiones(ruta_archivo: Path) -> pd.DataFrame:
    """Limpia turnos de caja y balances (pos.session)."""
    print(f"-> Procesando: {ruta_archivo.name}")
    df = pd.read_excel(ruta_archivo)
    df['Fecha de apertura'] = pd.to_datetime(df['Fecha de apertura'], errors='coerce')
    df['Fecha de cierre'] = pd.to_datetime(df['Fecha de cierre'], errors='coerce')
    for col in ['Balance inicial', 'Balance final', 'Balance de cierre teórico']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    return df


def transformar_reporte(ruta_archivo: Path) -> pd.DataFrame:
    """Normaliza la tabla dinámica de categorías de producto (report.pos.order)."""
    print(f"-> Procesando: {ruta_archivo.name}")
    df = pd.read_excel(ruta_archivo)
    columnas_limpias = []
    for i, col in enumerate(df.columns):
        nombre = str(col).strip()
        if not nombre or nombre.startswith('Unnamed:'):
            columnas_limpias.append(f"col_{i}")
        else:
            columnas_limpias.append(f"{nombre}_{i}")
    df.columns = columnas_limpias
    return df


# =============================================================================
# PIPELINE DE INGESTA CON SQLALCHEMY
# =============================================================================
def ejecutar_pipeline(password: str = None):
    if password:
        os.environ["MYSQL_PASSWORD"] = password

    # 1. Conexión y aseguramiento de la Base de Datos
    print(f"-> Verificando servidor MySQL ({DB_HOST}:{DB_PORT})...")
    engine_server = get_server_engine()
    try:
        with engine_server.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4;"))
            conn.commit()
        print(f"[OK] Base de datos `{DB_NAME}` lista y configurada.")
    except Exception:
        print(f"-> Usando base de datos `{DB_NAME}`.")

    # 2. Conexión a la base de datos
    engine = get_engine()

    # 3. Procesamiento y carga de archivos en tablas con el mismo nombre
    archivos_config = [
        {
            "archivo": "Órdenes del Punto de venta (pos.order)(2).xlsx",
            "transform_fn": transformar_ordenes,
            "tabla": "Órdenes del Punto de venta (pos.order)(2)"
        },
        {
            "archivo": "Pagos en Punto de venta (pos.payment)(1).xlsx",
            "transform_fn": transformar_pagos,
            "tabla": "Pagos en Punto de venta (pos.payment)(1)"
        },
        {
            "archivo": "Sesión de Punto de venta (pos.session).xlsx",
            "transform_fn": transformar_sesiones,
            "tabla": "Sesión de Punto de venta (pos.session)"
        },
        {
            "archivo": "Tabla dinámica Análisis de Punto de venta (report.pos.order)(4).xlsx",
            "transform_fn": transformar_reporte,
            "tabla": "Tabla dinámica Análisis de Punto de venta (report.pos.order)(4)"
        }
    ]

    print("\n=======================================================")
    print(f"  CARGANDO ARCHIVOS EN MYSQL [{DB_NAME}] CON SQLALCHEMY")
    print("=======================================================")

    for item in archivos_config:
        ruta = DATA_DIR / item["archivo"]
        if not ruta.exists():
            print(f"[ALERTA] Archivo no encontrado: {ruta}")
            continue

        df_transformado = item["transform_fn"](ruta)
        nombre_tabla = item["tabla"]
        
        print(f"-> Guardando en tabla MySQL: `{nombre_tabla}` ({len(df_transformado):,} filas)...")
        df_transformado.to_sql(
            name=nombre_tabla,
            con=engine,
            if_exists='replace',
            index=False,
            chunksize=2000
        )
        print(f"   [OK] Tabla `{nombre_tabla}` guardada exitosamente en MySQL.\n")

    print("=======================================================")
    print(f"¡Ingesta Exitosa! Base de Datos `{DB_NAME}` disponible en MySQL.")
    print("=======================================================\n")
    return engine


if __name__ == "__main__":
    pwd_input = sys.argv[1] if len(sys.argv) > 1 else None
    ejecutar_pipeline(pwd_input)
