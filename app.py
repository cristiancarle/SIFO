from modulos.database import (
    crear_base_datos,
    registrar_incendio,
    listar_incendios,
    obtener_incendios
)

from modulos.generar_kml import generar_kml
from core.analizador import analizar_incendio, analizar_coordenadas
from modulos.utilidades import crear_carpetas
import sys


def leer_entrada(mensaje):
    try:
        return input(mensaje)
    except EOFError:
        print("\nNo se recibió entrada. Saliendo de SIFO.")
        raise
    except KeyboardInterrupt:
        print("\nOperación cancelada. Saliendo de SIFO.")
        raise


def iniciar_interfaz_grafica():
    try:
        import tkinter as tk
        if tk.TkVersion < 8.6:
            print("\nTkinter no está disponible o está incompleto en este entorno.")
            return False

        from ui.gui import main as gui_main
    except ModuleNotFoundError as exc:
        if exc.name in {"folium", "matplotlib", "tkinter"}:
            print(
                f"\nFalta la dependencia '{exc.name}'. "
                "Instalá las dependencias con: pip install -r requirements.txt"
            )
        else:
            print(f"\nNo se pudo iniciar la interfaz gráfica: {exc}")
        return False
    except Exception as exc:
        print(f"\nNo se pudo iniciar la interfaz gráfica: {exc}")
        return False

    gui_main()
    return True


# =====================================================
# MENÚ
# =====================================================

def mostrar_menu():

    print("\n" + "=" * 60)
    print("            S I F O")
    print("Sistema Inteligente para Incendios Forestales")
    print("=" * 60)
    print("1 - Registrar incendio")
    print("2 - Listar incendios")
    print("3 - Generar mapa KML")
    print("4 - Analizar incendio")
    print("5 - Salir")
    print("=" * 60)


# =====================================================
# REGISTRAR
# =====================================================

def opcion_registrar():

    print("\nREGISTRO DE INCENDIO")
    print("-" * 40)

    try:
        fecha = leer_entrada("Fecha (dd/mm/aaaa): ")
        hora = leer_entrada("Hora (hh:mm): ")
        nombre = leer_entrada("Nombre del incendio: ")
        provincia = leer_entrada("Provincia: ")
        localidad = leer_entrada("Localidad: ")
        latitud = float(leer_entrada("Latitud: "))
        longitud = float(leer_entrada("Longitud: "))
        descripcion = leer_entrada("Descripción: ")
    except EOFError:
        return
    except KeyboardInterrupt:
        return
    except ValueError:
        print("\nLas coordenadas no son válidas.")
        return

    registrar_incendio(
        fecha,
        hora,
        nombre,
        provincia,
        localidad,
        latitud,
        longitud,
        descripcion
    )

    print("\n✅ Incendio registrado correctamente.")


# =====================================================
# LISTAR
# =====================================================

def opcion_listar():

    incendios = listar_incendios()

    if len(incendios) == 0:

        print("\nNo existen incendios registrados.")
        return

    print("\nLISTADO DE INCENDIOS")
    print("=" * 70)

    for incendio in incendios:

        print(f"ID: {incendio[0]}")
        print(f"Fecha: {incendio[1]}")
        print(f"Hora: {incendio[2]}")
        print(f"Nombre: {incendio[3]}")
        print(f"Provincia: {incendio[4]}")
        print(f"Localidad: {incendio[5]}")
        print(f"Latitud: {incendio[6]}")
        print(f"Longitud: {incendio[7]}")
        print(f"Descripción: {incendio[8]}")
        print(f"Estado: {incendio[9]}")
        print(f"Radio de análisis: {incendio[10]} m")
        print("-" * 70)


# =====================================================
# GENERAR KML
# =====================================================

