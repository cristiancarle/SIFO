# MANUAL OPERATIVO — SIFO — Sistema Inteligente para Incendios Forestales

Este manual está dirigido al personal de brigadas y jefes de cuadrilla. Explica cómo leer el informe de 24 hs que produce el sistema y, sobre todo, **cómo traducir esa información en decisiones de seguridad**: cuándo entrar a trabajar, cuándo salir, y qué hacer (y qué no hacer) en quebradas y barrancos.

> El informe es una herramienta de planificación. Los valores de velocidad y extensión son **estimaciones** basadas en modelos simplificados. Ninguna cifra reemplaza el relevamiento en terreno ni el criterio del jefe de cuadrilla.

---

## 1. Cómo está organizado el informe

El informe cubre las próximas **24 horas divididas en 8 períodos de 3 horas**, contados desde la hora de generación (t0 = 0 hs): 0–3, 3–6, 6–9, 9–12, 12–15, 15–18, 18–21 y 21–24 hs.

Cada período presenta, en formato de **orden de trabajo**:

- **VENTANA**: la hora de entrada y hora de salida recomendadas (ej. 06:00 – 09:00).
- **Meteorología del período**: temperatura, humedad relativa, viento medio (velocidad y dirección), ráfaga máxima, precipitación y nubosidad.
- **Humedad del combustible y riesgo**.
- **Carreras primarias esperadas**: hacia dónde corre el fuego principal, a qué velocidad y cuánto puede avanzar.
- **Carreras secundarias en quebradas**: propagación por el fondo de barrancos, con su advertencia de seguridad.
- **RECOMENDACIÓN OPERATIVA**: hora de entrada, hora de salida y las razones.

Además, el archivo KML se abre en Google Earth y muestra sobre el terreno: el foco, la dirección del viento (línea azul), las carreras primarias (rojas) y las carreras por quebrada (naranjas), organizadas por período.

## 2. Cómo leer el clima de cada período

| Dato | Qué mirar | Por qué importa |
|---|---|---|
| Viento medio y ráfagas | Dirección (de dónde viene) y km/h | El viento es el principal impulsor del fuego; las ráfagas definen la intensidad de las carreras |
| Temperatura y humedad relativa | Valores por período | Baja humedad relativa = combustible que se seca a lo largo del día |
| Precipitación | mm del período | Lluvia puede frenar o contener la propagación |
| Nubosidad | % de cobertura | Nubes bajas moderan el calentamiento y retrasan el secado |

**Regla general**: el viento suele intensificarse desde el mediodía, con pico entre las 12 y las 17 hs. Esa es la franja más peligrosa.

## 3. Humedad del combustible fino muerto (1 hora)

Es el % de humedad del material fino muerto (pasto seco, hojarasca fina, ramas de menos de 6 mm). Es el combustible que **primero se enciende y más rápido propaga**.

El informe clasifica el riesgo así:

| Humedad (fm) | Clasificación | Lectura operativa |
|---|---|---|
| < 10% | **SECO — EXTREMO** | Ignición casi instantánea, propagación explosiva. No ejecutar ataques directos en pastizal |
| 10–20% | **BAJO** (riesgo bajo de humedad, pero no de fuego) | Combustible seco y receptivo |
| 20–30% | **MODERADO** | El fuego propaga pero con menos intensidad |
| > 30% | **ALTO — COMBUSTIBLE HÚMEDO** | Propagación lenta o nula; buena ventana para trabajos directos |

El combustible está típicamente más húmedo de madrugada (por rocío y humedad relativa alta) y más seco entre las 13 y las 17 hs. El informe refleja este ciclo en los valores de cada período.

## 4. Carreras primarias

Son las **carreras principales del fuego**: la dirección hacia la que se propaga el frente principal, resultado de combinar la **empuje del viento** con la **pendiente de la ladera dominante** (el fuego sube ladera abajo→arriba, siempre más rápido cuesta arriba que cuesta abajo).

En el informe y en el KML se indican:

- **Dirección** (grados y punto cardinal): hacia dónde avanza el frente principal.
- **Velocidad estimada** (km/h): referencia de planificación, base en pastizal seco ajustada por viento y pendiente.
- **Extensión esperada** por período: cuánto puede avanzar el frente en esas 3 horas.

El KML dibuja la carrera principal y hasta dos flancos laterales si hay laderas opuestas.

**Cómo usarlas**: ubique siempre las carreras primarias respecto de su posición de trabajo y de sus vías de escape. **Nunca trabaje frente a una carrera primaria a favor del viento o cuesta arriba** sin ruta de escape despejada y puntos de seguridad identificados.

