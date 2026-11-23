/* Pestaña Recuperación */
function tabRecuperacion(m) {
  const can = m.emailOk;
  return `<div class="settings-card"><div class="settings-card-title"><i class="ti ti-mail-forward"></i> Recuperar por correo</div>
    <label class="check-row"><input type="checkbox" id="rc-email" ${can && m.recEmail ? 'checked' : ''} ${can ? '' : 'disabled'} onchange="setRecEmail(this.checked)">
      <span>Permitir restablecer mi contraseña con un código enviado a mi correo.${can ? '' : ' <b>Primero verifica un correo</b> en la pestaña Correo.'}</span></label>
  </div>
  <div class="settings-card"><div class="settings-card-title"><i class="ti ti-key"></i> Códigos de recuperación</div>
    <p class="hint">Ocho códigos de un solo uso para restablecer tu contraseña sin correo. Disponibles: <b>${m.recCount}</b></p>
    <div class="form-row"><input class="form-input" id="rc-pw" type="password" placeholder="Contraseña actual" autocomplete="current-password"><button class="btn btn-primary" onclick="genRecCodes()">${m.recCount ? 'Generar nuevos' : 'Generar códigos'}</button></div>
  </div>`;
}
async function setRecEmail(on) {
  try {
    const res = await API.put('/api/account/recovery-email', { enabled: !!on });
    acMsg(res.message, true);
  } catch (e) { acMsg(e.message); }
}
async function genRecCodes() {
  try {
    const res = await API.post('/api/account/recovery-codes', { password: $('rc-pw').value });
    gm('Códigos de recuperación', `<p>Guárdalos ahora; no se mostrarán de nuevo:</p>
      <pre class="codes">${res.codes.join('\n')}</pre>
      <div class="btn-row"><button class="btn" onclick="navigator.clipboard?.writeText('${res.codes.join('\n')}')"><i class="ti ti-copy"></i> Copiar</button><button class="btn btn-primary" onclick="gmClose()">Listo</button></div>`);
    renderAccount();
  } catch (e) { acMsg(e.message); }
}
