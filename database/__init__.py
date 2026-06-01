from .supabase_client import get_supabase
from .schema import crear_tablas

# Mantener compatibilidad: crear_tablas es no-op en la versión cloud
crear_tablas()
