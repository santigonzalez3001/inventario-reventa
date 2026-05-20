from .schema import get_connection, crear_tablas

# Crear tablas al importar el módulo, independiente de qué página cargue primero
crear_tablas()
