from core.analizador import analizar_incendio
from core.proyecto import guardar_analisis

analisis = analizar_incendio(1)

guardar_analisis(analisis)

print("Análisis generado correctamente")