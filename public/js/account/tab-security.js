/* Pestaña Seguridad: contraseña, 2FA en servidor e inactividad */
function tabSeguridad(m) {
  const on = !!m.totpOn;
  return `<div class="settings-card"><div class="settings-card-title"><i class="ti ti-lock"></i> Cambiar contraseña</div>
    <div class="form-group"><label class="form-label" for="p-old">Contraseña actual</label><input class="form-input" id="p-old" type="password" autocomplete="current-password"></div>
    <div class="form-row">
      <div class="form-group"><label class="form-label" for="p-new">Nueva (10+, Aa1)</label><input class="form-input" id="p-new" type="password" autocomplete="new-password"></div>
      <div class="form-group"><label class="form-label" for="p-new2">Repetir</label><input class="form-input" id="p-new2" type="password" autocomplete="new-password"></div>
    </div>
    <button class="btn btn-primary" onclick="chPw()">Cambiar contraseña</button>
  </div>
  <div class="settings-card"><div class="settings-card-title"><i class="ti ti-shield-lock"></i> Verificación en dos pasos ${on ? pill('ok', 'Activada') : pill('off', 'Desactivada')}</div>
    ${on ? `<div class="form-row"><input class="form-input" id="s-pw" type="password" placeholder="Contraseña actual" autocomplete="current-password"><button class="btn btn-danger" onclick="off2fa()">Desactivar 2FA</button></div>`
         : `<p class="hint">Usa Google Authenticator, Authy o Microsoft Authenticator.</p><button class="btn btn-primary" onclick="setup2fa()">Activar 2FA</button><div id="s-2fa"></div>`}
  </div>
  <div class="settings-card"><div class="settings-card-title"><i class="ti ti-clock"></i> Cierre por inactividad</div>
    <div class="form-group"><label class="form-label" for="s-idle">Cerrar sesión tras</label>
      <select class="form-input" id="s-idle" onchange="setIdle(this.value)">${[5, 15, 30, 60].map(n => `<option value="${n}"${n === m.timeout ? ' selected' : ''}>${n} minutos sin actividad</option>`).join('')}</select></div>
  </div>`;
}
async function setIdle(val) {
  try { const res = await API.put('/api/account/timeout', { timeout: +val }); acMsg(res.message, true); }
  catch (e) { acMsg(e.message); }
}
async function chPw() {
  const n = $('p-new').value;
  if (!pwOk(n)) return acMsg(POLICY_MSG);
  if (n !== $('p-new2').value) return acMsg('Las contraseñas nuevas no coinciden');
  try {
    const res = await API.put('/api/account/password', { oldPassword: $('p-old').value, newPassword: n });
    acFlashMsg(res.message, true);
  } catch (e) { acMsg(e.message); }
}
async function setup2fa() {
  try {
    const res = await API.post('/api/account/2fa/setup', {});
    $('s-2fa').innerHTML = `<p class="hint" style="margin:10px 0">Escanea el QR o ingresa la clave manualmente:<br><code>${esc(res.secret)}</code></p><div id="qr"></div><div class="form-row" style="margin-top:10px"><input class="form-input" id="s-code" maxlength="6" placeholder="Código de 6 dígitos" autocomplete="one-time-code"><button class="btn btn-primary" onclick="conf2fa()">Verificar y activar</button></div>`;
    if (window.QRCode) new QRCode($('qr'), { text: res.otpauthUri, width: 150, height: 150 });
  } catch (e) { acMsg(e.message); }
}
async function conf2fa() {
  try {
    const res = await API.post('/api/account/2fa/confirm', { code: v('s-code') });
    gm('2FA activada', `<p>Guarda estos códigos de respaldo (un solo uso):</p><pre class="codes">${res.backupCodes.join('\n')}</pre><button class="btn btn-primary" onclick="gmClose()">Listo</button>`);
    renderAccount();
  } catch (e) { acMsg(e.message); }
}
async function off2fa() {
  try {
    const res = await API.post('/api/account/2fa/disable', { password: $('s-pw').value });
    acFlashMsg(res.message, true);
  } catch (e) { acMsg(e.message); }
}
