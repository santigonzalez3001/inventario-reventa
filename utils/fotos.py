"""
Manejo de fotos: guardar archivos subidos en la carpeta /fotos y registrar rutas en BD.
"""
from pathlib import Path
from datetime import datetime
import uuid
import streamlit as st
from database.models import agregar_foto, listar_fotos, eliminar_foto

FOTOS_DIR = Path(__file__).parent.parent / "fotos"
FOTOS_DIR.mkdir(exist_ok=True)

MAX_FOTOS = 10
EXTENSIONES_PERMITIDAS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


def guardar_foto(producto_id: int, archivo, orden: int = 0) -> str:
    ext = Path(archivo.name).suffix.lower()
    if ext not in EXTENSIONES_PERMITIDAS:
        raise ValueError(f"Extensión no permitida: {ext}")

    nombre = f"{producto_id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}{ext}"
    ruta = FOTOS_DIR / nombre
    ruta.write_bytes(archivo.read())

    agregar_foto(producto_id, str(ruta), orden)
    return str(ruta)


def widget_fotos(producto_id: int):
    """Widget reutilizable de Streamlit para subir y mostrar fotos de un producto."""
    fotos = listar_fotos(producto_id)
    st.write(f"**Fotos** ({len(fotos)}/{MAX_FOTOS})")

    if fotos:
        cols = st.columns(min(len(fotos), 3))
        for i, foto in enumerate(fotos):
            ruta = Path(foto["ruta"])
            if ruta.exists():
                with cols[i % 3]:
                    st.image(str(ruta), use_container_width=True)
                    if st.button("Eliminar", key=f"del_foto_{foto['id']}"):
                        ruta.unlink(missing_ok=True)
                        eliminar_foto(foto["id"])
                        st.rerun()

    if len(fotos) < MAX_FOTOS:
        archivos = st.file_uploader(
            "Subir fotos (máx 10)",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key=f"uploader_{producto_id}_{uuid.uuid4().hex[:8]}",
        )
        if archivos:
            for i, arch in enumerate(archivos):
                if len(fotos) + i >= MAX_FOTOS:
                    st.warning("Límite de 10 fotos alcanzado.")
                    break
                try:
                    guardar_foto(producto_id, arch, orden=len(fotos) + i)
                except ValueError as e:
                    st.error(str(e))
            st.rerun()
