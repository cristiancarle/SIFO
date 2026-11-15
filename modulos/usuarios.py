"""Usuarios de SIFO: registro, login y administración (PostgreSQL o SQLite, ver db.py).

Estados: 'pendiente' (se registró, espera aprobación), 'activo', 'inactivo'.
Roles: 'admin' (aprueba/gestiona usuarios) y 'usuario'.
"""
import re
from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from . import db

USUARIO_RE = re.compile(r"[A-Za-z0-9_.-]{3,30}")
EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
CLAVE_MIN = 10

# Hash fijo para igualar tiempos cuando el usuario no existe (evita enumerar usuarios).
_HASH_FALSO = generate_password_hash("sifo-usuario-inexistente")


def iniciar_db(admin_usuario="", admin_clave="", admin_clave_hash=""):
    """Crea las tablas y, si se pasan credenciales de admin, asegura que esa cuenta exista y esté activa."""
    db.iniciar()
    if admin_usuario and (admin_clave or admin_clave_hash):
        h = admin_clave_hash or generate_password_hash(admin_clave)
        fila = _por_usuario(admin_usuario)
        if fila:
            db.ejecutar("UPDATE usuarios SET clave_hash = ?, rol = 'admin', estado = 'activo' WHERE id = ?",
                        (h, fila["id"]))
        else:
            db.ejecutar("INSERT INTO usuarios (usuario, nombre, clave_hash, rol, estado, creado) "
                        "VALUES (?, 'Administrador', ?, 'admin', 'activo', ?)", (admin_usuario, h, _ahora()))


def _por_usuario(usuario):
    return db.ejecutar("SELECT * FROM usuarios WHERE lower(usuario) = lower(?)", (usuario or "",), uno=True)


def _ahora():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def validar_registro(usuario, nombre, email, clave, clave2):
    """Devuelve una lista de errores (vacía si todo está bien)."""
    errores = []
    if not USUARIO_RE.fullmatch(usuario or ""):
        errores.append("El usuario debe tener entre 3 y 30 caracteres (letras, números, punto, guion o guion bajo).")
    if not (nombre or "").strip():
        errores.append("Ingresá tu nombre y apellido.")
    if not EMAIL_RE.fullmatch(email or ""):
        errores.append("El email no es válido.")
    if len(clave or "") < CLAVE_MIN:
        errores.append(f"La contraseña debe tener al menos {CLAVE_MIN} caracteres.")
    if clave != clave2:
        errores.append("Las contraseñas no coinciden.")
    return errores


def registrar(usuario, nombre, email, clave):
    """Crea el usuario en estado 'pendiente'. False si el nombre de usuario ya existe."""
    if _por_usuario(usuario):
        return False
    try:
        db.ejecutar("INSERT INTO usuarios (usuario, nombre, email, clave_hash, creado) VALUES (?, ?, ?, ?, ?)",
                    (usuario, nombre.strip()[:100], email.strip()[:150], generate_password_hash(clave), _ahora()))
        return True
    except db.ErrorIntegridad:
        return False


def autenticar(usuario, clave):
    """Devuelve (fila, motivo). motivo: 'ok', 'credenciales', 'pendiente', 'inactivo'."""
    u = _por_usuario(usuario)
    if u is None:
        check_password_hash(_HASH_FALSO, clave or "")
        return None, "credenciales"
    if not check_password_hash(u["clave_hash"], clave or ""):
        return None, "credenciales"
    if u["estado"] != "activo":
        return None, u["estado"]
    db.ejecutar("UPDATE usuarios SET ultimo_login = ? WHERE id = ?", (_ahora(), u["id"]))
    return u, "ok"


def obtener(uid):
    return db.ejecutar("SELECT * FROM usuarios WHERE id = ?", (uid,), uno=True)


def listar():
    return db.ejecutar("SELECT * FROM usuarios ORDER BY CASE WHEN estado = 'pendiente' THEN 0 ELSE 1 END, "
                       "lower(usuario)", todos=True)


def cambiar_estado(uid, estado):
    db.ejecutar("UPDATE usuarios SET estado = ? WHERE id = ?", (estado, uid))


def cambiar_rol(uid, rol):
    db.ejecutar("UPDATE usuarios SET rol = ? WHERE id = ?", (rol, uid))


def eliminar(uid):
    db.ejecutar("DELETE FROM usuarios WHERE id = ?", (uid,))


def cantidad_admins_activos():
    return db.ejecutar("SELECT COUNT(*) AS n FROM usuarios WHERE rol = 'admin' AND estado = 'activo'",
                       uno=True)["n"]


def cambiar_clave(uid, actual, nueva):
    u = obtener(uid)
    if u is None or not check_password_hash(u["clave_hash"], actual or ""):
        return "La contraseña actual es incorrecta."
    if len(nueva or "") < CLAVE_MIN:
        return f"La contraseña nueva debe tener al menos {CLAVE_MIN} caracteres."
    db.ejecutar("UPDATE usuarios SET clave_hash = ? WHERE id = ?", (generate_password_hash(nueva), uid))
    return ""
