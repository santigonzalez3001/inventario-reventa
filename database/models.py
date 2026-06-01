"""
CRUD para todas las entidades usando Supabase (PostgreSQL).
Las firmas de las funciones son idénticas a la versión SQLite para que
las páginas no necesiten cambios.
"""
import json
from collections import Counter
from datetime import datetime, date
from typing import Optional

from .supabase_client import get_supabase
from utils.sku import generar_sku


# ─── CATEGORÍAS ──────────────────────────────────────────────────────────────

def listar_categorias() -> list[dict]:
    sb = get_supabase()
    resp = sb.table("categorias").select("*").order("nombre").execute()
    return resp.data


def crear_categoria(nombre: str) -> dict:
    sb = get_supabase()
    resp = sb.table("categorias").insert({"nombre": nombre.strip(), "predefinida": 0}).execute()
    return resp.data[0]


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
    sb = get_supabase()
    resp = sb.table("productos").insert({
        "sku": sku,
        "categoria_id": categoria_id,
        "modelo": modelo.strip(),
        "marca": marca.strip(),
        "talla": talla.strip(),
        "color": color.strip(),
        "precio_compra": precio_compra,
        "precio_venta": precio_venta,
        "canales": json.dumps(canales or []),
        "fecha_ingreso": fecha,
        "notas": notas,
        "descripcion_ml": descripcion_ml,
        "precio_referencia": precio_referencia,
    }).execute()
    return _producto_dict(resp.data[0])


def obtener_producto(producto_id: int) -> Optional[dict]:
    sb = get_supabase()
    resp = sb.table("productos").select("*").eq("id", producto_id).execute()
    return _producto_dict(resp.data[0]) if resp.data else None


def listar_productos(
    estado: Optional[str] = None,
    categoria_id: Optional[int] = None,
    busqueda: str = "",
) -> list[dict]:
    sb = get_supabase()
    query = sb.table("productos").select("*, categorias(nombre)")
    if estado:
        query = query.eq("estado", estado)
    if categoria_id:
        query = query.eq("categoria_id", categoria_id)
    if busqueda:
        query = query.or_(
            f"modelo.ilike.%{busqueda}%,marca.ilike.%{busqueda}%,sku.ilike.%{busqueda}%"
        )
    query = query.order("fecha_ingreso", desc=True).order("id", desc=True)
    resp = query.execute()

    result = []
    for row in resp.data:
        d = dict(row)
        cat = d.pop("categorias", None) or {}
        d["categoria_nombre"] = cat.get("nombre", "")
        result.append(_producto_dict(d))
    return result


def actualizar_producto(producto_id: int, **campos) -> dict:
    if "canales" in campos and isinstance(campos["canales"], list):
        campos["canales"] = json.dumps(campos["canales"])
    sb = get_supabase()
    resp = sb.table("productos").update(campos).eq("id", producto_id).execute()
    return _producto_dict(resp.data[0])


def eliminar_producto(producto_id: int):
    sb = get_supabase()
    sb.table("ventas").delete().eq("producto_id", producto_id).execute()
    sb.table("productos").delete().eq("id", producto_id).execute()


def _producto_dict(row: dict) -> dict:
    if not row:
        return {}
    d = dict(row)
    try:
        d["canales"] = json.loads(d.get("canales") or "[]")
    except (json.JSONDecodeError, TypeError):
        d["canales"] = []
    return d


# ─── FOTOS ───────────────────────────────────────────────────────────────────

def agregar_foto(producto_id: int, ruta: str, orden: int = 0):
    sb = get_supabase()
    sb.table("fotos").insert({
        "producto_id": producto_id,
        "ruta": ruta,
        "orden": orden,
    }).execute()


def listar_fotos(producto_id: int) -> list[dict]:
    sb = get_supabase()
    resp = (
        sb.table("fotos")
        .select("*")
        .eq("producto_id", producto_id)
        .order("orden")
        .execute()
    )
    return resp.data


def eliminar_foto(foto_id: int):
    sb = get_supabase()
    sb.table("fotos").delete().eq("id", foto_id).execute()


# ─── VENTAS ──────────────────────────────────────────────────────────────────

COMISIONES = {
    "MercadoLibre": 0.16,   # ~16 % para tenis/ropa (rango real: 8 %–22 %)
    "Instagram":    0.0,
    "Facebook":     0.0,
    "Efectivo":     0.0,
    "Otro":         0.0,
}


def comision_fija_ml(precio: float) -> float:
    """Cargo fijo de MercadoLibre Colombia por unidad vendida (2025)."""
    if precio <= 30_000:
        return 2_500
    if precio <= 60_000:
        return 4_000
    return 0


