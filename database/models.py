"""
Funciones CRUD para todas las entidades de la app.
Cada función recibe parámetros explícitos y retorna dicts o listas de dicts.
"""
import json
from datetime import datetime
from typing import Optional
from .schema import get_connection
from utils.sku import generar_sku


# ─── CATEGORÍAS ──────────────────────────────────────────────────────────────

def listar_categorias() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM categorias ORDER BY nombre").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def crear_categoria(nombre: str) -> dict:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO categorias (nombre, predefinida) VALUES (?, 0)", (nombre.strip(),)
    )
    conn.commit()
    cat = conn.execute("SELECT * FROM categorias WHERE id=?", (cur.lastrowid,)).fetchone()
    conn.close()
    return dict(cat)


# ─── PRODUCTOS ───────────────────────────────────────────────────────────────

def crear_producto(
    categoria_id: int,
    modelo: str,
    marca: str,
    precio_compra: float,
    talla: str = "",
    color: str = "",
    precio_venta: Optional[float] = None,
    canales: list[str] = None,
    notas: str = "",
    descripcion_ml: str = "",
    precio_referencia: Optional[float] = None,
) -> dict:
    sku = generar_sku(marca, modelo, talla)
    fecha = datetime.now().strftime("%Y-%m-%d")
    canales_json = json.dumps(canales or [])

    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO productos
            (sku, categoria_id, modelo, marca, talla, color,
             precio_compra, precio_venta, canales, fecha_ingreso,
             notas, descripcion_ml, precio_referencia)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            sku, categoria_id, modelo.strip(), marca.strip(),
            talla.strip(), color.strip(), precio_compra, precio_venta,
            canales_json, fecha, notas, descripcion_ml, precio_referencia,
        ),
    )
    conn.commit()
    producto = conn.execute(
        "SELECT * FROM productos WHERE id=?", (cur.lastrowid,)
    ).fetchone()
    conn.close()
    return _producto_dict(producto)


def obtener_producto(producto_id: int) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM productos WHERE id=?", (producto_id,)).fetchone()
    conn.close()
    return _producto_dict(row) if row else None


def listar_productos(
    estado: Optional[str] = None,
    categoria_id: Optional[int] = None,
    busqueda: str = "",
) -> list[dict]:
    sql = """
        SELECT p.*, c.nombre AS categoria_nombre
        FROM productos p
        JOIN categorias c ON p.categoria_id = c.id
        WHERE 1=1
    """
    params = []
    if estado:
        sql += " AND p.estado = ?"
        params.append(estado)
    if categoria_id:
        sql += " AND p.categoria_id = ?"
        params.append(categoria_id)
    if busqueda:
        sql += " AND (p.modelo LIKE ? OR p.marca LIKE ? OR p.sku LIKE ?)"
        like = f"%{busqueda}%"
        params.extend([like, like, like])
    sql += " ORDER BY p.fecha_ingreso DESC, p.id DESC"

    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [_producto_dict(r) for r in rows]


def actualizar_producto(producto_id: int, **campos) -> dict:
    if "canales" in campos and isinstance(campos["canales"], list):
        campos["canales"] = json.dumps(campos["canales"])

    sets = ", ".join(f"{k}=?" for k in campos)
    valores = list(campos.values()) + [producto_id]
    conn = get_connection()
    conn.execute(f"UPDATE productos SET {sets} WHERE id=?", valores)
    conn.commit()
    row = conn.execute("SELECT * FROM productos WHERE id=?", (producto_id,)).fetchone()
    conn.close()
    return _producto_dict(row)


