from datetime import datetime, timedelta

from modulos.licencia import _machine_id, activar_licencia, crear_codigo_licencia


def test_crear_y_validar_licencia():
    maquina = _machine_id()
    fecha_expiracion = datetime.now() + timedelta(days=30)
    codigo = crear_codigo_licencia(fecha_expiracion, maquina)

    assert codigo.startswith("SIFO-")

    ok, mensaje = activar_licencia(codigo)
    assert ok is True
    assert "Licencia activada" in mensaje
