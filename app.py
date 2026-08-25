import os
import sys
from datetime import datetime

from config import INFORMES_DIR, KML_DIR
from modulos.database import (
    crear_base_datos,
    registrar_incendio,
    listar_incendios,
    obtener_incendio_por_id,
    obtener_incendios
)

from modulos.generar_kml import generar_kml
from modulos.informe_incendio import generar_informe_incendio
from modulos.utilidades import crear_carpetas, sanitizar_nombre_archivo

try:
    import tkinter as tk
    from tkinter import Tk, Button, Label, Listbox, Scrollbar, StringVar, messagebox
    from tkinter import ttk
except ImportError:
    tk = None
    Tk = None
    Button = None
    Label = None
    Listbox = None
    Scrollbar = None
    StringVar = None
    messagebox = None
    ttk = None


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
    print("3 - Generar mapa KML con simulación")
    print("4 - Generar informe PDF y dashboard")
    print("5 - Salir")
    print("=" * 60)


# =====================================================
# REGISTRAR
# =====================================================

def opcion_registrar():

    print("\nREGISTRO DE INCENDIO")
    print("-" * 40)

    fecha = input("Fecha (dd/mm/aaaa): ")
    hora = input("Hora (hh:mm): ")
    nombre = input("Nombre del incendio: ")
    provincia = input("Provincia: ")
    localidad = input("Localidad: ")

    try:
        latitud = float(input("Latitud: "))
        longitud = float(input("Longitud: "))
    except ValueError:
        print("\nLas coordenadas no son válidas.")
        return

    descripcion = input("Descripción: ")

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
            input("\nSeleccione el ID del incendio: ")
        )

    except ValueError:

        print("ID inválido.")
        return

    generar_kml(id_incendio)


def opcion_generar_informe():

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
            input("\nSeleccione el ID del incendio: ")
        )

    except ValueError:

        print("ID inválido.")
        return

    generar_informe_incendio(id_incendio)


# =====================================================
# TKINTER GUI
# =====================================================

def abrir_archivo(ruta):
    if not ruta or not os.path.exists(ruta):
        return False

    try:
        os.startfile(ruta)
        return True
    except AttributeError:
        pass

    try:
        if sys.platform.startswith('darwin'):
            os.system(f'open "{ruta}"')
        else:
            os.system(f'xdg-open "{ruta}"')
        return True
    except OSError:
        return False


