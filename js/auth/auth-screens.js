/* Pantallas de autenticación (se dibujan dentro de #auth-card) */
const POLICY_MSG = 'Contraseña: mínimo 10 caracteres con mayúscula, minúscula y número';
const pwOk = p => p.length >= 10 && /[a-z]/.test(p) && /[A-Z]/.test(p) && /\d/.test(p);
const err = (m, good) => { const e = $('a-err'); if (e) { e.className = good ? 'msg-ok' : 'err'; e.textContent = m; } };

function authView(m, msg = '', good = false) {
  const f = (i, l, t = 'text', ac = 'off') => `<label class="form-label" for="${i}">${l}</label><input class="form-input" id="${i}" type="${t}" autocomplete="${ac}" style="margin-bottom:10px">`;
  const b = (fn, t) => `<div class="${good ? 'msg-ok' : 'err'}" id="a-err" role="alert">${msg}</div><button class="btn btn-primary" style="width:100%;justify-content:center" onclick="${fn}()">${t}</button>`;
  const link = (view, t) => `<a href="#" onclick="authView('${view}');return false">${t}</a>`;
  const demo = DB.mail.mode === 'demo' ? `<p>${link('outbox', 'Ver bandeja de correo de demostración')}</p>` : '';
  const first = !DB.users.length;
  $('auth-card').innerHTML = {
    login: `<h2>Iniciar sesión</h2><p>Agenda de Citas</p>${f('a-user', 'Usuario', 'text', 'username')}${f('a-pass', 'Contraseña', 'password', 'current-password')}${b('doLogin', 'Entrar')}<p style="margin-top:12px">${link('forgot', '¿Olvidaste tu contraseña?')} · ${link('reg', 'Crear cuenta')}</p>`,
    reg: `<h2>${first ? 'Crear administrador inicial' : 'Crear cuenta'}</h2><p>Contraseña: 10+ caracteres con mayúscula, minúscula y número.</p>${f('a-user', 'Usuario', 'text', 'username')}${f('a-name', 'Nombre', 'text', 'name')}${f('a-mail', 'Correo (opcional, para recuperar tu contraseña)', 'email', 'email')}${f('a-pass', 'Contraseña', 'password', 'new-password')}${f('a-pass2', 'Repetir contraseña', 'password', 'new-password')}${b('doReg', 'Registrarme')}${first ? '' : `<p style="margin-top:12px">${link('login', 'Ya tengo cuenta')}</p>`}`,
    mfa: `<h2>Verificación en dos pasos</h2><p>Ingresa el código de tu app autenticadora o un código de respaldo.</p>${f('a-code', 'Código', 'text', 'one-time-code')}${b('doMfa', 'Verificar')}`,
    forgot: `<h2>Recuperar contraseña</h2><p>Escribe tu usuario o tu correo. Si la cuenta tiene un correo verificado, te enviaremos un código.</p>${f('a-id', 'Usuario o correo', 'text', 'username')}${b('doForgot', 'Enviar código')}<p style="margin-top:12px">${link('recov', 'Usar un código de recuperación')}</p>${demo}<p>${link('login', 'Volver')}</p>`,
    reset: `<h2>Restablecer contraseña</h2><p>Escribe el código que recibiste y tu nueva contraseña.</p>${f('a-code', 'Código de 6 dígitos', 'text', 'one-time-code')}${f('a-pass', 'Nueva contraseña', 'password', 'new-password')}${f('a-pass2', 'Repetir contraseña', 'password', 'new-password')}${f('a-2fa', 'Código del autenticador (solo si tienes 2FA)', 'text', 'off')}${b('doReset', 'Cambiar contraseña')}<p style="margin-top:12px">${link('forgot', 'Pedir otro código')}</p>${demo}`,
    recov: `<h2>Código de recuperación</h2><p>Usa uno de los códigos de recuperación que guardaste en tu cuenta.</p>${f('a-user', 'Usuario', 'text', 'username')}${f('a-code', 'Código de recuperación', 'text', 'off')}${f('a-pass', 'Nueva contraseña', 'password', 'new-password')}${f('a-pass2', 'Repetir contraseña', 'password', 'new-password')}${f('a-2fa', 'Código del autenticador (solo si tienes 2FA)', 'text', 'off')}${b('doRecov', 'Cambiar contraseña')}<p style="margin-top:12px">${link('login', 'Volver')}</p>`,
    outbox: `<h2>Bandeja de demostración</h2><p>Aquí aparecen los correos que la app "envía" mientras no haya un servicio de correo real configurado.</p><div class="mail-list">${outboxHtml()}</div><p style="margin-top:12px">${link(pendReset ? 'reset' : 'forgot', 'Volver')}</p>`
  }[m];
  const i = $('auth-card').querySelector('input'); i && i.focus();
}
