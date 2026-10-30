# Agenda de Citas

Aplicación web de agenda de citas. Funciona abriendo `index.html` con doble clic (sin servidor ni instalación).
Los datos se guardan en el `localStorage` del navegador.

## Estructura

```
index.html            Estructura de la página (HTML) y lista de scripts
css/
  base.css            Variables de color, reset, tipografía
  layout.css          Sidebar, mini-calendario, barra superior, vistas
  components.css      Botones, formularios, modales, tablas, mensajes
  calendar.css        Calendario y panel del día
  agenda.css          Lista de citas
  settings.css        Horarios
  services.css        Servicios
  auth.css            Pantalla de login
  account.css         Mi cuenta y bandeja de correo de demostración
js/
  core/               Constantes, utilidades, estado (S), base de datos local (DB),
                      criptografía, TOTP y códigos de un solo uso (otc)
  mail/mail.js        Envío de correo (modo demostración o EmailJS) y plantillas
  ui/                 Navegación entre vistas (views.js) y diálogo genérico
  calendar/ agenda/ settings/ services/ appointments/   Una carpeta por vista
  auth/               Sesión, pantallas de login, registro y recuperación
  agendas/            Varias agendas por usuario y guardado automático
  account/            Vista "Mi cuenta": una pestaña por archivo (tab-*.js)
  admin/users.js      Usuarios y bitácora (solo administrador)
  dev/seed-demo.js    Datos de ejemplo (no se carga; solo para usar desde la consola)
  main.js             Arranque
```

## Orden de carga

Los scripts son clásicos (no módulos) para que funcione con doble clic; comparten el ámbito global.
Por eso el orden en `index.html` importa:
`core` → `mail` → `ui` → vistas → `auth` → `agendas` → `account` → `admin` → `agendas/persistence.js` → `main.js`.
`persistence.js` envuelve funciones de otros archivos, así que va casi al final.

## Cómo agregar cosas

- **Nueva vista:** un `<div id="view-X" class="view">` y un botón `id="nav-X"` en `index.html`, y una entrada en `VIEWS` de `js/ui/views.js`.
- **Nueva pestaña en Mi cuenta:** una entrada en `AC_TABS` (`js/account/account-view.js`) y una función que devuelva su HTML.

## Cuenta de usuario

| Opción | Dónde |
|---|---|
| Nombre | Mi cuenta → Perfil |
| Correo con código de verificación (6 dígitos, 10 min, 5 intentos) | Mi cuenta → Correo |
| Recuperar contraseña por correo (activar/desactivar) | Mi cuenta → Recuperación |
| 8 códigos de recuperación de un solo uso | Mi cuenta → Recuperación |
| Cambio de contraseña, 2FA, cierre por inactividad (5/15/30/60 min) | Mi cuenta → Seguridad |
| Servicio de envío de correo (admin) | Mi cuenta → Servicio de correo |

En el login: **¿Olvidaste tu contraseña?** → código por correo, o **Usar un código de recuperación**.
Si la cuenta tiene 2FA, restablecer la contraseña también pide el código del autenticador.
Las respuestas no revelan si un usuario o correo existe.

## Conectar correo real (EmailJS)

1. En emailjs.com crea un servicio de correo y una plantilla con destinatario `{{to_email}}`, asunto `{{subject}}` y cuerpo `{{message}}`.
2. Entra como administrador → Mi cuenta → Servicio de correo → modo EmailJS, pega Service ID, Template ID y Public Key, guarda y usa "Enviar correo de prueba".
3. En el panel de EmailJS limita dominios y envíos por día (la Public Key es visible en el navegador).

Mientras no lo configures, la app usa el **modo demostración**: los correos se guardan en una bandeja local
(visible en el login → "Ver bandeja de correo de demostración").

## Límite importante

Todo corre en el navegador: no hay servidor. Quien tenga acceso al navegador y a sus herramientas de desarrollo
puede leer o modificar `localStorage`, así que estas protecciones sirven para uso personal o demostración.
Para producción hacen falta un backend y una base de datos reales, que sean quienes generen y validen los códigos y envíen los correos.
