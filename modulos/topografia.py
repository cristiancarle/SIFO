"""Topografía: DEM (OpenTopoData SRTM 90m), pendiente, aspecto y red de cauces D8."""
import json
import math
import os
import time

import requests

from .meteo import ErrorAPI, DIR_CACHE

URL = "https://api.opentopodata.org/v1/srtm90m"
LOTE = 100
PAUSA_S = 1.1
M_POR_GRADO = 111320.0
VECINOS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


class Topografia:
    def __init__(self):
        self.lat = self.lon = None
        self.radio_m = self.lado = None
        self.dem = None
        self.paso_m = None
        self._cauces = None
        self._calculo = None

    # ---------- Geometría de la grilla ----------
    def _coord(self, i, j):
        """lat/lon de la celda (fila i de norte a sur, columna j de oeste a este)."""
        paso = self.paso_m
        dn = self.radio_m - i * paso
        de = -self.radio_m + j * paso
        lat = self.lat + dn / M_POR_GRADO
        lon = self.lon + de / (M_POR_GRADO * math.cos(math.radians(self.lat)))
        return lat, lon

    # ---------- DEM ----------
    def get_dem(self, lat, lon, radio_m=3000, lado=25):
        """Matriz lado x lado de alturas (m) centrada en (lat, lon). Cacheada en disco."""
        self.lat, self.lon, self.radio_m, self.lado = lat, lon, radio_m, lado
        self.paso_m = 2 * radio_m / (lado - 1)
        self._cauces = self._calculo = None
        os.makedirs(DIR_CACHE, exist_ok=True)
        ruta = os.path.join(DIR_CACHE, f"dem_{lat:.4f}_{lon:.4f}_{radio_m}_{lado}.json")
        if os.path.exists(ruta):
            try:
                with open(ruta, encoding="utf-8") as f:
                    self.dem = json.load(f)
                return self.dem
            except (OSError, ValueError):
                pass

        puntos = [self._coord(i, j) for i in range(lado) for j in range(lado)]
        alturas = []
        for k in range(0, len(puntos), LOTE):
            if k:
                time.sleep(PAUSA_S)
            alturas.extend(self._consultar_lote(puntos[k:k + LOTE]))

        validas = [a for a in alturas if a is not None]
        if not validas:
            raise ErrorAPI("OpenTopoData no devolvió alturas para esta zona.")
        relleno = sum(validas) / len(validas)
        alturas = [relleno if a is None else a for a in alturas]
        self.dem = [alturas[i * lado:(i + 1) * lado] for i in range(lado)]
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(self.dem, f)
        return self.dem

    def _consultar_lote(self, pts):
        loc = "|".join(f"{la:.6f},{lo:.6f}" for la, lo in pts)
        ultimo = None
        for intento in range(3):
            try:
                r = requests.get(URL, params={"locations": loc}, timeout=30)
                if r.status_code == 429:
                    ultimo = "demasiadas solicitudes (HTTP 429)"
                    time.sleep(PAUSA_S * 2)
                    continue
                r.raise_for_status()
                datos = r.json()
                if datos.get("status") != "OK":
                    raise ErrorAPI(f"OpenTopoData respondió: {datos.get('error', datos)}")
                res = datos["results"]
                if len(res) != len(pts):
                    raise ErrorAPI("OpenTopoData devolvió una cantidad inesperada de puntos.")
                return [p.get("elevation") for p in res]
            except ErrorAPI:
                raise
            except (requests.RequestException, ValueError, KeyError) as e:
                ultimo = str(e)
                time.sleep(PAUSA_S)
        raise ErrorAPI(f"No se pudo obtener la topografía de OpenTopoData: {ultimo}")

    # ---------- Análisis ----------
    def _gradiente(self, i, j):
        n, d, p = self.lado, self.dem, self.paso_m
        j0, j1 = max(j - 1, 0), min(j + 1, n - 1)
        i0, i1 = max(i - 1, 0), min(i + 1, n - 1)
        dzde = (d[i][j1] - d[i][j0]) / ((j1 - j0) * p)
        dzdn = (d[i0][j] - d[i1][j]) / ((i1 - i0) * p)  # filas crecen hacia el sur
        return dzde, dzdn

    def _flujo_d8(self):
        """Receptor D8 de cada celda y acumulación de flujo (nº de celdas aportantes)."""
        n, d = self.lado, self.dem
        receptor = {}
        for i in range(n):
            for j in range(n):
                mejor, mejor_pend = None, 0.0
                for di, dj in VECINOS:
                    a, b = i + di, j + dj
                    if 0 <= a < n and 0 <= b < n:
                        pend = (d[i][j] - d[a][b]) / (math.hypot(di, dj) * self.paso_m)
                        if pend > mejor_pend:
                            mejor, mejor_pend = (a, b), pend
                receptor[(i, j)] = mejor
        acc = {(i, j): 1 for i in range(n) for j in range(n)}
        for (i, j) in sorted(acc, key=lambda c: -d[c[0]][c[1]]):
            r = receptor[(i, j)]
            if r:
                acc[r] += acc[(i, j)]
        return receptor, acc

    def calcular(self):
        """Pendiente, aspecto dominante y red de cauces del DEM."""
        if self.dem is None:
            raise ErrorAPI("Primero hay que llamar a get_dem().")
        n = self.lado
        pendientes, vx, vy = [], 0.0, 0.0
        for i in range(n):
            for j in range(n):
                dzde, dzdn = self._gradiente(i, j)
                tg = math.hypot(dzde, dzdn)
                pendientes.append(math.degrees(math.atan(tg)))
                # vector hacia donde mira la ladera (cuesta abajo), ponderado por pendiente
                vx += -dzde
                vy += -dzdn
        pend_pct = [math.tan(math.radians(p)) * 100 for p in pendientes]
        aspecto = math.degrees(math.atan2(vx, vy)) % 360 if (vx or vy) else 0.0
        self._cauces = self._red_de_cauces()
        ext = sum(self._largo_m(c) for c in self._cauces)
        self._calculo = {
            "pendiente_max": max(pend_pct),
            "pendiente_prom": sum(pend_pct) / len(pend_pct),
            "aspecto_grados": aspecto,
            "celdas_pendiente_grados": [pendientes[i * n:(i + 1) * n] for i in range(n)],
            "red_de_cauces": self._cauces,
            "extension_quebradas_m": ext,
            "altura_min": min(min(f) for f in self.dem),
            "altura_max": max(max(f) for f in self.dem),
        }
        return self._calculo

    def _red_de_cauces(self):
        n = self.lado
        receptor, acc = self._flujo_d8()
        umbral = max(5, int(0.03 * n * n))
        cauce = {c for c, a in acc.items() if a >= umbral and receptor[c]}
        con_aporte = {receptor[c] for c in cauce if receptor[c] in cauce}
        cabeceras = [c for c in cauce if c not in con_aporte]
        # Orden por altura descendente: las cabeceras más altas primero
        cabeceras.sort(key=lambda c: -self.dem[c[0]][c[1]])
        visitadas, lineas = set(), []
        for c in cabeceras:
            linea = [c]
            visitadas.add(c)
            while True:
                r = receptor[linea[-1]]
                if r is None:
                    break
                linea.append(r)
                if r in visitadas or r not in cauce:
                    break
                visitadas.add(r)
            if len(linea) >= 3:
                lineas.append([self._coord(i, j) for i, j in linea])
        return lineas

    @staticmethod
    def _largo_m(linea):
        t = 0.0
        for (la1, lo1), (la2, lo2) in zip(linea, linea[1:]):
            dn = (la2 - la1) * M_POR_GRADO
            de = (lo2 - lo1) * M_POR_GRADO * math.cos(math.radians(la1))
            t += math.hypot(dn, de)
        return t

    def identificar_barrancos(self):
        """Polilíneas [(lat, lon), ...] de fondos de quebrada, ordenadas aguas abajo."""
        if self._cauces is None:
            self.calcular()
        return self._cauces
