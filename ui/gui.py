import os
import json
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from modulos.database import (
    crear_base_datos,
    registrar_incendio,
    listar_incendios,
    obtener_incendios,
    obtener_incendio_por_id
)
from modulos.generar_kml import generar_kml
from core.analizador import analizar_incendio, analizar_coordenadas
from modulos.utilidades import crear_carpetas
from ui.graficos import crear_grafico_meteorologia, crear_grafico_estadisticas
from ui.mapa_interactivo import crear_mapa_interactivo, crear_mapa_carreras_potenciales


class SIFOApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("SIFO - Sistema Inteligente para Incendios Forestales")
        self.geometry("900x700")
        self.resizable(True, True)

        try:
            self.style = ttk.Style()
            self.style.theme_use('clam')
            self.style.configure('Title.TLabel', font=('Arial', 16, 'bold'), foreground='#CC0000')
            self.style.configure('Subtitle.TLabel', font=('Arial', 12, 'bold'), foreground='#333333')
            self.style.configure('Danger.TButton', font=('Arial', 10))
        except Exception:
            self.style = None

        crear_carpetas()
        crear_base_datos()

        self._create_widgets()

    def _create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(header_frame, text="🔥 SIFO", style='Title.TLabel').pack()
        ttk.Label(header_frame, text="Sistema Inteligente para Incendios Forestales", style='Subtitle.TLabel').pack()

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_registrar = ttk.Frame(notebook)
        self.tab_listar = ttk.Frame(notebook)
        self.tab_generar_kml = ttk.Frame(notebook)
        self.tab_analizar = ttk.Frame(notebook)
        self.tab_graficos = ttk.Frame(notebook)
        self.tab_mapa = ttk.Frame(notebook)
        self.tab_historial = ttk.Frame(notebook)
        self.tab_dashboard = ttk.Frame(notebook)

        notebook.add(self.tab_registrar, text="📝 Registrar Incendio")
        notebook.add(self.tab_listar, text="📋 Listar Incendios")
        notebook.add(self.tab_generar_kml, text="🗺️ Generar KML")
        notebook.add(self.tab_analizar, text="📊 Analizar Incendio")
        notebook.add(self.tab_graficos, text="📈 Gráficos")
        notebook.add(self.tab_mapa, text="🌍 Mapa Interactivo")
        notebook.add(self.tab_historial, text="📚 Historial")
        notebook.add(self.tab_dashboard, text="📉 Dashboard")

        self._create_tab_registrar()
        self._create_tab_listar()
        self._create_tab_generar_kml()
        self._create_tab_analizar()
        self._create_tab_graficos()
        self._create_tab_mapa()
        self._create_tab_historial()
        self._create_tab_dashboard()

    def _create_tab_registrar(self):
        frame = ttk.Frame(self.tab_registrar, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Registrar Nuevo Incendio", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 15))

        form_frame = ttk.LabelFrame(frame, text="Datos del Incendio", padding="10")
        form_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(form_frame, text="Fecha (dd/mm/aaaa):").grid(row=0, column=0, sticky=tk.W, pady=5)
        fecha_entry = ttk.Entry(form_frame, width=20)
        fecha_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))
        fecha_entry.grid(row=0, column=1, sticky=tk.EW, padx=10, pady=5)

        ttk.Label(form_frame, text="Hora (hh:mm):").grid(row=1, column=0, sticky=tk.W, pady=5)
        hora_entry = ttk.Entry(form_frame, width=20)
        hora_entry.insert(0, datetime.now().strftime("%H:%M"))
        hora_entry.grid(row=1, column=1, sticky=tk.EW, padx=10, pady=5)

        ttk.Label(form_frame, text="Nombre del Incendio:").grid(row=2, column=0, sticky=tk.W, pady=5)
        nombre_entry = ttk.Entry(form_frame, width=20)
        nombre_entry.grid(row=2, column=1, sticky=tk.EW, padx=10, pady=5)

        ttk.Label(form_frame, text="Provincia:").grid(row=3, column=0, sticky=tk.W, pady=5)
        provincia_entry = ttk.Entry(form_frame, width=20)
        provincia_entry.grid(row=3, column=1, sticky=tk.EW, padx=10, pady=5)

        ttk.Label(form_frame, text="Localidad:").grid(row=4, column=0, sticky=tk.W, pady=5)
        localidad_entry = ttk.Entry(form_frame, width=20)
        localidad_entry.grid(row=4, column=1, sticky=tk.EW, padx=10, pady=5)

        ttk.Label(form_frame, text="Latitud:").grid(row=5, column=0, sticky=tk.W, pady=5)
        lat_entry = ttk.Entry(form_frame, width=20)
        lat_entry.grid(row=5, column=1, sticky=tk.EW, padx=10, pady=5)

        ttk.Label(form_frame, text="Longitud:").grid(row=6, column=0, sticky=tk.W, pady=5)
        lon_entry = ttk.Entry(form_frame, width=20)
        lon_entry.grid(row=6, column=1, sticky=tk.EW, padx=10, pady=5)

        ttk.Label(form_frame, text="Descripción:").grid(row=7, column=0, sticky=tk.NW, pady=5)
        desc_text = tk.Text(form_frame, height=4, width=20)
        desc_text.grid(row=7, column=1, sticky=tk.EW, padx=10, pady=5)

        form_frame.columnconfigure(1, weight=1)

        def guardar_incendio():
            try:
                registrar_incendio(
                    fecha_entry.get(),
                    hora_entry.get(),
                    nombre_entry.get(),
                    provincia_entry.get(),
                    localidad_entry.get(),
                    float(lat_entry.get()),
                    float(lon_entry.get()),
                    desc_text.get("1.0", tk.END)
                )
                messagebox.showinfo("Éxito", "✅ Incendio registrado correctamente.")
                fecha_entry.delete(0, tk.END)
                fecha_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))
                hora_entry.delete(0, tk.END)
                hora_entry.insert(0, datetime.now().strftime("%H:%M"))
                nombre_entry.delete(0, tk.END)
                provincia_entry.delete(0, tk.END)
                localidad_entry.delete(0, tk.END)
                lat_entry.delete(0, tk.END)
                lon_entry.delete(0, tk.END)
                desc_text.delete("1.0", tk.END)
            except ValueError as e:
                messagebox.showerror("Error", f"Coordenadas inválidas: {e}")
            except Exception as e:
                messagebox.showerror("Error", f"Error al registrar: {e}")

        ttk.Button(frame, text="💾 Guardar Incendio", command=guardar_incendio).pack(pady=10)

    def _create_tab_listar(self):
        frame = ttk.Frame(self.tab_listar, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Listado de Incendios Registrados", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 15))

        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_incendios = ttk.Treeview(
            tree_frame,
            columns=("ID", "Fecha", "Hora", "Nombre", "Provincia", "Localidad", "Estado"),
            height=15,
            yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=self.tree_incendios.yview)

        self.tree_incendios.column("#0", width=0, stretch=tk.NO)
        self.tree_incendios.column("ID", anchor=tk.W, width=40)
        self.tree_incendios.column("Fecha", anchor=tk.W, width=80)
        self.tree_incendios.column("Hora", anchor=tk.W, width=60)
        self.tree_incendios.column("Nombre", anchor=tk.W, width=100)
        self.tree_incendios.column("Provincia", anchor=tk.W, width=100)
        self.tree_incendios.column("Localidad", anchor=tk.W, width=100)
        self.tree_incendios.column("Estado", anchor=tk.W, width=80)

        self.tree_incendios.heading("#0", text="", anchor=tk.W)
        self.tree_incendios.heading("ID", text="ID", anchor=tk.W)
        self.tree_incendios.heading("Fecha", text="Fecha", anchor=tk.W)
        self.tree_incendios.heading("Hora", text="Hora", anchor=tk.W)
        self.tree_incendios.heading("Nombre", text="Nombre", anchor=tk.W)
        self.tree_incendios.heading("Provincia", text="Provincia", anchor=tk.W)
        self.tree_incendios.heading("Localidad", text="Localidad", anchor=tk.W)
        self.tree_incendios.heading("Estado", text="Estado", anchor=tk.W)

        self.tree_incendios.pack(fill=tk.BOTH, expand=True)

        def recargar_lista():
            self.tree_incendios.delete(*self.tree_incendios.get_children())
            incendios = listar_incendios()
            for incendio in incendios:
                self.tree_incendios.insert("", tk.END, values=(
                    incendio[0],
                    incendio[1],
                    incendio[2],
                    incendio[3],
                    incendio[4],
                    incendio[5],
                    incendio[9]
                ))

        ttk.Button(frame, text="🔄 Recargar Lista", command=recargar_lista).pack(pady=10)

        recargar_lista()

    def _create_tab_generar_kml(self):
        frame = ttk.Frame(self.tab_generar_kml, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Generar Mapa KML", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 15))

        select_frame = ttk.LabelFrame(frame, text="Seleccionar Incendio", padding="10")
        select_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(select_frame, text="Incendio:").pack(anchor=tk.W, pady=(0, 5))

        self.combo_incendios_kml = ttk.Combobox(select_frame, state='readonly', width=50)
        self.combo_incendios_kml.pack(fill=tk.X, pady=(0, 10))

        def recargar_combo():
            incendios = obtener_incendios()
            opciones = [
                f"{inc[0]} - {inc[1]} {inc[2]} | {inc[3]}"
                for inc in incendios
            ]
            self.combo_incendios_kml['values'] = opciones

        def generar():
            if not self.combo_incendios_kml.get():
                messagebox.showwarning("Advertencia", "Seleccione un incendio.")
                return

            id_incendio = int(self.combo_incendios_kml.get().split(" - ")[0])

            def proceso():
                try:
                    generar_kml(id_incendio)
                    messagebox.showinfo("Éxito", "✅ KML generado correctamente.")
                except Exception as e:
                    messagebox.showerror("Error", f"Error al generar KML: {e}")

            thread = threading.Thread(target=proceso)
            thread.daemon = True
            thread.start()

        ttk.Button(select_frame, text="🔄 Recargar Incendios", command=recargar_combo).pack(pady=5)
        ttk.Button(frame, text="🗺️ Generar KML", command=generar).pack(pady=10)

        recargar_combo()

    def _create_tab_analizar(self):
        frame = ttk.Frame(self.tab_analizar, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Analizar Incendio (Generar Informe 24h)", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 15))

        option_frame = ttk.LabelFrame(frame, text="Opciones de Análisis", padding="10")
        option_frame.pack(fill=tk.X, pady=(0, 15))

        self.var_opcion = tk.StringVar(value="registrado")

        ttk.Radiobutton(option_frame, text="Usar Incendio Registrado", variable=self.var_opcion, value="registrado").pack(anchor=tk.W, pady=5)
        ttk.Radiobutton(option_frame, text="Ingresar Coordenadas Manualmente", variable=self.var_opcion, value="manual").pack(anchor=tk.W, pady=5)

        self.frame_registrado = ttk.LabelFrame(frame, text="Incendio Registrado", padding="10")
        self.frame_registrado.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(self.frame_registrado, text="Incendio:").pack(anchor=tk.W, pady=(0, 5))
        self.combo_incendios_analisis = ttk.Combobox(self.frame_registrado, state='readonly', width=50)
        self.combo_incendios_analisis.pack(fill=tk.X, pady=(0, 10))

        def recargar_combo_analisis():
            incendios = obtener_incendios()
            opciones = [
                f"{inc[0]} - {inc[1]} {inc[2]} | {inc[3]}"
                for inc in incendios
            ]
            self.combo_incendios_analisis['values'] = opciones

        ttk.Button(self.frame_registrado, text="🔄 Recargar", command=recargar_combo_analisis).pack(pady=5)
        recargar_combo_analisis()

        self.frame_manual = ttk.LabelFrame(frame, text="Coordenadas Manuales", padding="10")

        ttk.Label(self.frame_manual, text="Nombre:").grid(row=0, column=0, sticky=tk.W, pady=5)
        nombre_manual = ttk.Entry(self.frame_manual, width=30)
        nombre_manual.grid(row=0, column=1, sticky=tk.EW, padx=10, pady=5)

        ttk.Label(self.frame_manual, text="Provincia:").grid(row=1, column=0, sticky=tk.W, pady=5)
        provincia_manual = ttk.Entry(self.frame_manual, width=30)
        provincia_manual.grid(row=1, column=1, sticky=tk.EW, padx=10, pady=5)

        ttk.Label(self.frame_manual, text="Localidad:").grid(row=2, column=0, sticky=tk.W, pady=5)
        localidad_manual = ttk.Entry(self.frame_manual, width=30)
        localidad_manual.grid(row=2, column=1, sticky=tk.EW, padx=10, pady=5)

        ttk.Label(self.frame_manual, text="Latitud:").grid(row=3, column=0, sticky=tk.W, pady=5)
        lat_manual = ttk.Entry(self.frame_manual, width=30)
        lat_manual.grid(row=3, column=1, sticky=tk.EW, padx=10, pady=5)

        ttk.Label(self.frame_manual, text="Longitud:").grid(row=4, column=0, sticky=tk.W, pady=5)
        lon_manual = ttk.Entry(self.frame_manual, width=30)
        lon_manual.grid(row=4, column=1, sticky=tk.EW, padx=10, pady=5)

        ttk.Label(self.frame_manual, text="Descripción:").grid(row=5, column=0, sticky=tk.NW, pady=5)
        desc_manual = tk.Text(self.frame_manual, height=3, width=30)
        desc_manual.grid(row=5, column=1, sticky=tk.EW, padx=10, pady=5)

        self.frame_manual.columnconfigure(1, weight=1)

        def actualizar_visibilidad(event=None):
            if self.var_opcion.get() == "registrado":
                self.frame_registrado.pack(fill=tk.X, pady=(0, 15))
                self.frame_manual.pack_forget()
            else:
                self.frame_registrado.pack_forget()
                self.frame_manual.pack(fill=tk.X, pady=(0, 15))

        self.var_opcion.trace('w', actualizar_visibilidad)
        actualizar_visibilidad()

        def analizar():
            def proceso():
                try:
                    if self.var_opcion.get() == "registrado":
                        if not self.combo_incendios_analisis.get():
                            messagebox.showwarning("Advertencia", "Seleccione un incendio.")
                            return
                        id_incendio = int(self.combo_incendios_analisis.get().split(" - ")[0])
                        resultado = analizar_incendio(id_incendio)
                    else:
                        if not all([nombre_manual.get(), provincia_manual.get(), localidad_manual.get(), lat_manual.get(), lon_manual.get()]):
                            messagebox.showwarning("Advertencia", "Complete todos los campos.")
                            return
                        resultado = analizar_coordenadas(
                            nombre_manual.get(),
                            provincia_manual.get(),
                            localidad_manual.get(),
                            float(lat_manual.get()),
                            float(lon_manual.get()),
                            desc_manual.get("1.0", tk.END)
                        )

                    if resultado:
                        analisis, carpeta = resultado
                        messagebox.showinfo(
                            "Análisis Completado",
                            f"✅ Análisis completado exitosamente.\n\n"
                            f"Resultados guardados en:\n{carpeta}\n\n"
                            f"Se generó:\n"
                            f"- Informe de 24 horas (PDF)\n"
                            f"- Análisis JSON\n"
                            f"- Datos meteorológicos\n"
                            f"- Datos topográficos"
                        )
                    else:
                        messagebox.showerror("Error", "No se pudo completar el análisis.")
                except ValueError as e:
                    messagebox.showerror("Error", f"Coordenadas o datos inválidos: {e}")
                except Exception as e:
                    messagebox.showerror("Error", f"Error durante análisis: {e}")

            thread = threading.Thread(target=proceso)
            thread.daemon = True
            thread.start()

        ttk.Button(frame, text="📊 Analizar Incendio", command=analizar).pack(pady=10)

    def _create_tab_graficos(self):
        frame = ttk.Frame(self.tab_graficos, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Gráficos de Meteorología (24h)", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 15))

        info_frame = ttk.LabelFrame(frame, text="Seleccionar Análisis", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(info_frame, text="Carpeta de análisis:").pack(anchor=tk.W, pady=(0, 5))

        self.combo_graficos = ttk.Combobox(info_frame, state='readonly', width=60)
        self.combo_graficos.pack(fill=tk.X, pady=(0, 10))

        def recargar_analisis():
            self.combo_graficos['values'] = []
            carpeta_analisis = Path('analisis')
            if carpeta_analisis.exists():
                carpetas = sorted([f.name for f in carpeta_analisis.iterdir() if f.is_dir()], reverse=True)
                self.combo_graficos['values'] = carpetas

        def cargar_grafico():
            if not self.combo_graficos.get():
                messagebox.showwarning("Advertencia", "Seleccione un análisis.")
                return

            archivo_json = Path('analisis') / self.combo_graficos.get() / 'analisis.json'

            if not archivo_json.exists():
                messagebox.showerror("Error", "No se encontró el archivo de análisis.")
                return

            # Limpiar canvas anterior
            for widget in self.tab_graficos.winfo_children():
                if isinstance(widget, tk.Frame) and widget != frame:
                    widget.destroy()

            # Crear frame para gráficos
            graph_frame = ttk.Frame(self.tab_graficos)
            graph_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            def proceso():
                try:
                    crear_grafico_meteorologia(str(archivo_json), graph_frame)
                except Exception as e:
                    messagebox.showerror("Error", f"Error al cargar gráficos: {e}")

            thread = threading.Thread(target=proceso)
            thread.daemon = True
            thread.start()

        ttk.Button(info_frame, text="🔄 Recargar Análisis", command=recargar_analisis).pack(pady=5)
        ttk.Button(frame, text="📈 Cargar Gráficos", command=cargar_grafico).pack(pady=10)

        recargar_analisis()

    def _create_tab_mapa(self):
        frame = ttk.Frame(self.tab_mapa, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Mapa Interactivo de Incendios", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 15))

        # Botones de opciones
        btn_frame = ttk.LabelFrame(frame, text="Opciones de Visualización", padding="10")
        btn_frame.pack(fill=tk.X, pady=(0, 15))

        def crear_mapa_general():
            try:
                incendios = listar_incendios()
                if not incendios:
                    messagebox.showwarning("Advertencia", "No hay incendios registrados.")
                    return

                archivo_mapa = crear_mapa_interactivo(incendios)
                if archivo_mapa:
                    webbrowser.open('file://' + os.path.realpath(archivo_mapa))
                    messagebox.showinfo("Éxito", "✅ Mapa abierto en navegador.")
                else:
                    messagebox.showerror("Error", "No se pudo crear el mapa.")
            except Exception as e:
                messagebox.showerror("Error", f"Error al crear mapa: {e}")

        def crear_mapa_carrera():
            carpeta_analisis = Path('analisis')
            if not carpeta_analisis.exists() or not list(carpeta_analisis.iterdir()):
                messagebox.showwarning("Advertencia", "No hay análisis disponibles.")
                return

            carpetas = sorted([f.name for f in carpeta_analisis.iterdir() if f.is_dir()], reverse=True)

            window = tk.Toplevel(self)
            window.title("Seleccionar Análisis")
            window.geometry("400x150")

            ttk.Label(window, text="Seleccione un análisis:").pack(pady=10)

            combo = ttk.Combobox(window, values=carpetas, state='readonly', width=40)
            combo.pack(pady=10)

            def procesar():
                if not combo.get():
                    messagebox.showwarning("Advertencia", "Seleccione un análisis.")
                    return

                archivo_json = Path('analisis') / combo.get() / 'analisis.json'

                if not archivo_json.exists():
                    messagebox.showerror("Error", "No se encontró el análisis.")
                    return

                try:
                    archivo_mapa = crear_mapa_carreras_potenciales(str(archivo_json))
                    if archivo_mapa:
                        webbrowser.open('file://' + os.path.realpath(archivo_mapa))
                        messagebox.showinfo("Éxito", "✅ Mapa de carreras abierto.")
                        window.destroy()
                    else:
                        messagebox.showerror("Error", "No se pudo crear el mapa.")
                except Exception as e:
                    messagebox.showerror("Error", f"Error: {e}")

            ttk.Button(window, text="📍 Abrir Mapa", command=procesar).pack(pady=10)

        ttk.Button(btn_frame, text="🗺️ Mapa General de Incendios", command=crear_mapa_general).pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="🔥 Mapa de Carreras Potenciales", command=crear_mapa_carrera).pack(fill=tk.X, pady=5)

        info_label = ttk.Label(frame, text="💡 Los mapas se abrirán en tu navegador web. Usa el zoom para explorar.", foreground='blue')
        info_label.pack(anchor=tk.W, pady=10)

    def _create_tab_historial(self):
        frame = ttk.Frame(self.tab_historial, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Historial de Incendios", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 15))

        # Filtros
        filter_frame = ttk.LabelFrame(frame, text="Filtros de Búsqueda", padding="10")
        filter_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(filter_frame, text="Buscar por nombre:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        busqueda_entry = ttk.Entry(filter_frame, width=30)
        busqueda_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)

        ttk.Label(filter_frame, text="Provincia:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        provincia_combo = ttk.Combobox(filter_frame, state='readonly', width=28)
        provincia_combo.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)

        ttk.Label(filter_frame, text="Estado:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        estado_combo = ttk.Combobox(filter_frame, values=['Activo', 'Controlado', 'Extinguido'], state='readonly', width=28)
        estado_combo.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=5)

        filter_frame.columnconfigure(1, weight=1)

        # Tabla
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_historial = ttk.Treeview(
            tree_frame,
            columns=("ID", "Fecha", "Hora", "Nombre", "Provincia", "Localidad", "Estado"),
            height=15,
            yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=self.tree_historial.yview)

        self.tree_historial.column("#0", width=0, stretch=tk.NO)
        self.tree_historial.column("ID", anchor=tk.W, width=40)
        self.tree_historial.column("Fecha", anchor=tk.W, width=80)
        self.tree_historial.column("Hora", anchor=tk.W, width=60)
        self.tree_historial.column("Nombre", anchor=tk.W, width=120)
        self.tree_historial.column("Provincia", anchor=tk.W, width=100)
        self.tree_historial.column("Localidad", anchor=tk.W, width=100)
        self.tree_historial.column("Estado", anchor=tk.W, width=80)

        self.tree_historial.heading("#0", text="", anchor=tk.W)
        self.tree_historial.heading("ID", text="ID", anchor=tk.W)
        self.tree_historial.heading("Fecha", text="Fecha", anchor=tk.W)
        self.tree_historial.heading("Hora", text="Hora", anchor=tk.W)
        self.tree_historial.heading("Nombre", text="Nombre", anchor=tk.W)
        self.tree_historial.heading("Provincia", text="Provincia", anchor=tk.W)
        self.tree_historial.heading("Localidad", text="Localidad", anchor=tk.W)
        self.tree_historial.heading("Estado", text="Estado", anchor=tk.W)

        self.tree_historial.pack(fill=tk.BOTH, expand=True)

        def cargar_incendios():
            self.tree_historial.delete(*self.tree_historial.get_children())
            incendios = listar_incendios()

            busqueda = busqueda_entry.get().lower()
            provincia = provincia_combo.get()
            estado = estado_combo.get()

            for inc in incendios:
                if busqueda and busqueda not in inc[3].lower():
                    continue
                if provincia and inc[4] != provincia:
                    continue
                if estado and inc[9] != estado:
                    continue

                self.tree_historial.insert("", tk.END, values=(
                    inc[0],
                    inc[1],
                    inc[2],
                    inc[3],
                    inc[4],
                    inc[5],
                    inc[9]
                ))

        # Actualizar provincias disponibles
        def actualizar_provincias():
            incendios = listar_incendios()
            provincias = sorted(set(inc[4] for inc in incendios if inc[4]))
            provincia_combo['values'] = ['Todas'] + provincias

        ttk.Button(frame, text="🔍 Filtrar", command=cargar_incendios).pack(side=tk.LEFT, padx=5, pady=10)
        ttk.Button(frame, text="🔄 Limpiar Filtros", command=lambda: [
            busqueda_entry.delete(0, tk.END),
            provincia_combo.set('Todas'),
            estado_combo.set(''),
            cargar_incendios()
        ]).pack(side=tk.LEFT, padx=5, pady=10)

        actualizar_provincias()
        cargar_incendios()

    def _create_tab_dashboard(self):
        frame = ttk.Frame(self.tab_dashboard, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Dashboard - Estadísticas Generales", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 15))

        # Estadísticas resumidas
        stats_frame = ttk.LabelFrame(frame, text="Resumen General", padding="15")
        stats_frame.pack(fill=tk.X, pady=(0, 20))

        incendios = listar_incendios()

        # Crear grid de estadísticas
        stats = [
            ("Total de Incendios", len(incendios)),
            ("Activos", len([i for i in incendios if i[9] == 'Activo'])),
            ("Controlados", len([i for i in incendios if i[9] == 'Controlado'])),
            ("Extinguidos", len([i for i in incendios if i[9] == 'Extinguido'])),
        ]

        for idx, (label, valor) in enumerate(stats):
            stat_frame = ttk.Frame(stats_frame)
            stat_frame.grid(row=idx // 2, column=idx % 2, padx=20, pady=15, sticky=tk.EW)

            ttk.Label(stat_frame, text=label, font=('Arial', 10)).pack()
            ttk.Label(stat_frame, text=str(valor), font=('Arial', 20, 'bold'), foreground='#CC0000').pack()

        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)

        # Gráficos
        graph_frame = ttk.LabelFrame(frame, text="Análisis Visuales", padding="10")
        graph_frame.pack(fill=tk.BOTH, expand=True)

        def cargar_graficos():
            for widget in graph_frame.winfo_children():
                widget.destroy()

            crear_grafico_estadisticas(incendios, graph_frame)

        ttk.Button(frame, text="📊 Generar Gráficos", command=cargar_graficos).pack(pady=10)


def main():
    try:
        app = SIFOApp()
        app.mainloop()
    except Exception as exc:
        print(f"No se pudo abrir la interfaz gráfica: {exc}")
