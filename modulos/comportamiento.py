"""Comportamiento del fuego: carreras primarias (viento + pendiente) y secundarias (quebradas)."""
import math

M_POR_GRADO = 111320.0
VEL_BASE_KMH = 0.5        # pastizal seco, referencia BEHAVE simplificada
FACTOR_ENCAUZAMIENTO = 1.3
MAX_EXTENSION_M = 2000.0
ANGULO_FLANCO = 40.0
MAX_QUEBRADAS = 5

REGLAS_QUEBRADA = [
    "El fuego corre aguas abajo siguiendo el cauce.",
    "Se acelera en las quebradas en V cerradas (efecto chimenea y encauzamiento del viento).",
    "Las chimeneas de calor lanzan pavesas y generan focos secundarios en las laderas.",
    "RIESGO EXTREMO para las brigadas dentro de la quebrada: no ingresar ni dejar personal en el fondo.",
]


def destino(lat, lon, rumbo_deg, dist_m):
    """Punto a dist_m metros del origen en el rumbo dado (0=N, 90=E)."""
    r = math.radians(rumbo_deg)
    dn = dist_m * math.cos(r)
    de = dist_m * math.sin(r)
    return (lat + dn / M_POR_GRADO,
            lon + de / (M_POR_GRADO * math.cos(math.radians(lat))))


def diferencia_angular(a, b):
    return abs((a - b + 180) % 360 - 180)


class ComportamientoFuego:
    def analizar_periodo(self, lat, lon, periodo, topo, barrancos):
        """Comportamiento del período. `topo` puede ser None si falló la topografía."""
        viento = periodo["viento_med_kmh"]
        hacia = (periodo["viento_dir_med_deg"] + 180) % 360  # el viento viene DE dir_med
        f_viento = max(min(viento / 10.0, 4.0), 0.2)

        if topo:
            pend = topo["pendiente_prom"]
            cuesta_arriba = (topo["aspecto_grados"] + 180) % 360
            f_pend_vec = min(pend / 10.0, 2.0)
        else:
            pend, cuesta_arriba, f_pend_vec = 0.0, None, 0.0

        # (a) empuje del viento + (b) subida de la ladera
        x = f_viento * math.sin(math.radians(hacia))
        y = f_viento * math.cos(math.radians(hacia))
        if cuesta_arriba is not None:
            x += f_pend_vec * math.sin(math.radians(cuesta_arriba))
            y += f_pend_vec * math.cos(math.radians(cuesta_arriba))
        direccion = math.degrees(math.atan2(x, y)) % 360

        sube = cuesta_arriba is not None and diferencia_angular(direccion, cuesta_arriba) < 90
        if cuesta_arriba is None:
            f_pend = 1.0
        else:
            f_pend = (1 + pend / 10.0) if sube else 0.7
        velocidad = VEL_BASE_KMH * f_viento * f_pend

        horas = periodo["fin_h"] - periodo["inicio_h"]
        extension = min(velocidad * 1000 * horas, MAX_EXTENSION_M)
        foco = (lat, lon)

        lineas = [{"tipo": "principal", "rumbo": direccion, "extension_m": extension,
                   "puntos": [foco, destino(lat, lon, direccion, extension)]}]
        # Flancos si la ladera empuja en otra dirección que el viento (laderas opuestas)
        if cuesta_arriba is not None and diferencia_angular(hacia, cuesta_arriba) >= 45:
            for signo in (-1, 1):
                rumbo = (direccion + signo * ANGULO_FLANCO) % 360
                lineas.append({"tipo": "flanco", "rumbo": rumbo, "extension_m": extension * 0.5,
                               "puntos": [foco, destino(lat, lon, rumbo, extension * 0.5)]})

        vel_sec = velocidad * FACTOR_ENCAUZAMIENTO
        secundarias = self._secundarias(lat, lon, barrancos, vel_sec, horas)

        return {
            "direccion_carrera_primaria_deg": direccion,
            "direccion_viento_hacia_deg": hacia,
            "fuego_sube_ladera": sube,
            "lineas_carrera_primaria": lineas,
            "lineas_carrera_secundaria": secundarias,
            "velocidad_estimada_kmh": velocidad,
            "velocidad_quebrada_kmh": vel_sec,
            "extension_primaria_m": extension,
            "reglas_quebrada": REGLAS_QUEBRADA,
        }

    def _secundarias(self, lat, lon, barrancos, vel_kmh, horas):
        """Quebradas más cercanas al foco, con su velocidad y alcance en el período."""
        if not barrancos:
            return []
        alcance = max(vel_kmh * 1000 * horas, 0)

        def dist_foco(linea):
            return min(math.hypot((la - lat) * M_POR_GRADO,
                                  (lo - lon) * M_POR_GRADO * math.cos(math.radians(lat)))
                       for la, lo in linea)

        cercanas = sorted(barrancos, key=dist_foco)[:MAX_QUEBRADAS]
        return [{"puntos": linea, "distancia_foco_m": dist_foco(linea),
                 "velocidad_kmh": vel_kmh, "alcance_m": alcance} for linea in cercanas]


# ---------------------------------------------------------------- expansión por horizontes
ANCHO_REL = 0.4  # ancho máximo / largo total
HORIZONTES = [
    {"clave": "inmediata", "nombre": "Expansión inmediata (0-9hs)", "desde": 0, "hasta": 9},
    {"clave": "9hs", "nombre": "Expansión >9hs", "desde": 9, "hasta": 21},
    {"clave": "24hs", "nombre": "Expansión 24hs", "desde": 21, "hasta": 24},
]


