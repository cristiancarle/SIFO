import unittest

from modulos.generar_kml import (
    _calcular_coordenadas,
    _direccion_propagacion_viento,
    _distancia_posible,
    _generar_carreras_potenciales
)


class TestGenerarKML(unittest.TestCase):

    def test_calcular_coordenadas_orientacion(self):
        lat, lon = _calcular_coordenadas(0.0, 0.0, 1000, 90)
        self.assertAlmostEqual(lat, 0.0, places=6)
        self.assertGreater(lon, 0.0089)

    def test_direccion_propagacion_viento(self):
        self.assertEqual(_direccion_propagacion_viento({'direccion': 0}), 180)
        self.assertEqual(_direccion_propagacion_viento({'direccion': 270}), 90)
        self.assertIsNone(_direccion_propagacion_viento({'direccion': None}))

    def test_distancia_posible_increases_with_risk(self):
        base = _distancia_posible({'viento': 5}, {'tipo_combustible': 'Desconocido'}, {'maxima_pendiente_pct': 0})
        high_risk = _distancia_posible({'viento': 30}, {'tipo_combustible': 'Bosque'}, {'maxima_pendiente_pct': 20})
        self.assertGreater(high_risk, base)

    def test_generar_carreras_potenciales_with_full_data(self):
        meteo = {'direccion': 45, 'viento': 30}
        topografia = {'maxima_pendiente_pct': 20, 'pendiente_direccion': 315}
        combustible = {'tipo_combustible': 'Bosque'}
        carreras = _generar_carreras_potenciales(-33.45, -70.65, meteo, topografia, combustible)

        self.assertTrue(len(carreras) >= 4)
        for carrera in carreras:
            self.assertIn('name', carrera)
            self.assertIn('coords', carrera)
            self.assertEqual(len(carrera['coords']), 2)
            self.assertEqual(len(carrera['coords'][0]), 2)


if __name__ == '__main__':
    unittest.main()
