/* Pestaña Correo */
function tabCorreo(m) {
  const st = !m.email ? pill('off', 'Sin correo') : m.emailOk ? pill('ok', 'Verificado') : pill('warn', 'Sin verificar');
  const waiting = !!m.pendingEmail;
  const demoNote = APP.mailMode === 'demo' ? `<p class="hint" style="margin-top:8px">Modo demostración: el mensaje está en la <a href="#" onclick="openPublicOutbox();return false">bandeja de demostración</a>.</p>` : '';
  const verifyBox = waiting ? `<div class="verify-box">
      <p class="hint">Enviamos un código a <b>${esc(m.pendingEmail.addr)}</b>. Escríbelo para confirmar el correo (vence en 10 minutos).</p>
      <div class="form-row"><input class="form-input" id="em-code" inputmode="numeric" maxlength="6" placeholder="Código de 6 dígitos" autocomplete="one-time-code"><button class="btn btn-primary" onclick="emVerify()">Verificar</button></div>${demoNote}</div>` : '';
  return `<div class="settings-card"><div class="settings-card-title"><i class="ti ti-mail"></i> Correo electrónico ${st}</div>
    <p class="hint">${m.email ? `Correo actual: <b>${esc(m.email)}</b>` : 'Agrega un correo para recibir avisos y recuperar tu contraseña.'}</p>
    <div class="form-group"><label class="form-label" for="em-addr">${m.emailOk ? 'Cambiar por otro correo' : 'Correo'}</label><input class="form-input" id="em-addr" type="email" maxlength="80" autocomplete="email" value="${m.emailOk ? '' : esc(m.email)}"></div>
    ${m.emailOk ? `<div class="form-group"><label class="form-label" for="em-pw">Contraseña actual</label><input class="form-input" id="em-pw" type="password" autocomplete="current-password"></div>` : ''}
    <div class="btn-row">
      <button class="btn btn-primary" onclick="emSend()"><i class="ti ti-send"></i> ${m.emailOk ? 'Enviar código al nuevo correo' : 'Enviar código de verificación'}</button>
      ${m.email ? `<button class="btn btn-danger" onclick="emRemove()"><i class="ti ti-trash"></i> Quitar correo</button>` : ''}
    </div>${verifyBox}</div>`;
}
async function emSend() {
  try {
    const res = await API.post('/api/account/email/send', { email: v('em-addr'), password: $('em-pw')?.value || '' });
    acFlashMsg(res.message, true);
  } catch (e) { acMsg(e.message); }
}
async function emVerify() {
  try {
    const res = await API.post('/api/account/email/verify', { code: v('em-code') });
    acFlashMsg(res.message, true);
  } catch (e) { acMsg(e.message); }
}
async function emRemove() {
  if (!confirm('¿Quitar el correo de tu cuenta?')) return;
  try {
    const res = await API.del('/api/account/email', { password: $('em-pw')?.value || '' });
    acFlashMsg(res.message, true);
  } catch (e) { acMsg(e.message); }
}
