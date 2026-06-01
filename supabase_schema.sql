-- ═══════════════════════════════════════════════════════════
-- ESQUEMA para Supabase – Inventario Reventa
-- Copiar y ejecutar en: Supabase Dashboard → SQL Editor → New Query
-- ═══════════════════════════════════════════════════════════

-- CATEGORÍAS
CREATE TABLE IF NOT EXISTS categorias (
    id          SERIAL PRIMARY KEY,
    nombre      TEXT NOT NULL UNIQUE,
    predefinida INTEGER NOT NULL DEFAULT 0
);
INSERT INTO categorias (nombre, predefinida) VALUES
    ('Tenis', 1), ('Ropa', 1), ('Accesorios', 1), ('Otros', 1)
ON CONFLICT (nombre) DO NOTHING;

-- PRODUCTOS
CREATE TABLE IF NOT EXISTS productos (
    id                SERIAL PRIMARY KEY,
    sku               TEXT NOT NULL UNIQUE,
    categoria_id      INTEGER NOT NULL REFERENCES categorias(id),
    modelo            TEXT NOT NULL,
    marca             TEXT NOT NULL,
    talla             TEXT,
    color             TEXT,
    precio_compra     REAL NOT NULL CHECK(precio_compra > 0),
    precio_venta      REAL,
    estado            TEXT NOT NULL DEFAULT 'disponible'
                      CHECK(estado IN ('disponible','reservado','vendido')),
    canales           TEXT NOT NULL DEFAULT '[]',
    fecha_ingreso     TEXT NOT NULL,
    notas             TEXT,
    descripcion_ml    TEXT,
    precio_referencia REAL
);

-- FOTOS
CREATE TABLE IF NOT EXISTS fotos (
    id          SERIAL PRIMARY KEY,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    ruta        TEXT NOT NULL,
    orden       INTEGER NOT NULL DEFAULT 0
);

-- VENTAS
CREATE TABLE IF NOT EXISTS ventas (
    id            SERIAL PRIMARY KEY,
    producto_id   INTEGER NOT NULL REFERENCES productos(id),
    precio_final  REAL NOT NULL,
    canal         TEXT NOT NULL,
    comision_pct  REAL NOT NULL DEFAULT 0,
    comision_fija REAL NOT NULL DEFAULT 0,
    costo_envio   REAL NOT NULL DEFAULT 0,
    margen_neto   REAL,
    fecha_venta   TEXT NOT NULL,
    notas         TEXT
);

-- CAJA
CREATE TABLE IF NOT EXISTS caja (
    id          SERIAL PRIMARY KEY,
    tipo        TEXT NOT NULL CHECK(tipo IN ('ingreso','egreso')),
    concepto    TEXT NOT NULL,
    monto       REAL NOT NULL,
    fecha       TEXT NOT NULL,
    referencia  TEXT
);
