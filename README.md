# Agenda de Citas — MVP Entregable

Aplicación web full-stack de gestión de citas con backend en Python 3 (sin dependencias externas), base de datos **SQLite**, seguridad en servidor, **portal público de reservas con QR**, catálogo e historial de clientes, notificaciones SMTP, reportes e importación/exportación CSV y `.ics`.

## Requisitos

- **Python 3.10+** (no requiere `pip install` ni `npm install`)
- Opcional: Docker / Docker Compose para despliegue en producción

## Inicio rápido (local)

1. Copia el archivo de variables de entorno:
   ```bash
   cp .env.example .env
   ```
2. (Opcional) Define `ADMIN_USER` y `ADMIN_PASSWORD` en `.env` (mínimo 10 caracteres, mayúscula, minúscula y número). Si los dejas vacíos, el servidor imprimirá un **Token de configuración inicial** de un solo uso en la consola para registrar al primer administrador de forma segura.
3. Inicia el servidor:
   ```bash
   python3 server.py
   ```
4. Abre `http://localhost:8000` en tu navegador.

## Funcionalidades incluidas en el MVP

- **Backend y persistencia real (`SQLite`):** Base de datos en `data/agenda.db` en modo WAL con llaves foráneas y migración automática.
- **Seguridad en servidor:**
  - Contraseñas con PBKDF2-SHA256 (150,000 iteraciones + sal aleatoria).
  - Sesiones en servidor con cookies `HttpOnly` y `SameSite=Lax` (`Secure` bajo HTTPS).
  - Protección CSRF, cabeceras de seguridad HTTP y limitación de tasa (*rate limiting*).
  - 2FA (TOTP RFC 6238), códigos de respaldo y códigos temporales (OTC) validados exclusivamente en servidor.
  - Aprovisionamiento controlado del administrador inicial (`.env` o `SETUP_TOKEN`).
- **Lógica de citas y prevención de traslapes:**
  - Bloquea doble reserva considerando la duración real de cada servicio.
  - Impide agendar en días no laborables, fuera de horario, durante descansos o en fechas/horas pasadas.
- **Portal público de reservas (`/reservar/<slug>`):**
  - Enlace único y código QR por agenda para que los clientes consulten disponibilidad en tiempo real y reserven sin iniciar sesión.
- **Catálogo e historial de clientes:**
  - Registro automático al crear citas, autocompletado en el modal y vista de historial de visitas y cancelaciones.
- **Correo transaccional SMTP y recordatorios:**
  - Compatible con Gmail (App Password), Resend, SendGrid o Brevo desde el servidor; incluye modo demostración local para pruebas.
  - Avisos de confirmación, cancelación, reagendamiento y envío de recordatorios individuales o masivos para el día siguiente.
- **Reportes y exportación:**
  - Resumen de ingresos, tasa de cancelación, desglose por servicio y descarga en **CSV** e **iCalendar (`.ics`)**.
- **Diseño responsivo móvil:** Menú lateral colapsable y vistas adaptadas a teléfonos.

## Ejecutar pruebas automatizadas

```bash
python3 -m unittest discover -s tests -v
```

## Despliegue en producción (Docker)

```bash
cp .env.example .env
# Edita .env: configura COOKIE_SECURE=true (detrás de Nginx/Caddy/Render/Railway con HTTPS) y tus credenciales SMTP
docker compose up -d --build
```
