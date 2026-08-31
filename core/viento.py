import math


def grados_a_cardinal(grados):
    direcciones = [
        "Norte", "Noreste", "Este", "Sudeste",
        "Sur", "Sudoeste", "Oeste", "Noroeste"
    ]

    indice = round(grados / 45) % 8
    return direcciones[indice]


def direccion_flecha(grados):
    flechas = [
        "↑", "↗", "→", "↘",
        "↓", "↙", "←", "↖"
    ]

    indice = round(grados / 45) % 8
    return flechas[indice]


def clasificar_viento(velocidad):

    if velocidad < 10:
        return "Bajo"

    if velocidad < 25:
        return "Moderado"

    if velocidad < 40:
        return "Alto"

    return "Extremo"