"""
Generador de gráficos de meteorología para la interfaz SIFO
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import tkinter as tk
from datetime import datetime, timedelta
import json
import os
from pathlib import Path


def _normalizar_pronostico(datos):
    if isinstance(datos, list):
        return datos

    if not isinstance(datos, dict):
        return []

    for clave in ('datos_horarios', 'horarios', 'datos', 'pronostico_24h_horario'):
        valor = datos.get(clave)
        if isinstance(valor, list):
            return valor

    valor = datos.get('pronostico_24h')
    if isinstance(valor, list):
        return valor
    if isinstance(valor, dict):
        for clave in ('datos_horarios', 'horarios', 'datos', 'serie'):
            subvalor = valor.get(clave)
            if isinstance(subvalor, list):
                return subvalor
    return []


def crear_grafico_meteorologia(datos_json, frame_padre):
    """
    Crea gráficos interactivos de meteorología en tkinter
    
    Args:
        datos_json: ruta al archivo JSON de análisis
        frame_padre: frame de tkinter donde insertar el gráfico
    """
    try:
        with open(datos_json, 'r', encoding='utf-8') as f:
            datos = json.load(f)

        pronostico = _normalizar_pronostico(datos)
        if not pronostico:
            ruta_json = Path(datos_json).with_name('pronostico_24h.json')
            if ruta_json.exists():
                with open(ruta_json, 'r', encoding='utf-8') as f:
                    pronostico = _normalizar_pronostico(json.load(f))

        if not pronostico:
            tk.Label(frame_padre, text="No hay datos disponibles", fg='red').pack()
            return

        # Extraer datos
        horas = []
        temperaturas = []
        humedad = []
        velocidad_viento = []

        for dato in pronostico:
            hora_val = dato.get('hora') or dato.get('time') or dato.get('fecha_hora')
            if not hora_val:
                continue

            try:
                if isinstance(hora_val, str) and 'T' in hora_val:
                    hora = datetime.fromisoformat(hora_val.replace('Z', '+00:00')).strftime('%H:%M')
                elif isinstance(hora_val, str):
                    hora = hora_val
                else:
                    hora = str(hora_val)
            except ValueError:
                hora = str(hora_val)

            horas.append(hora)
            temperaturas.append(float(dato.get('temperatura', dato.get('temperature_2m', 0))))
            humedad.append(float(dato.get('humedad', dato.get('relativehumidity_2m', 0))))
            velocidad_viento.append(float(dato.get('viento', dato.get('velocidad_viento', dato.get('windspeed_10m', 0)))))
        
        # Crear figura con subplots
        fig = Figure(figsize=(12, 8), dpi=100)
        
        # Subplot 1: Temperatura y Humedad
        ax1 = fig.add_subplot(311)
        ax1.set_title('Temperatura y Humedad Relativa - 24h', fontsize=12, fontweight='bold')
        ax1.plot(range(len(horas)), temperaturas, marker='o', color='red', label='Temperatura (°C)', linewidth=2)
        ax1.set_ylabel('Temperatura (°C)', color='red')
        ax1.tick_params(axis='y', labelcolor='red')
        ax1.grid(True, alpha=0.3)
        
        ax1_twin = ax1.twinx()
        ax1_twin.plot(range(len(horas)), humedad, marker='s', color='blue', label='Humedad (%)', linewidth=2)
        ax1_twin.set_ylabel('Humedad (%)', color='blue')
        ax1_twin.tick_params(axis='y', labelcolor='blue')
        
        # Leyenda combinada
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax1_twin.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        # Subplot 2: Velocidad del Viento
        ax2 = fig.add_subplot(312)
        ax2.set_title('Velocidad del Viento - 24h', fontsize=12, fontweight='bold')
        colores = ['green' if v < 10 else 'orange' if v < 20 else 'red' for v in velocidad_viento]
        ax2.bar(range(len(horas)), velocidad_viento, color=colores, alpha=0.7)
        ax2.set_ylabel('Velocidad (km/h)')
        ax2.axhline(y=20, color='orange', linestyle='--', alpha=0.5, label='Riesgo moderado')
        ax2.axhline(y=35, color='red', linestyle='--', alpha=0.5, label='Riesgo alto')
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis='y')
        
        # Subplot 3: Índice de Riesgo (composición de factores)
        ax3 = fig.add_subplot(313)
        ax3.set_title('Índice de Riesgo de Incendio - 24h', fontsize=12, fontweight='bold')
        
        # Calcular índice de riesgo (0-100)
        indice_riesgo = []
        for i in range(len(horas)):
            # Mayor temperatura = más riesgo
            riesgo_temp = (temperaturas[i] / 40) * 30  # Max 30 puntos
            # Menor humedad = más riesgo
            riesgo_humedad = ((100 - humedad[i]) / 100) * 30  # Max 30 puntos
            # Mayor viento = más riesgo
            riesgo_viento = (velocidad_viento[i] / 50) * 40  # Max 40 puntos
            
            indice = min(100, riesgo_temp + riesgo_humedad + riesgo_viento)
            indice_riesgo.append(indice)
        
        colores_riesgo = ['green' if r < 30 else 'yellow' if r < 50 else 'orange' if r < 70 else 'red' for r in indice_riesgo]
        ax3.fill_between(range(len(horas)), indice_riesgo, alpha=0.3, color='red')
        ax3.plot(range(len(horas)), indice_riesgo, marker='D', color='darkred', linewidth=2)
        ax3.set_ylabel('Índice de Riesgo (0-100)')
        ax3.set_ylim(0, 100)
        ax3.axhline(y=30, color='green', linestyle=':', alpha=0.5, label='Bajo')
        ax3.axhline(y=50, color='yellow', linestyle=':', alpha=0.5, label='Moderado')
        ax3.axhline(y=70, color='orange', linestyle=':', alpha=0.5, label='Alto')
        ax3.legend(loc='upper left')
        ax3.grid(True, alpha=0.3)
        
        # Configurar eje X para todos
        for ax in [ax1, ax2, ax3]:
            ax.set_xticks(range(0, len(horas), 3))
            ax.set_xticklabels([horas[i] if i < len(horas) else '' for i in range(0, len(horas), 3)], rotation=45)
        
        ax3.set_xlabel('Hora')
        
        fig.tight_layout()
        
        # Insertar en tkinter
        canvas = FigureCanvasTkAgg(fig, master=frame_padre)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    except Exception as e:
        tk.Label(frame_padre, text=f"Error al cargar gráficos: {str(e)}", fg='red').pack()


def crear_grafico_estadisticas(incendios, frame_padre):
    """
    Crea gráficos de estadísticas generales
    
    Args:
        incendios: lista de incendios desde la BD
        frame_padre: frame de tkinter donde insertar el gráfico
    """
    try:
        if not incendios:
            tk.Label(frame_padre, text="No hay incendios registrados", fg='orange').pack()
            return
        
        fig = Figure(figsize=(12, 6), dpi=100)
        
        # Contar incendios por mes
        meses = {}
        provincias = {}
        
        for inc in incendios:
            fecha_str = inc[1]  # Formato dd/mm/yyyy
            try:
                fecha = datetime.strptime(fecha_str, "%d/%m/%Y")
                mes = fecha.strftime("%b")
                meses[mes] = meses.get(mes, 0) + 1
            except:
                pass
            
            provincia = inc[4]
            provincias[provincia] = provincias.get(provincia, 0) + 1
        
        # Subplot 1: Incendios por mes
        ax1 = fig.add_subplot(121)
        meses_ordenados = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        meses_datos = [meses.get(m, 0) for m in meses_ordenados]
        ax1.bar(meses_ordenados, meses_datos, color='orangered', alpha=0.7)
        ax1.set_title('Incendios por Mes', fontweight='bold')
        ax1.set_ylabel('Cantidad')
        ax1.grid(True, alpha=0.3, axis='y')
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # Subplot 2: Incendios por provincia (top 10)
        ax2 = fig.add_subplot(122)
        provincias_top = sorted(provincias.items(), key=lambda x: x[1], reverse=True)[:10]
        prov_nombres = [p[0] for p in provincias_top]
        prov_counts = [p[1] for p in provincias_top]
        
        ax2.barh(prov_nombres, prov_counts, color='firebrick', alpha=0.7)
        ax2.set_title('Incendios por Provincia (Top 10)', fontweight='bold')
        ax2.set_xlabel('Cantidad')
        ax2.grid(True, alpha=0.3, axis='x')
        
        fig.tight_layout()
        
        # Insertar en tkinter
        canvas = FigureCanvasTkAgg(fig, master=frame_padre)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    except Exception as e:
        tk.Label(frame_padre, text=f"Error al crear estadísticas: {str(e)}", fg='red').pack()