class VentanaSIFO:

    def __init__(self, root):
        self.root = root
        self.root.title('SIFO - Simulación de Incendio')
        self.root.geometry('880x540')
        self.root.minsize(760, 420)
        self.root.after(100, self._seleccionar_ultimo_incendio)

        self.root.configure(bg='#0b1220')

        try:
            style = ttk.Style()
            style.theme_use('clam')
            style.configure('Header.TLabel', background='#0b1220', foreground='#e2e8f0', font=('Arial', 16, 'bold'))
            style.configure('Panel.TFrame', background='#0f172a')
            style.configure('Main.TFrame', background='#111827')
            style.configure('Card.TFrame', background='#f8fafc')
            style.configure('TButton', padding=(14, 8), font=('Arial', 10, 'bold'))
            style.map('TButton', background=[('active', '#dbeafe')])
        except Exception:
            pass

        titulo = Label(
            root,
            text='SIFO - Sistema Inteligente para Incendios Forestales',
            font=('Arial', 15, 'bold'),
            bg='#0b1220',
            fg='#f8fafc',
            pady=14,
        )
        titulo.pack(fill='x')

        panel = ttk.Frame(root, padding=12)
        panel.pack(fill='both', expand=True)
        panel.configure(style='Panel.TFrame')

        Label(panel, text='Incendios disponibles', font=('Arial', 11, 'bold'), bg='#0f172a', fg='#e2e8f0').pack(anchor='w')

        frame_lista = ttk.Frame(panel)
        frame_lista.pack(fill='both', expand=True, pady=(8, 12))
        frame_lista.configure(style='Card.TFrame')

        scrollbar = Scrollbar(frame_lista, bg='#cbd5e1')
        scrollbar.pack(side='right', fill='y')

        self.lista = Listbox(
            frame_lista,
            yscrollcommand=scrollbar.set,
            font=('Consolas', 10),
            height=12,
            selectmode='single',
            activestyle='none',
            bg='#f8fafc',
            fg='#0f172a',
            bd=0,
            highlightthickness=0,
        )
        self.lista.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.lista.yview)

        self._recargar_incendios()

        botones = ttk.Frame(panel)
        botones.pack(fill='x', pady=(6, 0))

        ttk.Button(botones, text='Nuevo incendio', command=self.abrir_formulario_registro).pack(side='left', padx=(0, 8))
        ttk.Button(botones, text='Generar KML', command=self.generar_kml).pack(side='left', padx=(0, 8))
        ttk.Button(botones, text='Generar informe', command=self.generar_informe).pack(side='left', padx=(0, 8))
        ttk.Button(botones, text='Abrir KML', command=self.abrir_kml).pack(side='left', padx=(0, 8))
        ttk.Button(botones, text='Abrir PDF', command=self.abrir_pdf).pack(side='left', padx=(0, 8))
        ttk.Button(botones, text='Abrir HTML', command=self.abrir_html).pack(side='left', padx=(0, 8))

    def abrir_formulario_registro(self):
        dialog = tk.Toplevel(self.root)
        dialog.title('Registrar incendio')
        dialog.geometry('620x520')
        dialog.minsize(560, 480)
        dialog.configure(bg='#0f172a')
        dialog.transient(self.root)
        dialog.grab_set()

        cabecera = tk.Label(
            dialog,
            text='Registro de incidente',
            bg='#0f172a',
            fg='#f8fafc',
            font=('Arial', 16, 'bold'),
            pady=18,
        )
        cabecera.pack(fill='x')

        body = tk.Frame(dialog, bg='#111827', padx=16, pady=12)
        body.pack(fill='both', expand=True)

        campos = [
            ('Fecha (dd/mm/aaaa)', 'fecha'),
            ('Hora (hh:mm)', 'hora'),
            ('Nombre del incendio', 'nombre'),
            ('Provincia', 'provincia'),
            ('Localidad', 'localidad'),
            ('Latitud', 'latitud'),
            ('Longitud', 'longitud'),
            ('Descripción', 'descripcion'),
        ]

        entries = {}
        default_fecha = datetime.now().strftime('%d/%m/%Y')
        default_hora = datetime.now().strftime('%H:%M')

        for label_text, clave in campos:
            fila = tk.Frame(body, bg='#111827', pady=6)
            fila.pack(fill='x')

            label = tk.Label(fila, text=label_text, width=18, anchor='w', bg='#111827', fg='#e2e8f0', font=('Arial', 10, 'bold'))
            label.pack(side='left')

            var = tk.Entry(
                fila,
                width=40,
                font=('Arial', 10),
                bg='#f8fafc',
                fg='#0f172a',
                bd=1,
                relief='flat',
            )
            if clave == 'fecha':
                var.insert(0, default_fecha)
            elif clave == 'hora':
                var.insert(0, default_hora)
            var.pack(side='left', fill='x', expand=True, padx=(10, 0))
            entries[clave] = var

        def guardar():
            datos = {clave: entry.get().strip() for clave, entry in entries.items()}
            if not datos['nombre']:
                messagebox.showwarning('SIFO', 'Debe completar el nombre del incendio.')
                return

            datos['fecha'] = datos.get('fecha') or default_fecha
            datos['hora'] = datos.get('hora') or default_hora

            try:
                latitud = float(datos['latitud'])
                longitud = float(datos['longitud'])
            except ValueError:
                messagebox.showwarning('SIFO', 'Las coordenadas deben ser numéricas.')
                return

            registrar_incendio(
                datos.get('fecha', ''),
                datos.get('hora', ''),
                datos.get('nombre', ''),
                datos.get('provincia', ''),
                datos.get('localidad', ''),
                latitud,
                longitud,
                datos.get('descripcion', ''),
            )
            self._recargar_incendios()
            dialog.destroy()
            messagebox.showinfo('SIFO', 'Incendio registrado correctamente.')

        for entry in entries.values():
            entry.bind('<Return>', lambda event=None: guardar())

        footer = tk.Frame(dialog, bg='#0f172a', padx=16, pady=(0, 16))
        footer.pack(fill='x')
        ttk.Button(footer, text='Guardar', command=guardar).pack(side='right')
        ttk.Button(footer, text='Cancelar', command=dialog.destroy).pack(side='right', padx=(0, 8))

        dialog.protocol('WM_DELETE_WINDOW', dialog.destroy)

    def _recargar_incendios(self):
        self.lista.delete(0, 'end')
        incendios = obtener_incendios()
        if not incendios:
            self.lista.insert('end', 'No hay incendios registrados')
            self.lista.config(state='disabled')
            return

        self.lista.config(state='normal')
        for incendio in incendios:
            texto = f"{incendio[0]} - {incendio[1]} {incendio[2]} | {incendio[3]}"
            self.lista.insert('end', texto)

    def _seleccionar_ultimo_incendio(self):
        if self.lista.size() == 0:
            return
        if self.lista.get(0) == 'No hay incendios registrados':
            return
        self.lista.selection_clear(0, 'end')
        self.lista.selection_set(0)

    def _id_seleccionado(self):
        if self.lista.size() == 0:
            return None
        seleccion = self.lista.curselection()
        if not seleccion:
            if self.lista.get(0) == 'No hay incendios registrados':
                return None
            self.lista.selection_set(0)
            seleccion = self.lista.curselection()
        if not seleccion:
            return None
        texto = self.lista.get(seleccion[0])
        id_incendio = texto.split(' - ', 1)[0]
        try:
            return int(id_incendio)
        except (TypeError, ValueError):
            return None

    def generar_kml(self):
        id_incendio = self._id_seleccionado()
        if id_incendio is None:
            messagebox.showwarning('SIFO', 'Debe seleccionar un incendio antes de generar el KML.')
            return
        generar_kml(id_incendio)
        self._recargar_incendios()

    def generar_informe(self):
        id_incendio = self._id_seleccionado()
        if id_incendio is None:
            messagebox.showwarning('SIFO', 'Debe seleccionar un incendio antes de generar el informe.')
            return
        resultado = generar_informe_incendio(id_incendio)
        if resultado:
            messagebox.showinfo('SIFO', f'Informe generado:\nHTML: {resultado["html"]}\nPDF: {resultado["pdf"]}')

    def _ruta_archivo(self, extension):
        id_incendio = self._id_seleccionado()
        if id_incendio is None:
            incendios = obtener_incendios()
            if not incendios:
                messagebox.showwarning('SIFO', 'No hay incendios registrados.')
                return None
            id_incendio = incendios[0][0]

        incendio = obtener_incendio_por_id(id_incendio)

        if incendio is None:
            messagebox.showwarning('SIFO', 'No se encontró el incendio seleccionado.')
            return None

        nombre = (incendio[3] or f'Incendio {incendio[0]}').strip() or 'incendio'
        carpeta = KML_DIR if extension == '.kml' else INFORMES_DIR
        nombre_limpio = sanitizar_nombre_archivo(nombre, extension)
        rutas = [
            os.path.join(carpeta, nombre_limpio),
            os.path.join(carpeta, f'{nombre}{extension}'),
            os.path.join(carpeta, f'{nombre.strip()}{extension}'),
        ]

        for ruta in rutas:
            if os.path.exists(ruta):
                return os.path.abspath(ruta)

        if os.path.isdir(carpeta):
            nombre_base = os.path.splitext(nombre_limpio)[0].lower()
            for archivo in os.listdir(carpeta):
                if not archivo.lower().endswith(extension.lower()):
                    continue
                ruta_archivo = os.path.join(carpeta, archivo)
                if not os.path.isfile(ruta_archivo):
                    continue
                nombre_archivo = os.path.splitext(archivo)[0].lower()
                if (nombre_archivo == nombre_base or
                        nombre_archivo.replace('_', ' ') == nombre_base.replace('_', ' ') or
                        nombre_base in nombre_archivo or
                        nombre_archivo in nombre_base):
                    return os.path.abspath(ruta_archivo)

        messagebox.showwarning('SIFO', f'Aún no existe el archivo {extension.upper()} para este incendio.')
        return None

    def abrir_kml(self):
        ruta = self._ruta_archivo('.kml')
        if ruta:
            abrir_archivo(ruta)

    def abrir_pdf(self):
        ruta = self._ruta_archivo('.pdf')
        if ruta:
            abrir_archivo(ruta)

    def abrir_html(self):
        ruta = self._ruta_archivo('.html')
        if ruta:
            abrir_archivo(ruta)


def main_gui():

    if Tk is None:
        print('Tkinter no está disponible en este entorno.')
        return main_console()

    crear_carpetas()
    crear_base_datos()

    root = Tk()
    app = VentanaSIFO(root)
    root.mainloop()


# =====================================================
# MAIN
# =====================================================

def main_console():

    crear_carpetas()

    crear_base_datos()

    while True:

        mostrar_menu()

        opcion = input("Seleccione una opción: ")

        if opcion == "1":

            opcion_registrar()

        elif opcion == "2":

            opcion_listar()

        elif opcion == "3":

            opcion_generar_kml()

        elif opcion == "4":

            opcion_generar_informe()

        elif opcion == "5":

            print("\nGracias por utilizar SIFO.")
            break

        else:

            print("\nOpción incorrecta.")


# =====================================================
# INICIO
# =====================================================

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--console':
        main_console()
    else:
        main_gui()