"""
Generador de mapas interactivos con folium para SIFO
"""

import folium
from folium.plugins import HeatMap, MarkerCluster
import json
import os
import tempfile
from pathlib import Path


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
    Crea un mapa con las carreras potenciales del incendio
    
    Args:
        analisis_json: ruta al archivo JSON de análisis
        carpeta_salida: carpeta donde guardar el HTML
    
    Returns:
        ruta al archivo HTML generado
    """
    try:
        if not os.path.exists(analisis_json):
            return None
        
        with open(analisis_json, 'r', encoding='utf-8') as f:
            datos = json.load(f)
        
        if carpeta_salida is None:
            carpeta_salida = tempfile.gettempdir()
        
        # Centro del mapa
        epicentro_lat = datos.get('ubicacion', {}).get('latitud', -40)
        epicentro_lon = datos.get('ubicacion', {}).get('longitud', -65)
        
        # Crear mapa
        mapa = folium.Map(
            location=[epicentro_lat, epicentro_lon],
            zoom_start=11,
            tiles='OpenStreetMap'
        )
        
        # Marcador del epicentro
        folium.Marker(
            location=[epicentro_lat, epicentro_lon],
            popup="🔥 Epicentro del Incendio",
            icon=folium.Icon(color='red', icon='fire', prefix='fa')
        ).add_to(mapa)
        
        # Agregar carreras potenciales
        carreras = datos.get('analisis_propagacion', {}).get('carreras_potenciales', [])
        
        for i, carrera in enumerate(carreras, 1):
            # Dibujar línea de carrera
            coords = carrera.get('coordenadas', [])
            if coords:
                # Convertir a formato folium [lat, lon]
                path = [[c['latitud'], c['longitud']] for c in coords]
                
                folium.PolyLine(
                    path,
                    color='darkred' if carrera.get('prioridad') == 'Muy Alta' else 'red' if carrera.get('prioridad') == 'Alta' else 'orange',
                    weight=3,
                    opacity=0.8,
                    popup=f"Carrera {i}: {carrera.get('prioridad')}"
                ).add_to(mapa)
                
                # Marcador final de carrera
                ultima_coord = coords[-1]
                folium.CircleMarker(
                    location=[ultima_coord['latitud'], ultima_coord['longitud']],
                    radius=8,
                    popup=f"Carrera {i} - Proyección a 3h",
                    color='darkred' if carrera.get('prioridad') == 'Muy Alta' else 'red',
                    fill=True,
                    fillOpacity=0.7
                ).add_to(mapa)
        
        # Agregar información de viento
        if 'meteorologia' in datos:
            meteo = datos['meteorologia']
            viento = meteo.get('velocidad_viento', 0)
            direccion = meteo.get('direccion_viento', 'N/A')
            
            folium.Marker(
                location=[epicentro_lat + 0.02, epicentro_lon],
                popup=f"Viento: {viento} km/h desde {direccion}",
                icon=folium.Icon(color='blue', icon='cloud', prefix='fa')
            ).add_to(mapa)
        
        # Guardar
        archivo_salida = os.path.join(carpeta_salida, 'mapa_carreras_potenciales.html')
        mapa.save(archivo_salida)
        
        return archivo_salida
        
    except Exception as e:
        print(f"Error al crear mapa de carreras: {e}")
        return None