def eliminar_producto(producto_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM productos WHERE id=?", (producto_id,))
    conn.commit()
    conn.close()


def _producto_dict(row) -> dict:
    if row is None:
        return {}
    d = dict(row)
    try:
        d["canales"] = json.loads(d.get("canales") or "[]")
    except (json.JSONDecodeError, TypeError):
        d["canales"] = []
    return d


# ─── FOTOS ───────────────────────────────────────────────────────────────────

def agregar_foto(producto_id: int, ruta: str, orden: int = 0):
    conn = get_connection()
    conn.execute(
        "INSERT INTO fotos (producto_id, ruta, orden) VALUES (?,?,?)",
        (producto_id, ruta, orden),
    )
    conn.commit()
    conn.close()


def listar_fotos(producto_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM fotos WHERE producto_id=? ORDER BY orden", (producto_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def eliminar_foto(foto_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM fotos WHERE id=?", (foto_id,))
    conn.commit()
    conn.close()


# ─── VENTAS ──────────────────────────────────────────────────────────────────

COMISIONES = {
    "MercadoLibre": 0.14,
    "Instagram":    0.0,
    "Facebook":     0.0,
    "Efectivo":     0.0,
    "Otro":         0.0,
}


def registrar_venta(
    producto_id: int,
    precio_final: float,
    canal: str,
    comision_pct: Optional[float] = None,
    notas: str = "",
) -> dict:
    if comision_pct is None:
        comision_pct = COMISIONES.get(canal, 0.0)

    producto = obtener_producto(producto_id)
    precio_compra = producto["precio_compra"] if producto else 0
    comision_monto = precio_final * comision_pct
    margen_neto = precio_final - comision_monto - precio_compra

    fecha = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO ventas
            (producto_id, precio_final, canal, comision_pct, margen_neto, fecha_venta, notas)
        VALUES (?,?,?,?,?,?,?)
        """,
        (producto_id, precio_final, canal, comision_pct, margen_neto, fecha, notas),
    )
    venta_id = cur.lastrowid

    # Marcar producto como vendido
    conn.execute(
        "UPDATE productos SET estado='vendido' WHERE id=?", (producto_id,)
    )

    # Registrar en caja: ingreso por venta
    conn.execute(
        """
        INSERT INTO caja (tipo, concepto, monto, fecha, referencia)
        VALUES ('ingreso', ?, ?, ?, ?)
        """,
        (
            f"Venta {producto['marca']} {producto['modelo']} – {canal}",
            precio_final - comision_monto,
            fecha,
            f"venta:{venta_id}",
        ),
    )
    conn.commit()
    venta = conn.execute("SELECT * FROM ventas WHERE id=?", (venta_id,)).fetchone()
    conn.close()
    return dict(venta)


def listar_ventas(limite: int = 200) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT v.*, p.marca, p.modelo, p.talla, p.sku, p.precio_compra
        FROM ventas v
        JOIN productos p ON v.producto_id = p.id
        ORDER BY v.fecha_venta DESC
        LIMIT ?
        """,
        (limite,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── CAJA ────────────────────────────────────────────────────────────────────

def registrar_movimiento_caja(
    tipo: str, concepto: str, monto: float, referencia: str = ""
):
    fecha = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    conn.execute(
        "INSERT INTO caja (tipo, concepto, monto, fecha, referencia) VALUES (?,?,?,?,?)",
        (tipo, concepto, monto, fecha, referencia),
    )
    conn.commit()
    conn.close()


def resumen_caja() -> dict:
    conn = get_connection()
    rows = conn.execute("SELECT tipo, SUM(monto) as total FROM caja GROUP BY tipo").fetchall()
    conn.close()
    totales = {r["tipo"]: r["total"] for r in rows}
    ingresos = totales.get("ingreso", 0) or 0
    egresos = totales.get("egreso", 0) or 0
    return {
        "ingresos_totales": ingresos,
        "egresos_totales": egresos,
        "saldo_disponible": ingresos - egresos,
    }


def listar_movimientos_caja(limite: int = 100) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM caja ORDER BY fecha DESC, id DESC LIMIT ?", (limite,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── MÉTRICAS (dashboard) ────────────────────────────────────────────────────

def metricas_dashboard() -> dict:
    conn = get_connection()

    total_productos = conn.execute(
        "SELECT COUNT(*) FROM productos WHERE estado != 'vendido'"
    ).fetchone()[0]

    valor_stock = conn.execute(
        "SELECT SUM(precio_compra) FROM productos WHERE estado='disponible'"
    ).fetchone()[0] or 0

    ventas_mes = conn.execute(
        """
        SELECT COUNT(*) as unidades, SUM(margen_neto) as margen, SUM(precio_final) as ingresos
        FROM ventas
        WHERE strftime('%Y-%m', fecha_venta) = strftime('%Y-%m', 'now')
        """
    ).fetchone()

    margen_promedio = conn.execute(
        "SELECT AVG(margen_neto) FROM ventas"
    ).fetchone()[0] or 0

    dias_promedio = conn.execute(
        """
        SELECT AVG(julianday(v.fecha_venta) - julianday(p.fecha_ingreso))
        FROM ventas v
        JOIN productos p ON v.producto_id = p.id
        """
    ).fetchone()[0] or 0

    ventas_por_canal = conn.execute(
        "SELECT canal, COUNT(*) as total FROM ventas GROUP BY canal"
    ).fetchall()

    conn.close()

    return {
        "productos_activos": total_productos,
        "valor_stock": valor_stock,
        "ventas_mes_unidades": ventas_mes["unidades"] or 0,
        "ventas_mes_ingresos": ventas_mes["ingresos"] or 0,
        "ventas_mes_margen": ventas_mes["margen"] or 0,
        "margen_promedio": margen_promedio,
        "dias_promedio_inventario": round(dias_promedio, 1),
        "ventas_por_canal": {r["canal"]: r["total"] for r in ventas_por_canal},
    }
