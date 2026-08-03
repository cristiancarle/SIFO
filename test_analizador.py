from core.analizador import analizar_incendio
from core.proyecto import guardar_analisis

resultado = analizar_incendio(1)

if resultado is None:
    raise SystemExit("No se encontró el incendio con ID 1.")

analisis, carpeta = resultado

guardar_analisis(analisis)
print(f"Análisis generado correctamente en: {carpeta}")