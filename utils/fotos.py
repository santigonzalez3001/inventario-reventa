"""
Manejo de fotos usando Supabase Storage.
Las rutas guardadas en la BD son paths dentro del bucket 'fotos', no rutas locales.
"""
from datetime import datetime
from pathlib import Path
import streamlit as st
from database.supabase_client import get_supabase
from database.models import agregar_foto, listar_fotos, eliminar_foto

BUCKET = "Fotos"
MAX_FOTOS = 10
EXTENSIONES_PERMITIDAS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}

CONTENT_TYPES = {
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".webp": "image/webp",
    ".heic": "image/heic",
}


def guardar_foto(producto_id: int, archivo, orden: int = 0) -> str:
    """Sube el archivo a Supabase Storage y registra la ruta en la BD."""
    ext = Path(archivo.name).suffix.lower()
    if ext not in EXTENSIONES_PERMITIDAS:
        raise ValueError(f"Extensión no permitida: {ext}")

    nombre = f"{producto_id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}{ext}"
    storage_path = f"productos/{nombre}"
    file_bytes = archivo.read()

    sb = get_supabase()
    sb.storage.from_(BUCKET).upload(
        path=storage_path,
        file=file_bytes,
        file_options={"contentType": CONTENT_TYPES.get(ext, "image/jpeg")},
    )
    agregar_foto(producto_id, storage_path, orden)
    return storage_path


def url_foto(storage_path: str) -> str:
    """Devuelve la URL pública de una foto en el bucket."""
    sb = get_supabase()
    result = sb.storage.from_(BUCKET).get_public_url(storage_path)
    return result if isinstance(result, str) else result.get("publicUrl", "")


def borrar_foto_storage(storage_path: str):
    """Elimina un archivo del bucket de Supabase Storage."""
    sb = get_supabase()
    sb.storage.from_(BUCKET).remove([storage_path])


def widget_fotos(producto_id: int, prefix: str = ""):
    """Widget reutilizable para subir y mostrar fotos de un producto.

    prefix: namespace para las keys de Streamlit cuando el widget aparece
            varias veces en la misma página para el mismo producto.
    """
    fotos = listar_fotos(producto_id)
    st.write(f"**Fotos** ({len(fotos)}/{MAX_FOTOS})")

    # ── Fotos guardadas ───────────────────────────────────────────────────────
    if fotos:
        cols = st.columns(min(len(fotos), 4))
        for i, foto in enumerate(fotos):
            with cols[i % 4]:
                try:
                    st.image(url_foto(foto["ruta"]), use_container_width=True)
                except Exception:
                    st.caption(f"⚠️ Foto no disponible")
                if st.button("Eliminar", key=f"{prefix}del_foto_{foto['id']}"):
                    borrar_foto_storage(foto["ruta"])
                    eliminar_foto(foto["id"])
                    st.rerun()

    # ── Subir nuevas fotos ────────────────────────────────────────────────────
    if len(fotos) < MAX_FOTOS:
        counter_key = f"{prefix}upload_counter_{producto_id}"
        if counter_key not in st.session_state:
            st.session_state[counter_key] = 0

        archivos = st.file_uploader(
            "Agregar fotos",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key=f"{prefix}uploader_{producto_id}_{st.session_state[counter_key]}",
        )

        if archivos:
            # Vista previa
            st.write("**Vista previa:**")
            prev_cols = st.columns(min(len(archivos), 4))
            for i, arch in enumerate(archivos):
                with prev_cols[i % 4]:
                    img_bytes = arch.read()
                    arch.seek(0)
                    st.image(img_bytes, caption=arch.name, use_container_width=True)

            # Auto-guardar en Supabase Storage
            saved = 0
            for arch in archivos:
                if len(fotos) + saved >= MAX_FOTOS:
                    st.warning("Límite de 10 fotos alcanzado.")
                    break
                try:
                    arch.seek(0)
                    guardar_foto(producto_id, arch, orden=len(fotos) + saved)
                    saved += 1
                except ValueError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Error al subir foto: {e}")

            if saved:
                st.session_state[counter_key] += 1
                st.rerun()
