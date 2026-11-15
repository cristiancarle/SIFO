# DEPLOY.md — Cómo correr el sistema de incendios

Aplicación Flask que escucha en el **puerto 5000**. Hay tres formas de levantarla.

---

## Opción 1 — Directo (desarrollo)

```bash
cd ~/Proyectos/sistema-incendios
python3 app.py
```

Abrir en el navegador: `http://localhost:5000`

> Si falta alguna dependencia (Flask, etc.): `pip3 install -r requirements.txt`
> (si no hay `requirements.txt`, instalar lo que pida el error, p. ej. `pip3 install flask`).

---

## Opción 2 — Docker

```bash
cd ~/Proyectos/sistema-incendios
docker build -t sistema-incendios .
docker run -d --name sistema-incendios -p 5000:5000 --restart unless-stopped sistema-incendios
```

- Ver logs: `docker logs -f sistema-incendios`
- Parar: `docker stop sistema-incendios` / `docker rm sistema-incendios`
- Si Docker no está instalado: `sudo apt install docker.io` y `sudo usermod -aG docker $USER` (cerrar sesión y volver a entrar para usar docker sin sudo).

---

## Opción 3 — systemd (servicio de usuario, arranque automático)

El unit está en `systemd/sistema-incendios.service` y corre como **servicio de usuario** (no requiere root).

```bash
# 1. Crear el directorio de units de usuario y copiar el servicio
mkdir -p ~/.config/systemd/user
cp ~/Proyectos/sistema-incendios/systemd/sistema-incendios.service ~/.config/systemd/user/

# 2. Cargar el unit nuevo
systemctl --user daemon-reload

# 3. Arrancar y habilitar al inicio de sesión
systemctl --user enable --now sistema-incendios

# 4. Verificar
systemctl --user status sistema-incendios
```

Comandos útiles:

```bash
systemctl --user restart sistema-incendios   # reiniciar
systemctl --user stop sistema-incendios      # parar
journalctl --user -u sistema-incendios -f    # logs en vivo
```

> **Nota**: los servicios de usuario se detienen al cerrar sesión. Para que
> persistan incluso sin sesión activa:
> ```bash
> sudo loginctl enable-linger cristian
> ```
> Con `Restart=on-failure`, systemd reinicia el servidor automáticamente si
> falla o se cierra inesperadamente.

---

## Abrir el puerto 5000 en el firewall (Kali)

Kali suele traer `ufw` o `nftables`/`iptables`. Primero verificar si hay firewall activo:

```bash
sudo ufw status
sudo nft list ruleset | head -50
```

### Si se usa ufw

```bash
sudo ufw allow 5000/tcp
sudo ufw reload
```

### Si se usa nftables/iptables (sin ufw)

```bash
# Permitir tráfico entrante al puerto 5000 (regla no persistente)
sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT

# Persistente (si está instalado iptables-persistent):
sudo netfilter-persistent save
```

> Si no hay firewall activo (ufw `inactive` y ruleset de nftables vacío),
> no hay que hacer nada: el puerto ya es accesible desde la red local
> 192.168.0.0/24, siempre que Flask escuche en `0.0.0.0` y no solo en
> `127.0.0.1`.

### Verificar que el puerto está abierto

```bash
ss -tlnp | grep 5000          # el servidor debe listar 0.0.0.0:5000 o *:5000
curl -I http://localhost:5000 # respuesta HTTP = servidor vivo
```

Desde otro equipo de la red: `http://<IP-de-esta-máquina>:5000`
(IP local: `ip -4 addr show | grep inet`).
