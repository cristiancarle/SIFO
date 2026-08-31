"""
Generador de mapas interactivos con folium para SIFO
"""

import folium
from folium.plugins import HeatMap, MarkerCluster
import json
import os
import tempfile
from pathlib import Path

from modulos.generar_kml import _generar_carreras_potenciales


def crear_mapa_interactivo(incendios, carpeta_salida=None):
    """
    Crea un mapa interactivo con todos los incendios
    
    Args:
        incendios: lista de incendios desde la BD
        carpeta_salida: carpeta donde guardar el HTML (default: temp)
    
    Returns:
        ruta al archivo HTML generado
    """
    try:
        if not incendios:
            return None
        
        if carpeta_salida is None:
            carpeta_salida = tempfile.gettempdir()
        
        # Centro del mapa (promedio de coordenadas)
        lats = [inc[6] for inc in incendios if inc[6]]
        lons = [inc[7] for inc in incendios if inc[7]]
        
        if not lats or not lons:
            return None
        
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        
        # Crear mapa base
        mapa = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=6,
            tiles='OpenStreetMap'
        )
        
        # Agregar cluster de marcadores
        marker_cluster = MarkerCluster().add_to(mapa)
        
        # Agregar cada incendio
        for inc in incendios:
            lat, lon = inc[6], inc[7]
            if lat and lon:
                # Color según estado
                estado = inc[9]
                color = 'red' if estado == 'Activo' else 'orange' if estado == 'Controlado' else 'green'
                
                popup_text = f"""
                <b>{inc[3]}</b><br>
                Fecha: {inc[1]} {inc[2]}<br>
                Provincia: {inc[4]}<br>
                Localidad: {inc[5]}<br>
                Estado: {estado}
                """
                
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup(popup_text, max_width=250),
                    icon=folium.Icon(color=color, icon='fire', prefix='fa'),
                    tooltip=inc[3]
                ).add_to(marker_cluster)
        
        # Agregar heatmap
        heat_data = [[inc[6], inc[7]] for inc in incendios if inc[6] and inc[7]]
        if len(heat_data) > 2:
            HeatMap(heat_data, radius=25, blur=15, max_zoom=1).add_to(mapa)
        
        # Guardar
        archivo_salida = os.path.join(carpeta_salida, 'mapa_incendios.html')
        mapa.save(archivo_salida)
        
        return archivo_salida
        
    except Exception as e:
        print(f"Error al crear mapa: {e}")
        return None


def crear_mapa_carreras_potenciales(analisis_json, carpeta_salida=None):
    """
    Crea un mapa con las carreras potenciales del incendio usando los datos reales del análisis.
    """
    try:
        if not os.path.exists(analisis_json):
            return None

        with open(analisis_json, 'r', encoding='utf-8') as f:
            datos = json.load(f)

        if carpeta_salida is None:
            carpeta_salida = tempfile.gettempdir()
        os.makedirs(carpeta_salida, exist_ok=True)

        incendio = datos.get('incendio') or {}
        meteo = datos.get('meteorologia') or {}
        topografia = datos.get('topografia') or {}
        combustible = datos.get('combustible') or {}

        epicentro_lat = (
            incendio.get('latitud')
            or datos.get('latitud')
            or datos.get('ubicacion', {}).get('latitud')
            or -40
        )
        epicentro_lon = (
            incendio.get('longitud')
            or datos.get('longitud')
            or datos.get('ubicacion', {}).get('longitud')
            or -65
        )

        if not isinstance(meteo, dict):
            meteo = {}
        if not isinstance(topografia, dict):
            topografia = {}
        if not isinstance(combustible, dict):
            combustible = {}

        carreras = _generar_carreras_potenciales(epicentro_lat, epicentro_lon, meteo, topografia, combustible)

        mapa = folium.Map(
            location=[epicentro_lat, epicentro_lon],
            zoom_start=11,
            tiles='OpenStreetMap'
        )

        folium.Marker(
            location=[epicentro_lat, epicentro_lon],
            popup="🔥 Epicentro del Incendio",
            icon=folium.Icon(color='red', icon='fire', prefix='fa')
        ).add_to(mapa)

        for i, carrera in enumerate(carreras, 1):
            coords = carrera.get('coords', [])
            if len(coords) < 2:
                continue

            path = [[lat, lon] for lon, lat in coords]
            color = 'darkred' if carrera.get('tipo') == 'primaria' else 'orange'
            folium.PolyLine(
                path,
                color=color,
                weight=3,
                opacity=0.9,
                popup=f"{carrera.get('name', f'Carrera {i}') }"
            ).add_to(mapa)

            final_lat, final_lon = path[-1]
            folium.CircleMarker(
                location=[final_lat, final_lon],
                radius=7,
                popup=f"{carrera.get('name', f'Carrera {i}')}",
                color=color,
                fill=True,
                fillOpacity=0.8
            ).add_to(mapa)

        viento = meteo.get('viento')
        direccion = meteo.get('direccion_cardinal') or meteo.get('direccion')
        if viento is not None:
            folium.Marker(
                location=[epicentro_lat + 0.02, epicentro_lon],
                popup=f"Viento: {viento} km/h{f' desde {direccion}' if direccion is not None else ''}",
                icon=folium.Icon(color='blue', icon='wind', prefix='fa')
            ).add_to(mapa)

        mapa.fit_bounds([[epicentro_lat - 0.15, epicentro_lon - 0.15], [epicentro_lat + 0.15, epicentro_lon + 0.15]])

        archivo_salida = os.path.join(carpeta_salida, 'mapa_carreras_potenciales.html')
        mapa.save(archivo_salida)

        return archivo_salida

    except Exception as e:
        print(f"Error al crear mapa de carreras: {e}")
        return None
