import unittest
from core.generar_informe_pdf import _generar_estrategia_periodo


class TestGenerarInformePDF(unittest.TestCase):

    def test_generar_estrategia_vientos_extremos(self):
        meteo = {'temperatura': 35, 'humedad': 15, 'viento': 45, 'categoria_viento': 'Extremo'}
        topografia = {'maxima_pendiente_pct': 5}
        combustible = {'tipo_combustible': 'Pastizal'}

        estrategias = _generar_estrategia_periodo(meteo, topografia, combustible)
        self.assertGreater(len(estrategias), 0)
        self.assertTrue(any('EXTREMO' in e or 'VIENTO' in e for e in estrategias))

    def test_generar_estrategia_humedad_baja(self):
        meteo = {'temperatura': 28, 'humedad': 20, 'viento': 15, 'categoria_viento': 'Moderado'}
        topografia = {'maxima_pendiente_pct': 5}
        combustible = {'tipo_combustible': 'Bosque'}

        estrategias = _generar_estrategia_periodo(meteo, topografia, combustible)
        self.assertTrue(any('baja' in e.lower() for e in estrategias))

    def test_generar_estrategia_combustible_bosque(self):
        meteo = {'temperatura': 25, 'humedad': 45, 'viento': 20, 'categoria_viento': 'Moderado'}
        topografia = {'maxima_pendiente_pct': 12}
        combustible = {'tipo_combustible': 'Bosque'}

        estrategias = _generar_estrategia_periodo(meteo, topografia, combustible)
        self.assertTrue(any('BOSQUE' in e for e in estrategias))

    def test_generar_estrategia_terreno_pendiente(self):
        meteo = {'temperatura': 22, 'humedad': 50, 'viento': 10, 'categoria_viento': 'Bajo'}
        topografia = {'maxima_pendiente_pct': 25}
        combustible = {'tipo_combustible': 'Pastizal'}

        estrategias = _generar_estrategia_periodo(meteo, topografia, combustible)
        self.assertTrue(any('pendiente' in e.lower() or 'ascendente' in e.lower() for e in estrategias))


if __name__ == '__main__':
    unittest.main()
