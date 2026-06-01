"""
Página de inventario: registrar nuevos productos y ver/editar los existentes.
"""
import streamlit as st
import pandas as pd
from database.models import (
    listar_productos,
    crear_producto,
    actualizar_producto,
    eliminar_producto,
    listar_categorias,
    crear_categoria,
)
from utils.fotos import widget_fotos
from utils.claude_ai import generar_contenido_producto

st.set_page_config(page_title="Inventario", layout="wide")
st.title("Inventario")

CANALES_DISPONIBLES = ["MercadoLibre", "Instagram", "Facebook", "Efectivo"]
ESTADOS = ["disponible", "reservado", "vendido"]


# ─── SIDEBAR: filtros ────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filtros")
    busqueda = st.text_input("Buscar por marca / modelo / SKU")
    categorias = listar_categorias()
    opciones_cat = {c["nombre"]: c["id"] for c in categorias}
    filtro_cat = st.selectbox("Categoría", ["Todas"] + list(opciones_cat.keys()))
    filtro_estado = st.selectbox("Estado", ["Todos"] + ESTADOS)

    st.divider()
    st.subheader("Nueva categoría")
    nueva_cat = st.text_input("Nombre")
    if st.button("Agregar categoría") and nueva_cat.strip():
        try:
            crear_categoria(nueva_cat.strip())
            st.success(f"Categoría '{nueva_cat}' creada.")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")


# ─── FORMULARIO: registrar producto ─────────────────────────────────────────
with st.expander("+ Registrar nuevo producto", expanded=False):
    with st.form("form_nuevo_producto", clear_on_submit=False):
        col1, col2 = st.columns(2)

        with col1:
            marca = st.text_input("Marca *", placeholder="Nike, Adidas…")
            modelo = st.text_input("Modelo *", placeholder="Air Max 90, Yeezy 350…")
            talla = st.text_input("Talla", placeholder="42, M, XL…")
            color = st.text_input("Color", placeholder="Blanco, Negro…")
            categoria_nombre = st.selectbox("Categoría *", list(opciones_cat.keys()))

        with col2:
            precio_compra = st.number_input(
                "Precio de compra (COP) *", min_value=0.0, step=1000.0, format="%.0f"
            )
            precio_venta = st.number_input(
                "Precio de venta sugerido (COP)",
                min_value=0.0,
                step=1000.0,
                format="%.0f",
            )
            canales = st.multiselect("Canales de publicación", CANALES_DISPONIBLES)
            notas = st.text_area("Notas", height=80)

        descripcion_ml = st.text_area(
            "Descripción para MercadoLibre",
            value=st.session_state.get("desc_generada", ""),
            height=200,
            placeholder="Escribe la descripción manualmente o usa el botón de IA abajo.",
            key="campo_descripcion",
        )
        precio_ref_ia = st.session_state.get("precio_ref_ia")
        if precio_ref_ia:
            st.info(f"Precio de referencia encontrado en Colombia: **${precio_ref_ia:,.0f} COP**")

        col_ia, col_guardar = st.columns([1, 2])
        with col_ia:
            generar = st.form_submit_button("Generar con IA", use_container_width=True)
        with col_guardar:
            enviado = st.form_submit_button(
                "Guardar producto", use_container_width=True, type="primary"
            )

        if generar:
            if not marca or not modelo:
                st.error("Ingresa Marca y Modelo antes de generar.")
            else:
                with st.spinner("Buscando el producto en internet y generando descripción..."):
                    resultado = generar_contenido_producto(
                        marca=marca,
                        modelo=modelo,
                        talla=talla,
                        color=color,
                        categoria=categoria_nombre,
                        precio_compra=precio_compra,
                    )
                if resultado.error:
                    st.error(resultado.error)
                else:
                    st.session_state["desc_generada"] = resultado.descripcion_ml
                    st.session_state["precio_ref_ia"] = resultado.precio_referencia
                    st.success("Descripción generada. Revísala y ajusta si es necesario.")
                    st.rerun()

        if enviado:
            if not marca or not modelo or precio_compra <= 0:
                st.error("Completa los campos obligatorios: Marca, Modelo y Precio de compra.")
            else:
                try:
                    desc_final = st.session_state.get("desc_generada") or descripcion_ml
                    nuevo = crear_producto(
                        categoria_id=opciones_cat[categoria_nombre],
                        modelo=modelo,
                        marca=marca,
                        precio_compra=precio_compra,
                        talla=talla,
                        color=color,
                        precio_venta=precio_venta if precio_venta > 0 else None,
                        canales=canales,
                        notas=notas,
                        descripcion_ml=desc_final,
                        precio_referencia=st.session_state.get("precio_ref_ia"),
                    )
                    st.success(f"Producto registrado. SKU: **{nuevo['sku']}**")
                    for k in ["desc_generada", "precio_ref_ia"]:
                        st.session_state.pop(k, None)
                    st.session_state["producto_recien_creado"] = nuevo["id"]
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")


