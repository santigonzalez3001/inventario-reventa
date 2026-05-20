"""
Módulo de caja: capital invertido, recuperado y disponible para reinvertir.
"""
import streamlit as st
import pandas as pd
from database.models import (
    resumen_caja,
    listar_movimientos_caja,
    registrar_movimiento_caja,
)

st.set_page_config(page_title="Caja", layout="wide")
st.title("Caja y reinversión")

resumen = resumen_caja()

# ─── Resumen ─────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
c1.metric("Total ingresos", f"${resumen['ingresos_totales']:,.0f}")
c2.metric("Total egresos", f"${resumen['egresos_totales']:,.0f}")
c3.metric(
    "Saldo disponible",
    f"${resumen['saldo_disponible']:,.0f}",
    delta=f"${resumen['saldo_disponible']:,.0f}",
    delta_color="normal",
)

st.divider()

# ─── Registrar movimiento manual ─────────────────────────────────────────────
st.subheader("Registrar movimiento")
with st.form("form_caja", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        tipo = st.radio("Tipo", ["egreso", "ingreso"], horizontal=True)
        concepto = st.text_input("Concepto *", placeholder="Compra tenis, gasto envío…")
    with col2:
        monto = st.number_input("Monto (COP) *", min_value=0.0, step=1000.0, format="%.0f")
        referencia = st.text_input("Referencia opcional")

    if st.form_submit_button("Registrar", use_container_width=True):
        if not concepto or monto <= 0:
            st.error("Completa concepto y monto.")
        else:
            registrar_movimiento_caja(tipo, concepto, monto, referencia)
            st.success("Movimiento registrado.")
            st.rerun()

st.divider()

# ─── Historial ───────────────────────────────────────────────────────────────
st.subheader("Historial de movimientos")
movimientos = listar_movimientos_caja()
if movimientos:
    df = pd.DataFrame(movimientos)
    df["monto_fmt"] = df.apply(
        lambda r: f"+${r['monto']:,.0f}" if r["tipo"] == "ingreso" else f"-${r['monto']:,.0f}",
        axis=1,
    )
    columnas = ["fecha", "tipo", "concepto", "monto_fmt", "referencia"]
    columnas = [c for c in columnas if c in df.columns]
    st.dataframe(
        df[columnas],
        use_container_width=True,
        hide_index=True,
        column_config={
            "fecha": "Fecha",
            "tipo": "Tipo",
            "concepto": "Concepto",
            "monto_fmt": "Monto",
            "referencia": "Referencia",
        },
    )
else:
    st.info("No hay movimientos registrados.")
