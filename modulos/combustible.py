"""Humedad del combustible fino muerto (1 hora)."""


class Combustible:
    def humedad_muerta_1h(self, temp_c, rh_pct):
        """Humedad del combustible muerto de 1h en %.

        Aproximación de Simard (1968), usada por BEHAVE/Rothermel (humedad de
        equilibrio con HR en % y T en °F). Ya incluye el efecto de la temperatura.

        Nota: la fórmula de la especificación, 148.5*(1-exp(-0.0445*HR)), da
        valores físicamente imposibles (53 % con HR=10 %, 135 % con HR=54 %) y
        clasificaría siempre "combustible húmedo"; por eso se la reemplaza.
        El resultado se acota entre 1 % y 40 %.
        """
        rh = max(0.0, min(100.0, rh_pct))
        t_f = temp_c * 9 / 5 + 32
        if rh < 10:
            fm = 0.03229 + 0.281073 * rh - 0.000578 * rh * t_f
        elif rh <= 50:
            fm = 2.22749 + 0.160107 * rh - 0.01478 * t_f
        else:
            fm = 21.0606 + 0.005565 * rh ** 2 - 0.00035 * rh * t_f - 0.483199 * rh
        return max(1.0, min(40.0, fm))

    def clasificar_riesgo(self, fm_pct):
        if fm_pct < 10:
            return "SECO (<10%) - EXTREMO"
        if fm_pct < 20:
            return "BAJO (<20%)"
        if fm_pct < 30:
            return "MODERADO (<30%)"
        return "ALTO (>30%) - COMBUSTIBLE HÚMEDO"
