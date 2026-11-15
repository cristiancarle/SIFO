# DEPLOY.md: publicar SIFO en Internet

La app se empaqueta con **Docker** (gunicorn + Chromium para los PDF) y funciona en cualquier hosting
que acepte contenedores. Abajo están los pasos para **Render**, que ya viene configurado con `render.yaml`.

## Variables de entorno

| Variable | Obligatoria | Descripción |
|---|---|---|
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

> **Plan actual: Free (para probar).** No tiene disco persistente: cada redeploy o reinicio
> **borra los incendios y los usuarios registrados** (el admin se vuelve a crear solo), y la app se
> duerme tras 15 min sin uso. Para producción, en `render.yaml` cambiá `plan: free` por
> `plan: starter` (~USD 7/mes) y descomentá el bloque `disk:`. Así los datos quedan en `/data`.

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