def registrar_venta(
    producto_id: int,
    precio_final: float,
    canal: str,
    comision_pct: Optional[float] = None,
    costo_envio: float = 0.0,
    notas: str = "",
) -> dict:
    if comision_pct is None:
        comision_pct = COMISIONES.get(canal, 0.0)

    fija = comision_fija_ml(precio_final) if canal == "MercadoLibre" else 0.0
    producto = obtener_producto(producto_id)
    precio_compra = producto["precio_compra"] if producto else 0
    comision_monto = precio_final * comision_pct
    margen_neto = precio_final - comision_monto - fija - costo_envio - precio_compra
    fecha = datetime.now().strftime("%Y-%m-%d")

    sb = get_supabase()
    resp = sb.table("ventas").insert({
        "producto_id": producto_id,
        "precio_final": precio_final,
        "canal": canal,
        "comision_pct": comision_pct,
        "comision_fija": fija,
        "costo_envio": costo_envio,
        "margen_neto": margen_neto,
        "fecha_venta": fecha,
        "notas": notas,
    }).execute()
    venta = resp.data[0]

    sb.table("productos").update({"estado": "vendido"}).eq("id", producto_id).execute()
    sb.table("caja").insert({
        "tipo": "ingreso",
        "concepto": f"Venta {producto['marca']} {producto['modelo']} – {canal}",
        "monto": precio_final - comision_monto - fija,
        "fecha": fecha,
        "referencia": f"venta:{venta['id']}",
    }).execute()

    return venta


def listar_ventas(limite: int = 200) -> list[dict]:
    sb = get_supabase()
    resp = (
        sb.table("ventas")
        .select("*, productos(marca, modelo, talla, sku, precio_compra)")
        .order("fecha_venta", desc=True)
        .limit(limite)
        .execute()
    )
    result = []
    for row in resp.data:
        d = dict(row)
        prod_info = d.pop("productos", None) or {}
        d.update(prod_info)
        result.append(d)
    return result


# ─── CAJA ────────────────────────────────────────────────────────────────────

def registrar_movimiento_caja(
    tipo: str, concepto: str, monto: float, referencia: str = ""
):
    fecha = datetime.now().strftime("%Y-%m-%d")
    sb = get_supabase()
    sb.table("caja").insert({
        "tipo": tipo,
        "concepto": concepto,
        "monto": monto,
        "fecha": fecha,
        "referencia": referencia,
    }).execute()


def resumen_caja() -> dict:
    sb = get_supabase()
    resp = sb.table("caja").select("tipo, monto").execute()
    ingresos = sum(r["monto"] for r in resp.data if r["tipo"] == "ingreso")
    egresos  = sum(r["monto"] for r in resp.data if r["tipo"] == "egreso")
    return {
        "ingresos_totales": ingresos,
        "egresos_totales": egresos,
        "saldo_disponible": ingresos - egresos,
    }


def listar_movimientos_caja(limite: int = 100) -> list[dict]:
    sb = get_supabase()
    resp = (
        sb.table("caja")
        .select("*")
        .order("fecha", desc=True)
        .order("id", desc=True)
        .limit(limite)
        .execute()
    )
    return resp.data


# ─── MÉTRICAS (dashboard) ────────────────────────────────────────────────────

def metricas_dashboard() -> dict:
    sb = get_supabase()
    mes_actual = datetime.now().strftime("%Y-%m")

    prods = sb.table("productos").select("estado, precio_compra").execute().data
    total_productos = sum(1 for p in prods if p["estado"] != "vendido")
    valor_stock     = sum(p["precio_compra"] for p in prods if p["estado"] == "disponible")

    ventas_mes = (
        sb.table("ventas")
        .select("margen_neto, precio_final")
        .gte("fecha_venta", f"{mes_actual}-01")
        .execute()
        .data
    )
    ventas_mes_unidades = len(ventas_mes)
    ventas_mes_ingresos = sum(v["precio_final"]  for v in ventas_mes)
    ventas_mes_margen   = sum(v["margen_neto"]   for v in ventas_mes)

    todas_ventas = sb.table("ventas").select("margen_neto").execute().data
    margen_promedio = (
        sum(v["margen_neto"] for v in todas_ventas) / len(todas_ventas)
        if todas_ventas else 0
    )

    ventas_con_prod = (
        sb.table("ventas")
        .select("fecha_venta, productos(fecha_ingreso)")
        .execute()
        .data
    )
    dias_list = []
    for v in ventas_con_prod:
        prod_info = v.get("productos") or {}
        fi = prod_info.get("fecha_ingreso")
        if fi:
            dias_list.append(
                (date.fromisoformat(v["fecha_venta"]) - date.fromisoformat(fi)).days
            )
    dias_promedio = sum(dias_list) / len(dias_list) if dias_list else 0

    canales_resp = sb.table("ventas").select("canal").execute().data
    ventas_por_canal = dict(Counter(v["canal"] for v in canales_resp))

    return {
        "productos_activos":    total_productos,
        "valor_stock":          valor_stock,
        "ventas_mes_unidades":  ventas_mes_unidades,
        "ventas_mes_ingresos":  ventas_mes_ingresos,
        "ventas_mes_margen":    ventas_mes_margen,
        "margen_promedio":      margen_promedio,
        "dias_promedio_inventario": round(dias_promedio, 1),
        "ventas_por_canal":     ventas_por_canal,
    }