def _a_metros(lat0, lon0, lat, lon):
    """(norte, este) en metros de (lat, lon) respecto de (lat0, lon0)."""
    return ((lat - lat0) * M_POR_GRADO, (lon - lon0) * M_POR_GRADO * math.cos(math.radians(lat0)))


def _punto_en_poligono(lat, lon, poli):
    dentro = False
    n = len(poli)
    for i in range(n):
        la1, lo1 = poli[i]
        la2, lo2 = poli[(i + 1) % n]
        if (lo1 > lon) != (lo2 > lon) and lat < (la2 - la1) * (lon - lo1) / (lo2 - lo1) + la1:
            dentro = not dentro
    return dentro


def cauces_en_poligono(poli, cauces, paso_m=30.0):
    """Cantidad de cauces que cruzan el polígono (muestreo de cada polilínea cada paso_m)."""
    n = 0
    for cauce in cauces or []:
        hit = len(cauce) == 1 and _punto_en_poligono(cauce[0][0], cauce[0][1], poli)
        for (la1, lo1), (la2, lo2) in zip(cauce, cauce[1:]):
            if hit:
                break
            d = math.hypot((la2 - la1) * M_POR_GRADO,
                           (lo2 - lo1) * M_POR_GRADO * math.cos(math.radians(la1)))
            k = max(int(d / paso_m), 1)
            hit = any(_punto_en_poligono(la1 + (la2 - la1) * i / k, lo1 + (lo2 - lo1) * i / k, poli)
                      for i in range(k + 1))
        n += bool(hit)
    return n


def poligono_teardrop(lat0, lon0, tramos, n_muestras=40):
    """Gota alargada con el foco en el vértice trasero, siguiendo la estela de `tramos`
    [(rumbo_deg, dist_m), ...]. Devuelve (poligono cerrado [(lat, lon)], punta, largo_m)."""
    pts = [(0.0, 0.0)]  # estela en metros (norte, este) desde el foco
    for rumbo, d in tramos:
        r = math.radians(rumbo)
        pts.append((pts[-1][0] + d * math.cos(r), pts[-1][1] + d * math.sin(r)))
    largos = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])]
    largo = sum(largos)
    if largo <= 0:
        return [(lat0, lon0)] * 4, (lat0, lon0), 0.0

    def en_estela(s):
        acum = 0.0
        for i, l in enumerate(largos):
            if s <= acum + l or i == len(largos) - 1:
                f = 0.0 if l == 0 else min((s - acum) / l, 1.0)
                a, b = pts[i], pts[i + 1]
                tn, te = b[0] - a[0], b[1] - a[1]
                norma = math.hypot(tn, te) or 1.0
                return (a[0] + tn * f, a[1] + te * f), (tn / norma, te / norma)
            acum += l

    izq, der = [], []
    for k in range(n_muestras + 1):
        t = k / n_muestras
        (pn, pe), (tn, te) = en_estela(t * largo)
        semi = ANCHO_REL * largo / 2 * math.sin(math.pi * t ** 0.75)
        izq.append((pn - te * semi, pe + tn * semi))
        der.append((pn + te * semi, pe - tn * semi))
    contorno = izq + der[-2::-1]  # ida por un flanco, vuelta por el otro

    def a_geo(p):
        return (lat0 + p[0] / M_POR_GRADO, lon0 + p[1] / (M_POR_GRADO * math.cos(math.radians(lat0))))

    poli = [a_geo(p) for p in contorno]
    poli.append(poli[0])
    return poli, a_geo(pts[-1]), largo


def calcular_expansiones(lat, lon, periodos, cauces=None):
    """Tres horizontes acumulados; cada uno parte de la punta del anterior.
    `periodos`: lista de {'meteo', 'fm', 'comportamiento'} (resultados de analizar)."""
    resultado = []
    origen = (lat, lon)
    for h in HORIZONTES:
        sel = [p for p in periodos if h["desde"] <= p["meteo"]["inicio_h"] < h["hasta"]]
        if not sel:
            continue
        tramos = [(p["comportamiento"]["direccion_carrera_primaria_deg"],
                   p["comportamiento"]["velocidad_estimada_kmh"] * 1000 *
                   (p["meteo"]["fin_h"] - p["meteo"]["inicio_h"])) for p in sel]
        poli, punta, largo = poligono_teardrop(origen[0], origen[1], tramos)
        dn, de = _a_metros(lat, lon, punta[0], punta[1])
        rumbo_foco = math.degrees(math.atan2(de, dn)) % 360
        dn2, de2 = _a_metros(origen[0], origen[1], punta[0], punta[1])
        rumbo = math.degrees(math.atan2(de2, dn2)) % 360 if largo else rumbo_foco
        resultado.append({
            **h, "poligono": poli, "origen": origen, "punta": punta, "largo_m": largo,
            "ancho_max_m": ANCHO_REL * largo, "rumbo_deg": rumbo,
            "rumbo_foco_deg": rumbo_foco, "dist_foco_m": math.hypot(dn, de),
            "velocidad_media_kmh": sum(p["comportamiento"]["velocidad_estimada_kmh"] for p in sel) / len(sel),
            "fm_min": min(p["fm"] for p in sel),
            "viento_max_kmh": max(p["meteo"]["viento_med_kmh"] for p in sel),
            "sube_ladera": any(p["comportamiento"]["fuego_sube_ladera"] for p in sel),
            "cauces_cruzan": cauces_en_poligono(poli, cauces),
        })
        origen = punta
    return resultado
