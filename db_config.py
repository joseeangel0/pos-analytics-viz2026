import os
from pathlib import Path
from sqlalchemy import create_engine, text

# Cargar variables desde archivo .env local si existe
ENV_PATH = Path(__file__).parent / ".env"
if ENV_PATH.exists():
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

DB_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("MYSQL_PORT", 3306))
DB_USER = os.getenv("MYSQL_USER", "root")
DB_PASS = os.getenv("MYSQL_PASSWORD", "")
DB_NAME = os.getenv("MYSQL_DATABASE", "Viz2026")

SQLITE_PATH = Path(__file__).parent / f"{DB_NAME}.db"


def get_engine(db_name: str = DB_NAME):
    """
    Crea y retorna un Engine de SQLAlchemy.
    Prioriza MySQL 8.0 utilizando las credenciales de variables de entorno / .env.
    Si MySQL no responde, conmuta de forma segura al motor SQLite local.
    """
    if DB_PASS:
        try:
            url = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{db_name}"
            engine = create_engine(url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1;"))
            return engine
        except Exception:
            pass

    # Fallback seguro a SQLite
    return create_engine(f"sqlite:///{SQLITE_PATH}")


def get_server_engine():
    """Engine de conexión al servidor MySQL sin seleccionar base de datos (para crearla si no existe)."""
    if DB_PASS:
        try:
            url = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/"
            engine = create_engine(url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1;"))
            return engine
        except Exception:
            pass
    return create_engine(f"sqlite:///{SQLITE_PATH}")
