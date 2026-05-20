"""
Dashboard de métricas del negocio.
"""
import streamlit as st
import pandas as pd
from database.models import metricas_dashboard, listar_ventas, listar_productos

st.set_page_config(page_title="Dashboard", layout="wide")
st.title("Dashboard")

m = metricas_dashboard()

# ─── KPIs principales ────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Productos activos", m["productos_activos"])
c2.metric("Valor en stock", f"${m['valor_stock']:,.0f}")
c3.metric("Ventas este mes", m["ventas_mes_unidades"])
c4.metric("Margen este mes", f"${m['ventas_mes_margen']:,.0f}")

st.divider()

col1, col2 = st.columns(2)

# ─── Ventas por canal ────────────────────────────────────────────────────────
with col1:
    st.subheader("Ventas por canal")
    if m["ventas_por_canal"]:
        df_canal = pd.DataFrame(
            list(m["ventas_por_canal"].items()), columns=["Canal", "Unidades"]
        )
        st.bar_chart(df_canal.set_index("Canal"))
    else:
        st.info("Sin ventas aún.")

# ─── Días promedio en inventario ─────────────────────────────────────────────
with col2:
    st.subheader("Estadísticas generales")
    st.metric("Días promedio en inventario", m["dias_promedio_inventario"])
    st.metric("Margen promedio por venta", f"${m['margen_promedio']:,.0f}")

st.divider()

# ─── Evolución de ventas (últimas 30) ────────────────────────────────────────
st.subheader("Evolución de ventas")
ventas = listar_ventas(limite=60)
if ventas:
    df_v = pd.DataFrame(ventas)
    df_v["fecha_venta"] = pd.to_datetime(df_v["fecha_venta"])
    df_agg = df_v.groupby("fecha_venta").agg(
        ingresos=("precio_final", "sum"),
        unidades=("id", "count"),
    ).reset_index()
    st.line_chart(df_agg.set_index("fecha_venta")[["ingresos", "unidades"]])
else:
    st.info("Sin ventas para graficar.")

st.divider()

# ─── Estado del inventario ───────────────────────────────────────────────────
st.subheader("Estado del inventario")
todos = listar_productos()
if todos:
    df_inv = pd.DataFrame(todos)
    conteo = df_inv["estado"].value_counts().reset_index()
    conteo.columns = ["Estado", "Cantidad"]
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.dataframe(conteo, hide_index=True, use_container_width=True)
    with col_b:
        st.bar_chart(conteo.set_index("Estado"))
