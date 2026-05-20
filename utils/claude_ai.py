"""
Integración con Claude API para generación de contenido de productos.
Usa web search para buscar el modelo exacto y precios en Colombia.
"""
import os
import anthropic
from dataclasses import dataclass


@dataclass
class ResultadoIA:
    descripcion_ml: str
    precio_referencia: float | None
    fuentes: list[str]
    error: str | None = None


def _get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    # Intentar leer desde st.secrets si no está en el entorno
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("ANTHROPIC_API_KEY")
        except Exception:
            pass

    if not api_key:
        raise ValueError(
            "Falta ANTHROPIC_API_KEY. "
            "Agrégala en .streamlit/secrets.toml (local) o en Streamlit Cloud > Settings > Secrets."
        )
    return anthropic.Anthropic(api_key=api_key)


def generar_contenido_producto(
    marca: str,
    modelo: str,
    talla: str,
    color: str,
    categoria: str,
    precio_compra: float,
) -> ResultadoIA:
    """
    Llama a Claude con web search para:
    1. Buscar el producto exacto en el mercado colombiano
    2. Generar descripción optimizada para MercadoLibre Colombia
    3. Encontrar rango de precios de referencia en COP
    """
    client = _get_client()

    prompt = f"""Eres un experto en e-commerce colombiano especializado en reventa de {categoria.lower()}.

Producto a analizar:
- Marca: {marca}
- Modelo: {modelo}
- Talla: {talla if talla else "no especificada"}
- Color: {color if color else "no especificado"}
- Categoría: {categoria}
- Precio de compra (referencia interna): ${precio_compra:,.0f} COP

TAREA 1 — Investigación de mercado:
Busca en web el precio actual de "{marca} {modelo}" en Colombia (MercadoLibre Colombia, tiendas colombianas, revendedores). Encuentra el rango de precios en COP para este modelo específico.

TAREA 2 — Descripción para MercadoLibre:
Genera una descripción de producto optimizada para MercadoLibre Colombia siguiendo este formato EXACTO:

---DESCRIPCION_START---
[Título sugerido: máximo 60 caracteres, incluir marca, modelo, talla y color]

[3-4 oraciones de descripción que resalten: autenticidad, características del modelo, comodidad/estilo, condición del producto]

✅ CARACTERÍSTICAS:
• [característica 1]
• [característica 2]
• [característica 3]
• [característica 4 si aplica]

📦 CONDICIÓN: [Nuevo / Usado en excelente estado / etc.]
📏 TALLA: {talla if talla else "Consultar"}
🎨 COLOR: {color if color else "Ver fotos"}

💬 Cualquier pregunta, con gusto respondo.
---DESCRIPCION_END---

TAREA 3 — Precio de referencia:
Al final de tu respuesta, incluye EXACTAMENTE esta línea (solo el número, sin puntos de miles ni símbolo $):
PRECIO_REF: [precio_en_cop_como_numero_entero]

Si no encuentras precio confiable en Colombia, escribe: PRECIO_REF: 0
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            tools=[
                {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": 4,
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )

        # Extraer texto de todos los bloques de contenido
        texto_completo = ""
        fuentes = []
        for bloque in response.content:
            if bloque.type == "text":
                texto_completo += bloque.text
            elif hasattr(bloque, "type") and bloque.type == "tool_result":
                pass

        # Parsear descripción
        descripcion = ""
        if "---DESCRIPCION_START---" in texto_completo and "---DESCRIPCION_END---" in texto_completo:
            inicio = texto_completo.index("---DESCRIPCION_START---") + len("---DESCRIPCION_START---")
            fin = texto_completo.index("---DESCRIPCION_END---")
            descripcion = texto_completo[inicio:fin].strip()

        if not descripcion:
            descripcion = texto_completo.strip()

        # Parsear precio de referencia
        precio_ref = None
        for linea in texto_completo.split("\n"):
            if linea.strip().startswith("PRECIO_REF:"):
                try:
                    valor = linea.split(":", 1)[1].strip().replace(",", "").replace(".", "")
                    precio_ref = float(valor) if valor != "0" else None
                except (ValueError, IndexError):
                    pass

        return ResultadoIA(
            descripcion_ml=descripcion,
            precio_referencia=precio_ref,
            fuentes=fuentes,
        )

    except anthropic.AuthenticationError:
        return ResultadoIA(
            descripcion_ml="",
            precio_referencia=None,
            fuentes=[],
            error="API key inválida. Verifica ANTHROPIC_API_KEY.",
        )
    except anthropic.RateLimitError:
        return ResultadoIA(
            descripcion_ml="",
            precio_referencia=None,
            fuentes=[],
            error="Límite de la API alcanzado. Intenta en unos minutos.",
        )
    except Exception as e:
        return ResultadoIA(
            descripcion_ml="",
            precio_referencia=None,
            fuentes=[],
            error=f"Error inesperado: {str(e)}",
        )
