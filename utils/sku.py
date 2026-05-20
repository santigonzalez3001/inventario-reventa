"""
Generador de SKU automático para cada producto.
Formato: MARCA-MODELO-TALLA-XXXX  (ej: NIK-AM90-42-0001)
"""
import re
import time


def _limpiar(texto: str, largo: int) -> str:
    texto = re.sub(r"[^A-Z0-9]", "", texto.upper())
    return texto[:largo] if texto else "XX"


def generar_sku(marca: str, modelo: str, talla: str = "") -> str:
    parte_marca = _limpiar(marca, 3)
    palabras_modelo = re.sub(r"\s+", "-", modelo.strip().upper())
    parte_modelo = _limpiar(palabras_modelo.replace("-", ""), 5)
    parte_talla = _limpiar(talla, 4) if talla else "ST"
    # Sufijo basado en milisegundos para unicidad
    sufijo = str(int(time.time() * 1000))[-4:]
    return f"{parte_marca}-{parte_modelo}-{parte_talla}-{sufijo}"
