/* Pestaña Recuperación: por correo y con códigos de un solo uso */
function tabRecuperacion(m) {
  const can = m.emailOk;
  return `<div class="settings-card"><div class="settings-card-title"><i class="ti ti-mail-forward"></i> Recuperar por correo</div>
    <label class="check-row"><input type="checkbox" id="rc-email" ${can && m.recEmail !== false ? 'checked' : ''} ${can ? '' : 'disabled'} onchange="setRecEmail(this.checked)">
      <span>Permitir restablecer mi contraseña con un código enviado a mi correo.${can ? '' : ' <b>Primero verifica un correo</b> en la pestaña Correo.'}</span></label>
    <p class="hint" style="margin:10px 0 0">${m.totp?.on ? 'Como tienes la verificación en dos pasos activa, también se pedirá el código del autenticador.' : 'Si activas la verificación en dos pasos, también se pedirá al restablecer la contraseña.'}</p>
  </div>
  <div class="settings-card"><div class="settings-card-title"><i class="ti ti-key"></i> Códigos de recuperación</div>
    <p class="hint">Ocho códigos de un solo uso para restablecer tu contraseña sin correo. Guárdalos en un lugar seguro. Al generar nuevos, los anteriores dejan de funcionar.</p>
    <p class="hint">Disponibles: <b>${m.rec.length}</b></p>
    <div class="form-row"><input class="form-input" id="rc-pw" type="password" placeholder="Contraseña actual" aria-label="Contraseña actual" autocomplete="current-password"><button class="btn btn-primary" onclick="genRecCodes()">${m.rec.length ? 'Generar nuevos' : 'Generar códigos'}</button></div>
  </div>`;
}

function setRecEmail(on) {
  const m = acUser(); if (!m) return;
  m.recEmail = !!on; log('Recuperación por correo ' + (on ? 'activada' : 'desactivada')); save();
  acMsg('Preferencia guardada.', true);
}

async function genRecCodes() {
  const m = acUser(); if (!m) return;
  if (!await acPwOk(m, 'rc-pw')) return acMsg('Contraseña incorrecta');
  const codes = Array.from({ length: 8 }, () => rnd(8).match(/.{4}/g).join('-'));
  m.rec = await Promise.all(codes.map(c => sha(normCode(c))));
  log('Códigos de recuperación generados'); save();
  gm('Códigos de recuperación', `<p>Guárdalos ahora; no se mostrarán de nuevo. Cada uno sirve una sola vez.</p>
    <pre class="codes">${codes.join('\n')}</pre>
    <div class="btn-row"><button class="btn" onclick="navigator.clipboard&&navigator.clipboard.writeText('${codes.join('\\n')}')"><i class="ti ti-copy"></i> Copiar</button><button class="btn btn-primary" onclick="gmClose()">Listo</button></div>`);
  renderAccount();
}
