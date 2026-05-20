"""
Creación y migración del esquema de base de datos SQLite.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "inventario.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def crear_tablas():
    conn = get_connection()
    cur = conn.cursor()

    # Categorías (incluye las personalizadas)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre      TEXT NOT NULL UNIQUE,
            predefinida INTEGER NOT NULL DEFAULT 0
        )
    """)

    # Productos / inventario
    cur.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            sku             TEXT NOT NULL UNIQUE,
            categoria_id    INTEGER NOT NULL REFERENCES categorias(id),
            modelo          TEXT NOT NULL,
            marca           TEXT NOT NULL,
            talla           TEXT,
            color           TEXT,
            precio_compra   REAL NOT NULL,
            precio_venta    REAL,
            estado          TEXT NOT NULL DEFAULT 'disponible'
                            CHECK(estado IN ('disponible','reservado','vendido')),
            canales         TEXT NOT NULL DEFAULT '[]',
            fecha_ingreso   TEXT NOT NULL,
            notas           TEXT,
            descripcion_ml  TEXT,
            precio_referencia REAL,
            CONSTRAINT precio_positivo CHECK(precio_compra > 0)
        )
    """)

    # Fotos asociadas a cada producto
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fotos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
            ruta        TEXT NOT NULL,
            orden       INTEGER NOT NULL DEFAULT 0
        )
    """)

    # Ventas
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id     INTEGER NOT NULL REFERENCES productos(id),
            precio_final    REAL NOT NULL,
            canal           TEXT NOT NULL,
            comision_pct    REAL NOT NULL DEFAULT 0,
            margen_neto     REAL,
            fecha_venta     TEXT NOT NULL,
            notas           TEXT
        )
    """)

    # Movimientos de caja
    cur.execute("""
        CREATE TABLE IF NOT EXISTS caja (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo        TEXT NOT NULL CHECK(tipo IN ('ingreso','egreso')),
            concepto    TEXT NOT NULL,
            monto       REAL NOT NULL,
            fecha       TEXT NOT NULL,
            referencia  TEXT
        )
    """)

    # Categorías predefinidas
    predefinidas = [("Tenis", 1), ("Ropa", 1), ("Accesorios", 1), ("Otros", 1)]
    cur.executemany(
        "INSERT OR IGNORE INTO categorias (nombre, predefinida) VALUES (?, ?)",
        predefinidas,
    )

    conn.commit()
    conn.close()
