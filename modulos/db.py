"""Almacenamiento persistente de SIFO.

- Con la variable DATABASE_URL (postgresql://...): PostgreSQL (Neon, Supabase, Render...).
- Sin ella: SQLite local en SIFO_DB (por defecto datos/sifo.db).

Se guarda lo que no se puede reconstruir: usuarios e incendios (metadatos + resultados del
análisis). KML, GeoJSON, informe HTML y PDF son derivados: se regeneran en disco cuando faltan.
"""
import json
import os
import sqlite3
import threading

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
ES_PG = DATABASE_URL.startswith(("postgres://", "postgresql://"))
RUTA_SQLITE = os.environ.get("SIFO_DB") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "datos", "sifo.db")

if ES_PG:
    import psycopg
    from psycopg.rows import dict_row

    ErrorIntegridad = (psycopg.IntegrityError,)
    _ErrorConexion = (psycopg.OperationalError, psycopg.InterfaceError)
else:
    ErrorIntegridad = (sqlite3.IntegrityError,)
    _ErrorConexion = ()

_local = threading.local()


def _nueva_conexion():
    if ES_PG:
        # Neon/Supabase suspenden la base tras unos minutos sin uso: timeout generoso para el arranque.
        return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=20, autocommit=True)
    os.makedirs(os.path.dirname(RUTA_SQLITE), exist_ok=True)
    con = sqlite3.connect(RUTA_SQLITE, timeout=10, isolation_level=None, check_same_thread=False)
    con.row_factory = lambda c, fila: {d[0]: v for d, v in zip(c.description, fila)}
    return con


def _conexion():
    con = getattr(_local, "con", None)
    if con is None or (ES_PG and con.closed):
        con = _local.con = _nueva_conexion()
    return con


def ejecutar(sql, params=(), uno=False, todos=False):
    """Ejecuta SQL con marcadores '?' (se adaptan a PostgreSQL). Devuelve dict, lista de dicts o None.
    Reintenta una vez si la conexión se cortó (la base gratuita se suspende cuando no se usa)."""
    if ES_PG:
        sql = sql.replace("?", "%s")
    for intento in (1, 2):
        try:
            cur = _conexion().execute(sql, params)
            if uno:
                return cur.fetchone()
            if todos:
                return cur.fetchall()
            return None
        except _ErrorConexion:
            _local.con = None
            if intento == 2:
                raise


def iniciar():
    if ES_PG:
        ejecutar("""CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            usuario TEXT NOT NULL,
            nombre TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            clave_hash TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'usuario',
            estado TEXT NOT NULL DEFAULT 'pendiente',
            creado TEXT NOT NULL,
            ultimo_login TEXT)""")
        ejecutar("CREATE UNIQUE INDEX IF NOT EXISTS usuarios_usuario_ci ON usuarios (lower(usuario))")
    else:
        ejecutar("""CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL UNIQUE COLLATE NOCASE,
            nombre TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            clave_hash TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'usuario',
            estado TEXT NOT NULL DEFAULT 'pendiente',
            creado TEXT NOT NULL,
            ultimo_login TEXT)""")
    ejecutar("""CREATE TABLE IF NOT EXISTS incendios (
        base TEXT PRIMARY KEY,
        meta TEXT NOT NULL,
        datos TEXT NOT NULL)""")


# ------------------------------------------------------------------ incendios
def guardar_incendio(meta, datos):
    m = json.dumps(meta, ensure_ascii=False)
    d = json.dumps(datos, ensure_ascii=False)
    ejecutar("INSERT INTO incendios (base, meta, datos) VALUES (?, ?, ?) "
             "ON CONFLICT (base) DO UPDATE SET meta = excluded.meta, datos = excluded.datos",
             (meta["base"], m, d))


def meta_incendio(base):
    fila = ejecutar("SELECT meta FROM incendios WHERE base = ?", (base,), uno=True)
    return json.loads(fila["meta"]) if fila else None


def datos_incendio(base):
    fila = ejecutar("SELECT datos FROM incendios WHERE base = ?", (base,), uno=True)
    return json.loads(fila["datos"]) if fila else None


def listar_incendios():
    filas = ejecutar("SELECT meta FROM incendios ORDER BY base DESC", todos=True)
    return [json.loads(f["meta"]) for f in filas]


def borrar_incendio(base):
    ejecutar("DELETE FROM incendios WHERE base = ?", (base,))


def existe_incendio(base):
    return ejecutar("SELECT 1 AS x FROM incendios WHERE base = ?", (base,), uno=True) is not None
