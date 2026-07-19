import sqlite3

DB = "datos/incendios.db"


def conectar():
    return sqlite3.connect(DB)


def crear_base_datos():

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incendios(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            fecha TEXT NOT NULL,
            hora TEXT NOT NULL,

            nombre_incendio TEXT,

            provincia TEXT,
            localidad TEXT,

            latitud REAL NOT NULL,
            longitud REAL NOT NULL,

            descripcion TEXT,

            estado TEXT DEFAULT 'ACTIVO',

            radio_analisis INTEGER DEFAULT 10000

        )
    """)

    conexion.commit()
    conexion.close()

def obtener_incendios():

    conexion = conectar()

    cursor = conexion.cursor()

    cursor.execute("""
        SELECT id,
               nombre_incendio,
               fecha,
               provincia
        FROM incendios
        ORDER BY id
    """)

    datos = cursor.fetchall()

    conexion.close()

    return datos

def registrar_incendio(
        fecha,
        hora,
        nombre,
        provincia,
        localidad,
        latitud,
        longitud,
        descripcion):

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        INSERT INTO incendios(

            fecha,
            hora,
            nombre_incendio,
            provincia,
            localidad,
            latitud,
            longitud,
            descripcion

        )

        VALUES(?,?,?,?,?,?,?,?)

    """, (

        fecha,
        hora,
        nombre,
        provincia,
        localidad,
        latitud,
        longitud,
        descripcion

    ))

    conexion.commit()
    conexion.close()


def listar_incendios():

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("SELECT * FROM incendios")

    datos = cursor.fetchall()

    conexion.close()

    return datos