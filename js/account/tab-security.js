/* Pestaña Seguridad: contraseña, verificación en dos pasos e inactividad */
function tabSeguridad(m) {
  const on = !!m.totp;
  return `<div class="settings-card"><div class="settings-card-title"><i class="ti ti-lock"></i> Cambiar contraseña</div>
    <div class="form-group"><label class="form-label" for="p-old">Contraseña actual</label><input class="form-input" id="p-old" type="password" autocomplete="current-password"></div>
    <div class="form-row">
      <div class="form-group"><label class="form-label" for="p-new">Nueva (10+, Aa1)</label><input class="form-input" id="p-new" type="password" autocomplete="new-password"></div>
      <div class="form-group"><label class="form-label" for="p-new2">Repetir</label><input class="form-input" id="p-new2" type="password" autocomplete="new-password"></div>
    </div>
    <button class="btn btn-primary" onclick="chPw()">Cambiar contraseña</button>
  </div>
  <div class="settings-card"><div class="settings-card-title"><i class="ti ti-shield-lock"></i> Verificación en dos pasos ${on ? pill('ok', 'Activada') : pill('off', 'Desactivada')}</div>
    ${on ? `<div class="form-row"><input class="form-input" id="s-pw" type="password" placeholder="Contraseña actual" aria-label="Contraseña actual" autocomplete="current-password"><button class="btn btn-danger" onclick="off2fa()">Desactivar 2FA</button></div>`
         : `<p class="hint">Usa Google Authenticator, Authy, Microsoft Authenticator o similar.</p><button class="btn btn-primary" onclick="setup2fa()">Activar 2FA</button><div id="s-2fa"></div>`}
  </div>
  <div class="settings-card"><div class="settings-card-title"><i class="ti ti-clock"></i> Cierre por inactividad</div>
    <div class="form-group"><label class="form-label" for="s-idle">Cerrar sesión tras</label>
      <select class="form-input" id="s-idle" onchange="setIdle(this.value)">${[5, 15, 30, 60].map(n => `<option value="${n}"${n === m.timeout ? ' selected' : ''}>${n} minutos sin actividad</option>`).join('')}</select></div>
  </div>`;
}

function setIdle(val) {
  const m = acUser(); if (!m) return;
  m.timeout = [5, 15, 30, 60].includes(+val) ? +val : 15;
  bump(); log('Tiempo de inactividad: ' + m.timeout + ' min'); save();
  acMsg('Preferencia guardada.', true);
}

async function chPw() {
  const m = acUser(); if (!m) return;
  const n = $('p-new').value;
  if (!await acPwOk(m, 'p-old')) return acMsg('Contraseña actual incorrecta');
  if (!pwOk(n)) return acMsg('La nueva contraseña no cumple la política');
  if (n !== $('p-new2').value) return acMsg('Las contraseñas nuevas no coinciden');
  m.salt = rnd(16); m.hash = await hashPw(n, m.salt);
  log('Cambio de contraseña'); save();
  acFlashMsg('Contraseña actualizada.', true);
}

function setup2fa() {
  tmp = b32e(crypto.getRandomValues(new Uint8Array(20)));
  const u = 'otpauth://totp/AgendaCitas:' + encodeURIComponent(me().user) + '?secret=' + tmp + '&issuer=AgendaCitas';
  $('s-2fa').innerHTML = `<p class="hint" style="margin:10px 0">Escanea el QR o ingresa la clave manualmente:<br><code>${tmp}</code></p><div id="qr"></div><div class="form-row" style="margin-top:10px"><input class="form-input" id="s-code" maxlength="6" placeholder="Código de 6 dígitos" aria-label="Código de 6 dígitos" autocomplete="one-time-code"><button class="btn btn-primary" onclick="conf2fa()">Verificar y activar</button></div>`;
  if (window.QRCode) new QRCode($('qr'), { text: u, width: 150, height: 150 });
}
async function conf2fa() {
  if (!await checkTotp(tmp, v('s-code'))) return acMsg('Código incorrecto');
  const m = acUser(), codes = Array.from({ length: 8 }, () => rnd(4));
  m.totp = { secret: tmp, on: true }; m.backup = await Promise.all(codes.map(sha)); tmp = null;
  log('2FA activada'); save();
  gm('2FA activada', `<p>Guarda estos códigos de respaldo (un solo uso). No se mostrarán de nuevo:</p><pre class="codes">${codes.join('\n')}</pre><button class="btn btn-primary" onclick="gmClose()">Listo</button>`);
  renderAccount();
}
async function off2fa() {
  const m = acUser(); if (!m) return;
  if (!await acPwOk(m, 's-pw')) return acMsg('Contraseña incorrecta');
  m.totp = null; m.backup = []; log('2FA desactivada'); save();
  acFlashMsg('Verificación en dos pasos desactivada.', true);
}
