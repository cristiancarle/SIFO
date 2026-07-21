from dataclasses import dataclass

@dataclass
class Incendio:

    id: int
    fecha: str
    latitud: float
    longitud: float
    descripcion: str