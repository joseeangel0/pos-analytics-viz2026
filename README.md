# 🧭 Analítica de Punto de Venta — Viz2026

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.1-D71F00?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Plotly](https://img.shields.io/badge/Plotly-7.1-3F4F75?logo=plotly&logoColor=white)](https://plotly.com/python/)
[![Dash](https://img.shields.io/badge/Dash-4.4-008DE4?logo=plotly&logoColor=white)](https://dash.plotly.com/)

Proyecto de visualización y modelado de información a partir de las exportaciones de un sistema POS (órdenes, pagos y sesiones de caja). Los archivos Excel se limpian con **pandas**, se cargan en **MySQL** a través de **SQLAlchemy** y se consultan con SQL para generar un dashboard en **Dash** y tres reportes HTML interactivos con **Plotly**.

> Si MySQL no está disponible, `db_config.py` usa automáticamente una base **SQLite** local (`Viz2026.db`), así que el proyecto también puede ejecutarse sin servidor.

---

## 🔄 Flujo de datos

```
Excel exportados del POS (.xlsx)
        │
        ▼
dataTransform.py  ──  limpieza, tipos numéricos, columnas de Año / Mes / Semana
        │
        ▼  SQLAlchemy + PyMySQL
Base de datos Viz2026  (MySQL 8.0, o SQLite como respaldo)
        │
        ├──► app.py               → Dashboard Dash con las 3 visualizaciones (http://127.0.0.1:8050)
        ├──► generar_html.py      → ordenes.html
        ├──► generar_pagos.py     → pagos.html
        └──► generar_sesiones.py  → sesiones.html
```

---

## 📈 Visualizaciones

Las tres visualizaciones están en el dashboard de **Dash** (`app.py`), cada una con su propia consulta SQL y un selector de granularidad. También se exportan como reportes HTML independientes para GitHub Pages.

| Archivo | Qué muestra | Tipo de gráfica | Vistas disponibles |
| :--- | :--- | :--- | :--- |
| `ordenes.html` | Importe vendido en 2026 por responsable | Barras agrupadas | Mes · Semana ISO |
| `pagos.html` | Importe cobrado por método de pago (2025–2026, top 8 + "Otros métodos") | Barras apiladas | Mes · Trimestre · Semana ISO · Día |
| `sesiones.html` | Duración promedio de los turnos de caja por colaborador (≥ 10 sesiones, turnos de 0.5 a 24 h) | Líneas y barras | Mensual (líneas) · Semanal (líneas) · Mensual (barras) |
| `index.html` | Portal de entrada para GitHub Pages con enlaces a los tres reportes | — | — |

> 🔒 **Privacidad:** los nombres de empleados se reemplazan por códigos (`Colaborador XXXX`, `Caja XXXX`) generados con una sal secreta (`ANON_SALT` en `.env`). Ningún nombre real se publica en los reportes.

---

## 📂 Estructura

```
├── assets/
│   └── style.css          # Estilos del dashboard Dash (tema oscuro turquesa)
├── .env.example           # Plantilla de variables de entorno
├── requirements.txt       # Dependencias fijadas
├── anonimizar.py          # Seudónimos para nombres de empleados
├── db_config.py           # Conexión SQLAlchemy (MySQL con respaldo SQLite)
├── dataTransform.py       # ETL: Excel → tablas en la base de datos
├── app.py                 # Dashboard Dash: 3 visualizaciones + consultas SQL
├── generar_html.py        # Genera ordenes.html
├── generar_pagos.py       # Genera pagos.html
├── generar_sesiones.py    # Genera sesiones.html
├── grafica_local.py       # Gráfica rápida leyendo el Excel directamente (sin BD)
├── index.html             # Portal principal
├── ordenes.html           # Reporte de órdenes
├── pagos.html             # Reporte de pagos
└── sesiones.html          # Reporte de sesiones
```

---

## ⚙️ Cómo ejecutarlo

**1. Clonar e instalar**

```bash
git clone https://github.com/<usuario>/<repositorio>.git
cd <repositorio>

python -m venv .venv
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

**2. Configurar el entorno**

Copia `.env.example` a `.env` y ajusta los valores:

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=tu_contraseña
MYSQL_DATABASE=Viz2026

# Carpeta donde están los Excel exportados del POS
DATA_DIR=./data
```

Si dejas `MYSQL_PASSWORD` vacío se usará SQLite.

**3. Cargar los datos**

Coloca en `DATA_DIR` los cuatro archivos exportados del POS (`pos.order`, `pos.payment`, `pos.session` y `report.pos.order`) y ejecuta:

```bash
python dataTransform.py
```

**4. Ver los resultados**

```bash
python app.py               # dashboard con las 3 gráficas en http://127.0.0.1:8050

python generar_html.py      # regenera ordenes.html
python generar_pagos.py     # regenera pagos.html
python generar_sesiones.py  # regenera sesiones.html
```

---

## 🌐 GitHub Pages

1. En el repositorio, entra a **Settings → Pages**.
2. En **Branch** elige `main` y la carpeta `/ (root)`, luego **Save**.
3. Tras unos minutos el portal queda disponible en `https://<usuario>.github.io/<repositorio>/`.
