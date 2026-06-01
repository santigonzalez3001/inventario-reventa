"""
Página de ventas: registrar una venta e historial.
"""
import streamlit as st
import pandas as pd
from database.models import (
    listar_productos,
    registrar_venta,
    listar_ventas,
    COMISIONES,
    comision_fija_ml,
)

st.set_page_config(page_title="Ventas", layout="wide")
st.title("Ventas")

CANALES = list(COMISIONES.keys())


# ─── FORMULARIO: registrar venta ────────────────────────────────────────────
st.subheader("Registrar venta")

productos_disponibles = listar_productos(estado="disponible") + listar_productos(estado="reservado")

if not productos_disponibles:
    st.info("No hay productos disponibles para vender. Registra productos primero.")
else:
    opciones = {
        f"{p['sku']} — {p['marca']} {p['modelo']} T{p.get('talla','?')}": p["id"]
        for p in productos_disponibles
    }

    with st.form("form_venta", clear_on_submit=True):
        seleccion = st.selectbox("Producto *", list(opciones.keys()))
        pid = opciones[seleccion]
        producto = next(p for p in productos_disponibles if p["id"] == pid)

        col1, col2 = st.columns(2)
        with col1:
            precio_final = st.number_input(
                "Precio final de venta (COP) *",
                min_value=0.0,
                value=float(producto.get("precio_venta") or producto["precio_compra"] * 1.3),
                step=1000.0,
                format="%.0f",
            )
            canal = st.selectbox("Canal de venta *", CANALES)

        with col2:
            comision_pct = st.number_input(
                "Comisión del canal (%)",
                min_value=0.0,
                max_value=50.0,
                value=COMISIONES.get(canal, 0.0) * 100,
                step=0.5,
                format="%.1f",
                help="MercadoLibre cobra entre 8 % y 22 % según la categoría. Para tenis/ropa el valor típico es 16 %.",
            ) / 100

            # Campo de envío — visible siempre, relevante sobre todo en ML
            costo_envio = st.number_input(
                "Costo de envío (COP)",
                min_value=0.0,
                value=0.0,
                step=500.0,
                format="%.0f",
                help="Ingresa el valor del envío que pagas tú como vendedor. "
                     "En MercadoLibre el envío gratis es obligatorio para productos ≥ $60.000.",
            )

            notas_venta = st.text_area("Notas", height=68)

        # ── Vista previa del margen ───────────────────────────────────────────
        comision_monto = precio_final * comision_pct
        fija = comision_fija_ml(precio_final) if canal == "MercadoLibre" else 0.0
        margen = precio_final - comision_monto - fija - costo_envio - producto["precio_compra"]
        margen_pct = (margen / precio_final * 100) if precio_final > 0 else 0

        if canal == "MercadoLibre":
            envio_obligatorio = precio_final >= 60_000

            with st.container(border=True):
                st.markdown("#### Desglose MercadoLibre")
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Precio venta", f"${precio_final:,.0f}")
                c2.metric(
                    f"Comisión ({comision_pct*100:.1f} %)",
                    f"−${comision_monto:,.0f}",
                )
                c3.metric(
                    "Cargo fijo ML",
                    f"−${fija:,.0f}",
                    help="$2.500 si precio ≤ $30k · $4.000 si $30k–$60k · $0 si > $60k",
                )
                c4.metric(
                    "Envío" + (" ⚠️ obligatorio" if envio_obligatorio else ""),
                    f"−${costo_envio:,.0f}",
                )
                c5.metric("Costo producto", f"−${producto['precio_compra']:,.0f}")

                color = "green" if margen >= 0 else "red"
                st.markdown(
                    f"**Ganancia neta: "
                    f"<span style='color:{color}; font-size:1.2em'>"
                    f"${margen:,.0f} ({margen_pct:.1f} %)"
                    f"</span>**",
                    unsafe_allow_html=True,
                )

                if envio_obligatorio and costo_envio == 0:
                    st.warning(
                        "El precio supera $60.000: el **envío gratis es obligatorio** en MercadoLibre. "
                        "Ingresa el costo de envío para un cálculo preciso."
                    )
        else:
            st.info(
                f"**Vista previa:** Precio ${precio_final:,.0f} — "
                f"Comisión ${comision_monto:,.0f} — "
                f"Envío ${costo_envio:,.0f} — "
                f"Costo ${producto['precio_compra']:,.0f} — "
                f"**Ganancia neta: ${margen:,.0f} ({margen_pct:.1f} %)**"
            )

        if st.form_submit_button("Confirmar venta", use_container_width=True, type="primary"):
            if precio_final <= 0:
                st.error("El precio final debe ser mayor a 0.")
            else:
                try:
                    venta = registrar_venta(
                        producto_id=pid,
                        precio_final=precio_final,
                        canal=canal,
                        comision_pct=comision_pct,
                        costo_envio=costo_envio,
                        notas=notas_venta,
                    )
                    st.success(
                        f"Venta registrada. Ganancia neta: **${venta['margen_neto']:,.0f}**"
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al registrar venta: {e}")


# ─── HISTORIAL DE VENTAS ─────────────────────────────────────────────────────
st.divider()
st.subheader("Historial de ventas")

ventas = listar_ventas()

if not ventas:
    st.info("Todavía no hay ventas registradas.")
else:
    df = pd.DataFrame(ventas)
    df["comision_pct"] = df["comision_pct"].apply(lambda x: f"{x*100:.1f}%")
    df["precio_final"] = df["precio_final"].apply(lambda x: f"${x:,.0f}")
    df["precio_compra"] = df["precio_compra"].apply(lambda x: f"${x:,.0f}")
    df["margen_neto"] = df["margen_neto"].apply(lambda x: f"${x:,.0f}")
    if "comision_fija" in df.columns:
        df["comision_fija"] = df["comision_fija"].apply(lambda x: f"${x:,.0f}" if x else "—")
    if "costo_envio" in df.columns:
        df["costo_envio"] = df["costo_envio"].apply(lambda x: f"${x:,.0f}" if x else "—")

    columnas = [
        "fecha_venta", "sku", "marca", "modelo", "talla",
        "precio_compra", "precio_final", "canal", "comision_pct",
        "comision_fija", "costo_envio", "margen_neto",
    ]
    columnas = [c for c in columnas if c in df.columns]

    st.dataframe(
        df[columnas],
        use_container_width=True,
        hide_index=True,
        column_config={
            "fecha_venta":    "Fecha",
            "sku":            "SKU",
            "marca":          "Marca",
            "modelo":         "Modelo",
            "talla":          "Talla",
            "precio_compra":  "Costo",
            "precio_final":   "Precio venta",
            "canal":          "Canal",
            "comision_pct":   "Comisión %",
            "comision_fija":  "Cargo fijo ML",
            "costo_envio":    "Envío",
            "margen_neto":    "Ganancia neta",
        },
    )
    st.caption(f"{len(ventas)} ventas en total")
