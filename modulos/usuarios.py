"""Usuarios de SIFO: registro, login y administración (SQLite, sin dependencias extra).

Estados: 'pendiente' (se registró, espera aprobación), 'activo', 'inactivo'.
Roles: 'admin' (aprueba/gestiona usuarios) y 'usuario'.
"""
import os
import re
import sqlite3
from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

RUTA_DB = os.environ.get("SIFO_DB") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "datos", "sifo.db")

USUARIO_RE = re.compile(r"[A-Za-z0-9_.-]{3,30}")
EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
CLAVE_MIN = 10

# Hash fijo para igualar tiempos cuando el usuario no existe (evita enumerar usuarios).
_HASH_FALSO = generate_password_hash("sifo-usuario-inexistente")


def _con():
    os.makedirs(os.path.dirname(RUTA_DB), exist_ok=True)
    con = sqlite3.connect(RUTA_DB, timeout=10)
    con.row_factory = sqlite3.Row
    return con


def iniciar_db(admin_usuario="", admin_clave="", admin_clave_hash=""):
    """Crea la tabla y, si se pasan credenciales de admin, asegura que esa cuenta exista y esté activa."""
    with _con() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL UNIQUE COLLATE NOCASE,
            nombre TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            clave_hash TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'usuario',
            estado TEXT NOT NULL DEFAULT 'pendiente',
            creado TEXT NOT NULL,
            ultimo_login TEXT)""")
        if admin_usuario and (admin_clave or admin_clave_hash):
            h = admin_clave_hash or generate_password_hash(admin_clave)
            fila = con.execute("SELECT id FROM usuarios WHERE usuario = ?", (admin_usuario,)).fetchone()
            if fila:
                con.execute("UPDATE usuarios SET clave_hash = ?, rol = 'admin', estado = 'activo' WHERE id = ?",
                            (h, fila["id"]))
            else:
                con.execute("INSERT INTO usuarios (usuario, nombre, clave_hash, rol, estado, creado) "
                            "VALUES (?, 'Administrador', ?, 'admin', 'activo', ?)",
                            (admin_usuario, h, _ahora()))


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
    try:
        with _con() as con:
            con.execute("INSERT INTO usuarios (usuario, nombre, email, clave_hash, creado) VALUES (?, ?, ?, ?, ?)",
                        (usuario, nombre.strip()[:100], email.strip()[:150], generate_password_hash(clave), _ahora()))
        return True
    except sqlite3.IntegrityError:
        return False


def autenticar(usuario, clave):
    """Devuelve (fila, motivo). motivo: 'ok', 'credenciales', 'pendiente', 'inactivo'."""
    with _con() as con:
        u = con.execute("SELECT * FROM usuarios WHERE usuario = ?", (usuario or "",)).fetchone()
    if u is None:
        check_password_hash(_HASH_FALSO, clave or "")
        return None, "credenciales"
    if not check_password_hash(u["clave_hash"], clave or ""):
        return None, "credenciales"
    if u["estado"] != "activo":
        return None, u["estado"]
    with _con() as con:
        con.execute("UPDATE usuarios SET ultimo_login = ? WHERE id = ?", (_ahora(), u["id"]))
    return u, "ok"


def obtener(uid):
    with _con() as con:
        return con.execute("SELECT * FROM usuarios WHERE id = ?", (uid,)).fetchone()


def listar():
    with _con() as con:
        return con.execute("SELECT * FROM usuarios ORDER BY estado = 'pendiente' DESC, usuario").fetchall()


def cambiar_estado(uid, estado):
    with _con() as con:
        con.execute("UPDATE usuarios SET estado = ? WHERE id = ?", (estado, uid))


def cambiar_rol(uid, rol):
    with _con() as con:
        con.execute("UPDATE usuarios SET rol = ? WHERE id = ?", (rol, uid))


def eliminar(uid):
    with _con() as con:
        con.execute("DELETE FROM usuarios WHERE id = ?", (uid,))


def cantidad_admins_activos():
    with _con() as con:
        return con.execute("SELECT COUNT(*) FROM usuarios WHERE rol = 'admin' AND estado = 'activo'").fetchone()[0]


def cambiar_clave(uid, actual, nueva):
    u = obtener(uid)
    if u is None or not check_password_hash(u["clave_hash"], actual or ""):
        return "La contraseña actual es incorrecta."
    if len(nueva or "") < CLAVE_MIN:
        return f"La contraseña nueva debe tener al menos {CLAVE_MIN} caracteres."
    with _con() as con:
        con.execute("UPDATE usuarios SET clave_hash = ? WHERE id = ?", (generate_password_hash(nueva), uid))
    return ""