## 5. Carreras secundarias: quebradas y barrancos

Son las carreras que corren **por el fondo de quebradas y barrancos**, detectadas sobre el modelo de elevación. Son especialmente traicioneras porque el terreno las oculta y porque se comportan de manera previsible pero extrema:

- **El fuego corre aguas abajo del cauce**, acelerando conforme el cauce se encajona.
- En **V cerradas** (barrancos angostos con paredes empinadas) la velocidad aumenta notablemente.
- **Chimeneas de calor**: el quebradón funciona como un horno vertical. El calor y los gases ascienden por el fondo, precalentando el combustible aguas arriba del cauce y generando igniciones aguas arriba de la posición del fuego principal. La chimenea puede "arrastrar" el fuego en pocos minutos desde el fondo hasta la coronación de ambas laderas.
- **Encauzamiento del viento**: el viento que corre a ras en general se canaliza por el quebradón y sopla más fuerte y alineado con el cauce que en el terreno abierto. El sistema aplica un factor de aceleración de **1.3x** sobre la velocidad base por este efecto.
- Los dos flancos del fuego dentro de la quebrada **suben simultáneamente por ambas laderas**: una brigada en el fondo puede quedar rodeada en minutos.

En el informe, cada carrera secundaria lleva su **advertencia de seguridad**. En el KML se ven como líneas **naranjas** siguiendo los fondos de quebrada.

**Regla dura**: si el trabajo está dentro o sobre el borde de una quebrada marcada en naranja, la operación se define como de alto riesgo y requiere autorización expresa del jefe de cuadrilla, con escape alto y lateral — nunca por el fondo.

## 6. Ventanas de entrada y salida (la regla de oro)

El corazón del informe es la recomendación de **HORA DE ENTRADA** y **HORA DE SALIDA** de cada período. La lógica es siempre la misma:

### Cuándo entrar

- En **ventanas de baja intensidad**: madrugada y amanecer (típicamente 04:00 – 10:00), cuando la humedad del combustible está alta, el viento es bajo y la temperatura aún no subió.
- Cuando la ráfaga máxima del período es menor a **40 km/h**.
- Cuando la humedad del combustible no está en categoría extrema.
- Fuera de las quebradas cuando el viento es fuerte.

### Cuándo salir

- **Antes del pico de viento y de calor, típicamente entre las 12 y las 17 hs.** Salir no significa retirarse a las 12:00: significa **salir con margen**, de forma de estar fuera del sector (o pasados a posiciones seguras) antes de que el viento gire y cargue.
- Cuando el informe anuncia que las condiciones se agravan (aumento de ráfagas, combustible llegando a extremo, cambio de dirección del viento).
- Al cierre de la ventana recomendada, sin excepciones, aun si la tarea quedó inconclusa. La tarea se retoma en la próxima ventana.

### Reglas operativas fijas

1. **Entrar temprano, salir antes del pico.** El trabajo de mayor rendimiento se hace de madrugada; las horas críticas se usan para reabastecer, descansar y reorganizar.
2. **No operar en quebradas** durante períodos de viento fuerte o con combustible en categoría extrema.
3. Identificar siempre **dos vías de escape** y **zonas de seguridad** antes de entrar, y mantener comunicación de la cuadrilla con el jefe de operaciones.
4. Si el informe marca carreras secundarias en naranja cerca del sector de trabajo, **no comprometer personal dentro del cauce** bajo ninguna condición de viento.

## 7. Ejemplo de lectura de un período

> **Período 9–12 hs** — Viento NE 18 km/h, ráfagas 32 km/h, 31 °C, HR 28%. Combustible: fm 11% (BAJO). Carrera primaria hacia el SSO a 1.2 km/h. Carrera secundaria en quebrada al O del foco (advertencia: chimenea de calor).
> **Recomendación**: entrada 09:00, **salida 11:30** — salir antes del pico de viento de las 12–15 hs.

Lectura: es la última ventana útil del día. Entrar temprano en el período, trabajar en la ladera a sotavento del viento NE, no entrar al quebradón del O, y retirar la cuadrilla con media hora de margen antes del mediodía.

## 8. Recordatorio final

- El informe ordena la información; la **decisión es del jefe de cuadrilla** con el terreno a la vista.
- Ante condiciones que difieran del pronóstico (viento que gira y cargue inesperadamente, columna de humo que se verticaliza y colapsa), la regla es una: **salir y reevaluar**.
- Fuego en quebrada con viento fuerte: **no se combatía desde adentro; se combate desde arriba y afuera.**