def opcion_generar_kml():

    incendios = obtener_incendios()

    if len(incendios) == 0:

        print("\nNo existen incendios registrados.")
        return

    print("\nINCENDIOS DISPONIBLES")
    print("=" * 60)

    for incendio in incendios:

        print(
            f"{incendio[0]} - {incendio[1]} | "
            f"{incendio[2]} | {incendio[3]}"
        )

    try:

        id_incendio = int(
            leer_entrada("\nSeleccione el ID del incendio: ")
        )

    except EOFError:
        return
    except KeyboardInterrupt:
        return
    except ValueError:

        print("ID inválido.")
        return

    generar_kml(id_incendio)


def opcion_analizar():
    print("\nANÁLISIS DE INCIDENTE")
    print("-" * 40)
    print("1 - Usar incendio registrado")
    print("2 - Ingresar coordenadas manualmente")

    try:
        opcion = leer_entrada("Seleccione una opción: ")
    except EOFError:
        return
    except KeyboardInterrupt:
        return

    if opcion == "1":
        incendios = obtener_incendios()

        if len(incendios) == 0:
            print("\nNo existen incendios registrados.")
            return

        print("\nINCENDIOS DISPONIBLES")
        print("=" * 60)

        for incendio in incendios:
            print(
                f"{incendio[0]} - {incendio[1]} | "
                f"{incendio[2]} | {incendio[3]}"
            )

        try:
            id_incendio = int(leer_entrada("\nSeleccione el ID del incendio: "))
        except EOFError:
            return
        except KeyboardInterrupt:
            return
        except ValueError:
            print("ID inválido.")
            return

        resultado = analizar_incendio(id_incendio)

    elif opcion == "2":
        try:
            nombre = leer_entrada("Nombre del incidente: ")
            provincia = leer_entrada("Provincia: ")
            localidad = leer_entrada("Localidad: ")
            latitud = float(leer_entrada("Latitud: "))
            longitud = float(leer_entrada("Longitud: "))
            descripcion = leer_entrada("Descripción: ")
        except EOFError:
            return
        except KeyboardInterrupt:
            return
        except ValueError:
            print("\nLas coordenadas no son válidas.")
            return
        resultado = analizar_coordenadas(
            nombre,
            provincia,
            localidad,
            latitud,
            longitud,
            descripcion
        )
    else:
        print("Opción incorrecta.")
        return

    if resultado is None:
        print("No se pudo realizar el análisis.")
        return

    analisis, carpeta = resultado

    print("\nAnálisis completado.")
    print(f"Resultados guardados en: {carpeta}")


# =====================================================
# MAIN
# =====================================================

def main():

    crear_carpetas()

    crear_base_datos()

    print("\n" + "=" * 60)
    print("            S I F O")
    print("Sistema Inteligente para Incendios Forestales")
    print("=" * 60)
    print("1 - Interfaz Gráfica (Recomendado)")
    print("2 - Menú de Línea de Comandos")
    print("3 - Salir")
    print("=" * 60)

    try:
        opcion = leer_entrada("Seleccione una opción: ")
    except EOFError:
        return
    except KeyboardInterrupt:
        return

    if opcion == "1":
        print("\nIniciando interfaz gráfica...")
        iniciar_interfaz_grafica()
    elif opcion == "2":
        menu_cli()
    elif opcion == "3":
        print("\nGracias por utilizar SIFO.")
        sys.exit(0)
    else:
        print("\nOpción incorrecta.")


def menu_cli():

    crear_carpetas()

    crear_base_datos()

    while True:

        mostrar_menu()

        try:
            opcion = leer_entrada("Seleccione una opción: ")
        except EOFError:
            break
        except KeyboardInterrupt:
            break

        if opcion == "1":

            opcion_registrar()

        elif opcion == "2":

            opcion_listar()

        elif opcion == "3":

            opcion_generar_kml()

        elif opcion == "4":

            opcion_analizar()

        elif opcion == "5":

            print("\nGracias por utilizar SIFO.")
            break

        else:

            print("\nOpción incorrecta.")


# =====================================================
# INICIO
# =====================================================

if __name__ == "__main__":
    main()