# ─── FOTOS del producto recién creado ───────────────────────────────────────
if "producto_recien_creado" in st.session_state:
    pid = st.session_state["producto_recien_creado"]
    with st.expander(f"Subir fotos para el producto #{pid}", expanded=True):
        widget_fotos(pid, prefix="new_")
        if st.button("Listo, cerrar fotos"):
            del st.session_state["producto_recien_creado"]
            st.rerun()


# ─── TABLA DE INVENTARIO ─────────────────────────────────────────────────────
st.divider()
st.subheader("Productos en inventario")

productos = listar_productos(
    estado=None if filtro_estado == "Todos" else filtro_estado,
    categoria_id=opciones_cat.get(filtro_cat) if filtro_cat != "Todas" else None,
    busqueda=busqueda,
)

if not productos:
    st.info("No hay productos con esos filtros.")
else:
    df = pd.DataFrame(productos)
    columnas_mostrar = [
        "sku", "marca", "modelo", "talla", "color",
        "precio_compra", "precio_venta", "precio_referencia",
        "estado", "canales", "fecha_ingreso",
    ]
    columnas_mostrar = [c for c in columnas_mostrar if c in df.columns]
    df["canales"] = df["canales"].apply(lambda x: ", ".join(x) if x else "—")
    df["precio_compra"] = df["precio_compra"].apply(lambda x: f"${x:,.0f}")
    df["precio_venta"] = df["precio_venta"].apply(
        lambda x: f"${x:,.0f}" if x else "—"
    )
    df["precio_referencia"] = df["precio_referencia"].apply(
        lambda x: f"${x:,.0f}" if x else "—"
    )

    st.caption("Haz clic en una fila para ver el detalle completo del producto.")
    event = st.dataframe(
        df[columnas_mostrar],
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "sku": "SKU",
            "marca": "Marca",
            "modelo": "Modelo",
            "talla": "Talla",
            "color": "Color",
            "precio_compra": "Costo",
            "precio_venta": "Precio venta",
            "precio_referencia": "Ref. mercado",
            "estado": st.column_config.SelectboxColumn("Estado", options=ESTADOS),
            "canales": "Canales",
            "fecha_ingreso": "Fecha ingreso",
        },
    )
    st.caption(f"Total: {len(productos)} productos")

    # ── Detalle del producto al hacer clic en una fila ───────────────────────
    filas_seleccionadas = event.selection.rows if event.selection else []
    if filas_seleccionadas:
        idx = filas_seleccionadas[0]
        prod = productos[idx]
        st.session_state["pid_seleccionado"] = prod["id"]

        with st.expander(
            f"Detalle: {prod['marca']} {prod['modelo']} — {prod['sku']}",
            expanded=True,
        ):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**SKU:** {prod['sku']}")
                st.markdown(f"**Marca:** {prod['marca']}")
                st.markdown(f"**Modelo:** {prod['modelo']}")
                st.markdown(f"**Talla:** {prod.get('talla') or '—'}")
                st.markdown(f"**Color:** {prod.get('color') or '—'}")
                st.markdown(f"**Categoría:** {prod.get('categoria_nombre') or '—'}")
                st.markdown(f"**Fecha ingreso:** {prod.get('fecha_ingreso') or '—'}")
            with c2:
                estado_emoji = {"disponible": "🟢", "reservado": "🟡", "vendido": "🔴"}.get(
                    prod["estado"], ""
                )
                st.markdown(f"**Estado:** {estado_emoji} {prod['estado']}")
                st.markdown(f"**Precio compra:** ${prod['precio_compra']:,.0f}")
                pv = prod.get("precio_venta")
                st.markdown(f"**Precio venta:** {'${:,.0f}'.format(pv) if pv else '—'}")
                pr = prod.get("precio_referencia")
                st.markdown(f"**Ref. mercado:** {'${:,.0f}'.format(pr) if pr else '—'}")
                canales_str = ", ".join(prod.get("canales") or []) or "—"
                st.markdown(f"**Canales:** {canales_str}")
            if prod.get("notas"):
                st.markdown(f"**Notas:** {prod['notas']}")
            if prod.get("descripcion_ml"):
                with st.expander("Descripción para MercadoLibre"):
                    st.markdown(prod["descripcion_ml"])

            st.subheader("Fotos")
            widget_fotos(prod["id"], prefix="detail_")


# ─── DETALLE / EDICIÓN ────────────────────────────────────────────────────────
st.divider()
st.subheader("Editar producto")

