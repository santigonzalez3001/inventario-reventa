"""
Punto de entrada de la app. Inicializa la BD y muestra el home.
"""
import streamlit as st
from database.schema import crear_tablas
from database.models import metricas_dashboard, listar_productos

# Inicializar BD en cada arranque (idempotente)
crear_tablas()

st.set_page_config(
    page_title="Inventario Reventa",
    page_icon="👟",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Inventario Reventa")
st.caption("Gestión de tenis, ropa y accesorios")

m = metricas_dashboard()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Productos activos", m["productos_activos"])
col2.metric("Valor en stock", f"${m['valor_stock']:,.0f} COP")
col3.metric("Ventas este mes", m["ventas_mes_unidades"])
col4.metric("Margen este mes", f"${m['ventas_mes_margen']:,.0f} COP")

st.divider()

st.subheader("Últimos productos ingresados")
recientes = listar_productos()[:5]
if recientes:
    for p in recientes:
        canales = ", ".join(p.get("canales") or []) or "—"
        st.write(
            f"**{p['sku']}** — {p['marca']} {p['modelo']} "
            f"T{p.get('talla','?')} | Estado: `{p['estado']}` | Canales: {canales}"
        )
else:
    st.info("Sin productos registrados. Ve a **Inventario** para agregar el primero.")

st.divider()
st.markdown(
    """
**Navegación:**
- **Inventario** → Registrar y gestionar productos
- **Ventas** → Registrar ventas y ver historial
- **Dashboard** → Métricas del negocio
- **Caja** → Flujo de capital e inversión
"""
)
