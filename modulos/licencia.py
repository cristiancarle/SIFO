import hashlib
import hmac
import json
import os
import platform
import uuid
from datetime import datetime, timedelta
from pathlib import Path

TRIAL_DAYS = 30
LICENCIA_SECRETO = b"SIFO-RENOVACION-MENSUAL-2026"

LOCAL_APP_DATA = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
LICENCIA_DIR = Path(LOCAL_APP_DATA) / "SIFO"
LICENCIA_FILE = LICENCIA_DIR / "licencia.json"


def _machine_id() -> str:
    raw = f"{platform.node()}|{uuid.getnode()}|{platform.system()}|{platform.release()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16].upper()


def _firmar(payload: str) -> str:
    return hmac.new(LICENCIA_SECRETO, payload.encode("utf-8"), hashlib.sha256).hexdigest()[:16].upper()


def crear_codigo_licencia(fecha_expiracion: datetime | None = None, machine_id: str | None = None) -> str:
    """Genera una clave de licencia mensual asociada al equipo."""
    if fecha_expiracion is None:
        fecha_expiracion = datetime.now() + timedelta(days=30)

    machine = (machine_id or _machine_id()).upper()
    fecha = fecha_expiracion.strftime("%Y%m%d")
    payload = f"{machine}|{fecha}"
    firma = _firmar(payload)
    return f"SIFO-{machine}-{fecha}-{firma}"


def _guardar_estado(data: dict):
    LICENCIA_DIR.mkdir(parents=True, exist_ok=True)
    with open(LICENCIA_FILE, "w", encoding="utf-8") as archivo:
        json.dump(data, archivo, ensure_ascii=False, indent=2)


def _estado_default() -> dict:
    ahora = datetime.now()
    return {
        "tipo": "trial",
        "fecha_instalacion": ahora.isoformat(timespec="seconds"),
        "expira_en": (ahora + timedelta(days=TRIAL_DAYS)).isoformat(timespec="seconds"),
        "maquina": _machine_id(),
    }


def inicializar_licencia() -> dict:
    if not LICENCIA_FILE.exists():
        estado = _estado_default()
        _guardar_estado(estado)
        return estado

    with open(LICENCIA_FILE, "r", encoding="utf-8") as archivo:
        try:
            estado = json.load(archivo)
        except json.JSONDecodeError:
            estado = _estado_default()
            _guardar_estado(estado)
        return estado


def activar_licencia(codigo: str) -> tuple[bool, str]:
    """Activa la licencia si la clave es válida y corresponde al equipo actual."""
    clave = codigo.strip().upper().replace(" ", "-")
    partes = clave.split("-")

    if len(partes) != 4 or partes[0] != "SIFO":
        return False, "El formato de la clave no es válido."

    machine = partes[1]
    fecha = partes[2]
    firma = partes[3]

    if len(machine) < 8 or len(fecha) != 8 or len(firma) < 8:
        return False, "La clave no cumple el formato esperado."

    try:
        fecha_dt = datetime.strptime(fecha, "%Y%m%d")
    except ValueError:
        return False, "La fecha de la licencia no es válida."

    payload = f"{machine}|{fecha}"
    firma_esperada = _firmar(payload)

    if not hmac.compare_digest(firma_esperada, firma):
        return False, "La clave no coincide con la firma válida."

    maquina_actual = _machine_id()
    if maquina_actual != machine:
        return False, "La clave no corresponde a este equipo."

    if fecha_dt < datetime.now():
        return False, "La licencia ya venció. Debe renovarla para continuar."

    nuevo_estado = {
        "tipo": "licencia",
        "fecha_activacion": datetime.now().isoformat(timespec="seconds"),
        "expira_en": fecha_dt.isoformat(timespec="seconds"),
        "maquina": maquina_actual,
    }
    _guardar_estado(nuevo_estado)
    return True, f"Licencia activada correctamente hasta {fecha_dt.strftime('%d/%m/%Y')}."


def estado_licencia() -> dict:
    """Retorna el estado con un indicador true/false para dejar arrancar la app."""
    estado = inicializar_licencia()
    ahora = datetime.now()

    tipo = estado.get("tipo", "trial")
    if tipo == "licencia":
        expira = estado.get("expira_en")
        if not expira:
            return {"permitido": False, "tipo": "trial", "mensaje": "La licencia no tiene fecha de vencimiento."}
        fecha_exp = datetime.fromisoformat(expira)
        if fecha_exp <= ahora:
            return {"permitido": False, "tipo": "licencia", "mensaje": "La licencia venció. Debe renovarla."}
        return {"permitido": True, "tipo": "licencia", "mensaje": f"Licencia válida hasta {fecha_exp.strftime('%d/%m/%Y')}."}

    fecha_instalacion = datetime.fromisoformat(estado.get("fecha_instalacion", datetime.now().isoformat()))
    expira_trial = datetime.fromisoformat(estado.get("expira_en", (datetime.now() + timedelta(days=TRIAL_DAYS)).isoformat()))

    if ahora <= expira_trial:
        return {
            "permitido": True,
            "tipo": "trial",
            "mensaje": f"Modo prueba vigente. Le quedan { (expira_trial - ahora).days + 1 } días.",
            "dias_restantes": max((expira_trial - ahora).days, 0),
        }

    return {
        "permitido": False,
        "tipo": "trial",
        "mensaje": "La prueba gratuita venció. Debe ingresar una licencia activa para continuar.",
    }


def requiere_activacion() -> bool:
    return not estado_licencia()["permitido"]


def solicitar_activacion_por_consola() -> bool:
    print("\nLa licencia no está activa.")
    print("Es necesario activar la aplicación para continuar.")
    print("Puede ingresar una clave de renovación mensual, por ejemplo: SIFO-XXXX-YYYYMMDD-XXXXXXXXXXXX")

    try:
        clave = input("Ingrese su código de licencia: ").strip()
    except EOFError:
        return False
    except KeyboardInterrupt:
        return False

    ok, mensaje = activar_licencia(clave)
    print(f"\n{mensaje}")
    return ok


def solicitar_activacion_por_gui() -> bool:
    try:
        import tkinter as tk
        from tkinter import messagebox, simpledialog
    except Exception:
        return solicitar_activacion_por_consola()

    ventana = tk.Tk()
    ventana.withdraw()
    ventana.attributes("-topmost", True)

    estado = estado_licencia()
    if estado["permitido"]:
        ventana.destroy()
        return True

    messagebox.showwarning(
        "Licencia requerida",
        f"{estado['mensaje']}\n\nIngrese su clave de activación o renovación mensual para continuar."
    )

    clave = simpledialog.askstring(
        "Activación de SIFO",
        "Ingrese su código de licencia mensual:\nEjemplo: SIFO-XXXX-YYYYMMDD-XXXXXXXXXXXX",
        parent=ventana,
    )
    ventana.destroy()

    if not clave:
        return False

    ok, mensaje = activar_licencia(clave)
    if ok:
        messagebox.showinfo("Licencia activada", mensaje)
        return True

    messagebox.showerror("Licencia inválida", mensaje)
    return False
