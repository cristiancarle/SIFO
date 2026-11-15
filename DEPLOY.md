# DEPLOY.md: publicar SIFO en Internet

La app se empaqueta con **Docker** (gunicorn + Chromium para los PDF) y funciona en cualquier hosting
que acepte contenedores. Abajo están los pasos para **Render**, que ya viene configurado con `render.yaml`.

## Variables de entorno

| Variable | Obligatoria | Descripción |
|---|---|---|
| `DATABASE_URL` | sí en hosting gratuito | PostgreSQL donde se guardan usuarios e incendios (Neon/Supabase). Sin ella se usa SQLite local. |
| `SIFO_SECRET_KEY` | sí | Firma las cookies de sesión. Render la genera sola. |
| `SIFO_ADMIN_USUARIO` | sí | Usuario administrador inicial. |
| `SIFO_ADMIN_CLAVE_HASH` | sí* | Hash de la clave del admin (*o `SIFO_ADMIN_CLAVE` en texto plano). |
| `SIFO_REGISTRO` | no | `1` (por defecto): registro abierto, pendiente de aprobación. `0`: registro cerrado. |
| `SIFO_PRODUCCION` | no | La imagen Docker ya trae `1` (cookies Secure, HSTS, proxy). |
| `SIFO_DATA_DIR`, `SIFO_CACHE_DIR`, `SIFO_DB` | no | Rutas de datos. En Docker apuntan a `/data`. |

Para generar el hash de la clave del admin:

```bash
python3 -c "from werkzeug.security import generate_password_hash as g; print(g('MI-CLAVE-LARGA'))"
```

## Render (recomendado)

1. Subí el repositorio a GitHub. Puede ser **privado**.
2. En https://dashboard.render.com hacé **New → Blueprint** y elegí el repo. Render detecta `render.yaml`.
3. Cuando lo pida, pegá el valor de `SIFO_ADMIN_CLAVE_HASH`.
4. Esperá el build (unos 3-5 min). La app queda en `https://sifo-xxxx.onrender.com`, con HTTPS automático.
5. Opcional: en **Settings → Custom Domains** agregá tu dominio, por ejemplo `sifo.tudominio.com.ar`.

> **Plan actual: Free + base PostgreSQL gratuita.** El disco de Render free es temporal, así que
> los usuarios y los incendios se guardan en una base externa (`DATABASE_URL`). Los KML, informes y
> PDF son una caché que se regenera sola desde la base cuando el servicio se reinicia.

### Crear la base gratuita en Neon

1. Registrate en https://neon.tech (podés usar tu cuenta de GitHub).
2. **Create project** → nombre `sifo`, región **AWS US West 2 (Oregon)**, la misma zona que el servicio de Render.
3. En **Connection string**, copiá la cadena que empieza con `postgresql://` (con `?sslmode=require`).
4. En Render → servicio **sifo** → **Environment** → agregá `DATABASE_URL` con esa cadena → **Save, rebuild, and deploy**.

Las tablas se crean solas al arrancar. Neon free suspende la base tras 5 min sin uso; la primera
consulta después de eso tarda 1-2 segundos más.

Cada `git push` a la rama principal redeploya la app automáticamente.

## Docker en cualquier servidor (VPS, Railway, Fly.io...)

```bash
docker build -t sifo .
docker run -d --name sifo -p 8000:8000 --restart unless-stopped \
  -v sifo-datos:/data --env-file .env sifo
```

Poné delante un proxy con HTTPS (Caddy, nginx + certbot, o el que traiga el hosting). Sin HTTPS, el
login no funciona en modo producción, porque la cookie es `Secure`.

## Desarrollo local

```bash
pip install -r requirements.txt
SIFO_ADMIN_USUARIO=admin SIFO_ADMIN_CLAVE='clave-de-prueba' python3 app.py   # http://127.0.0.1:5000
```

Verificación completa (usa las APIs reales):

```bash
SIFO_ADMIN_USUARIO=admin SIFO_ADMIN_CLAVE='clave-de-prueba' python3 test/verificar_sistema.py
```
