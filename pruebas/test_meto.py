from providers.openmeteo import obtener_meteorologia

datos = obtener_meteorologia(
    -24.95675,
    -65.60647
)

print(datos)