# Usar todos los productos (sin filtro) para que los vendidos también sean editables/eliminables
todos_productos = listar_productos()

if todos_productos:
    # Pre-seleccionar el producto que se hizo clic en la tabla
    default_idx = 0
    if "pid_seleccionado" in st.session_state:
        sid = st.session_state["pid_seleccionado"]
        for i, tp in enumerate(todos_productos):
            if tp["id"] == sid:
                default_idx = i
                break

    opciones_ids = {
        f"{p['sku']} — {p['marca']} {p['modelo']} [{p['estado']}]": p["id"]
        for p in todos_productos
    }
    seleccion = st.selectbox(
        "Seleccionar producto",
        list(opciones_ids.keys()),
        index=default_idx,
    )
    pid_editar = opciones_ids[seleccion]
    p = next(x for x in todos_productos if x["id"] == pid_editar)

    # Botón de regenerar descripción con IA (fuera del form)
    col_regen, _ = st.columns([1, 3])
    with col_regen:
        if st.button("Regenerar descripción con IA", key="regen_ia"):
            with st.spinner("Generando..."):
                resultado = generar_contenido_producto(
                    marca=p["marca"],
                    modelo=p["modelo"],
                    talla=p.get("talla") or "",
                    color=p.get("color") or "",
                    categoria=p.get("categoria_nombre") or "Tenis",
                    precio_compra=p["precio_compra"],
                )
            if resultado.error:
                st.error(resultado.error)
            else:
                actualizar_producto(
                    pid_editar,
                    descripcion_ml=resultado.descripcion_ml,
                    precio_referencia=resultado.precio_referencia,
                )
                st.success(
                    "Descripción actualizada."
                    + (
                        f" Precio ref: ${resultado.precio_referencia:,.0f}"
                        if resultado.precio_referencia
                        else ""
                    )
                )
                st.rerun()

    with st.form("form_editar"):
        col1, col2 = st.columns(2)
        with col1:
            nueva_marca = st.text_input("Marca", value=p["marca"])
            nuevo_modelo = st.text_input("Modelo", value=p["modelo"])
            nueva_talla = st.text_input("Talla", value=p.get("talla") or "")
            nuevo_color = st.text_input("Color", value=p.get("color") or "")
        with col2:
            nuevo_precio_compra = st.number_input(
                "Precio compra", value=float(p["precio_compra"]), step=1000.0, format="%.0f"
            )
            nuevo_precio_venta = st.number_input(
                "Precio venta",
                value=float(p["precio_venta"]) if p.get("precio_venta") else 0.0,
                step=1000.0,
                format="%.0f",
            )
            nuevo_estado = st.selectbox(
                "Estado", ESTADOS, index=ESTADOS.index(p["estado"])
            )
            nuevos_canales = st.multiselect(
                "Canales", CANALES_DISPONIBLES, default=p.get("canales") or []
            )
            nuevas_notas = st.text_area("Notas", value=p.get("notas") or "")

        nueva_descripcion = st.text_area(
            "Descripción MercadoLibre",
            value=p.get("descripcion_ml") or "",
            height=200,
        )

        if st.form_submit_button("Guardar cambios", use_container_width=True, type="primary"):
            actualizar_producto(
                pid_editar,
                marca=nueva_marca,
                modelo=nuevo_modelo,
                talla=nueva_talla,
                color=nuevo_color,
                precio_compra=nuevo_precio_compra,
                precio_venta=nuevo_precio_venta if nuevo_precio_venta > 0 else None,
                estado=nuevo_estado,
                canales=nuevos_canales,
                notas=nuevas_notas,
                descripcion_ml=nueva_descripcion,
            )
            st.success("Producto actualizado.")
            st.rerun()

    # Mostrar descripción actual si existe
    if p.get("descripcion_ml"):
        with st.expander("Ver descripción actual para MercadoLibre"):
            st.markdown(p["descripcion_ml"])

    st.subheader("Fotos del producto")
    widget_fotos(pid_editar, prefix="edit_")

    # ── Eliminar producto (fuera del form, con confirmación) ─────────────────
    st.divider()
    with st.expander("Eliminar producto", expanded=False):
        st.warning(
            f"Esto eliminará permanentemente **{p['marca']} {p['modelo']}** "
            f"({p['sku']}) junto con sus ventas y fotos asociadas."
        )
        confirmar = st.checkbox("Confirmar eliminación", key="check_eliminar")
        if confirmar:
            if st.button("Eliminar permanentemente", type="secondary", key="btn_eliminar"):
                try:
                    eliminar_producto(pid_editar)
                    st.session_state.pop("pid_seleccionado", None)
                    st.success("Producto eliminado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al eliminar: {e}")
