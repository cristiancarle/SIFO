# Instalador profesional para SIFO

Este directorio contiene la preparación para generar un instalador Windows profesional para la aplicación SIFO.

## Requisitos

- Python 3.10 o superior
- PowerShell
- Inno Setup (opcional si querés compilar también el instalador `.exe`)

## Generación del ejecutable

Desde la raíz del proyecto:

```powershell
powershell -ExecutionPolicy Bypass -File .\installer\build_installer.ps1
```

Eso hará lo siguiente:

- crea un entorno virtual temporal `.venv-installer`
- instala las dependencias de [requirements.txt](../requirements.txt)
- instala PyInstaller
- genera el ejecutable en `installer\dist\SIFO\SIFO.exe`
- si Inno Setup está instalado, compila el instalador en `installer\output\SIFO-Setup.exe`

## Resultado esperado

- ejecutable de la app: `installer\dist\SIFO\SIFO.exe`
- instalador Windows: `installer\output\SIFO-Setup.exe`

## Qué incluye el instalador

- copia la aplicación a `C:\Program Files\SIFO`
- crea acceso directo en el menú Inicio
- crea acceso directo en el escritorio
- lanza la app automáticamente al finalizar la instalación
- incluye un sistema de activación con prueba de 30 días y bloqueo si la licencia vence

## Licencia y suscripción mensual

La aplicación se inicia en modo prueba durante 30 días. Cuando vence:

- bloquea el arranque
- solicita una clave de licencia
- si el cliente paga la membresía mensual, se le entrega una clave nueva
- la clave se valida contra el equipo actual y la fecha de vencimiento

Esto permite mantener un esquema tipo suscripción mensual sin necesidad de instalar Python en la máquina destino.

## Nota importante

La salida final del instalador es la opción recomendada para una PC sin Python instalada.

La aplicación queda empacada con todas sus dependencias y recursos para evitar que el usuario tenga que ejecutar `pip install -r requirements.txt` manualmente.
