/* Pestaña Correo: agregar, verificar, cambiar y quitar el correo de la cuenta */
function tabCorreo(m) {
  const st = !m.email ? pill('off', 'Sin correo') : m.emailOk ? pill('ok', 'Verificado') : pill('warn', 'Sin verificar');
  const waiting = m.pend && m.pend.exp > Date.now();
  const demoNote = DB.mail.mode === 'demo' ? `<p class="hint" style="margin-top:8px">Modo demostración: el mensaje está en la <a href="#" onclick="openOutbox();return false">bandeja de demostración</a>.</p>` : '';
  const verifyBox = waiting ? `<div class="verify-box">
      <p class="hint">Enviamos un código a <b>${esc(m.pend.addr)}</b>. Escríbelo para confirmar el correo (vence en 10 minutos).</p>
      <div class="form-row"><input class="form-input" id="em-code" inputmode="numeric" maxlength="6" placeholder="Código de 6 dígitos" aria-label="Código de verificación" autocomplete="one-time-code"><button class="btn btn-primary" onclick="emVerify()">Verificar</button></div>${demoNote}</div>` : '';
  return `<div class="settings-card"><div class="settings-card-title"><i class="ti ti-mail"></i> Correo electrónico ${st}</div>
    <p class="hint">${m.email ? `Correo actual: <b>${esc(m.email)}</b>` : 'Agrega un correo para poder recuperar tu contraseña.'}</p>
    <div class="form-group"><label class="form-label" for="em-addr">${m.emailOk ? 'Cambiar por otro correo' : 'Correo'}</label><input class="form-input" id="em-addr" type="email" maxlength="80" autocomplete="email" value="${m.emailOk ? '' : esc(m.email)}"></div>
    ${m.emailOk ? `<div class="form-group"><label class="form-label" for="em-pw">Contraseña actual</label><input class="form-input" id="em-pw" type="password" autocomplete="current-password"></div>` : ''}
    <div class="btn-row">
      <button class="btn btn-primary" onclick="emSend()"><i class="ti ti-send"></i> ${m.emailOk ? 'Enviar código al nuevo correo' : 'Enviar código de verificación'}</button>
      ${m.email ? `<button class="btn btn-danger" onclick="emRemove()"><i class="ti ti-trash"></i> Quitar correo</button>` : ''}
    </div>${verifyBox}</div>`;
}

async function emSend() {
  const m = acUser(); if (!m) return;
  let addr = v('em-addr').toLowerCase();
  if (!addr && m.email && !m.emailOk) addr = m.email;
  if (!EMAIL_RE.test(addr) || addr.length > 80) return acMsg('Escribe un correo válido');
  if (m.emailOk && addr === m.email) return acMsg('Ese ya es tu correo verificado.');
  if (m.emailOk && !await acPwOk(m, 'em-pw')) return acMsg('Contraseña incorrecta');
  if (DB.users.some(u => u.id !== m.id && u.emailOk && u.email === addr)) return acMsg('Ese correo ya está asociado a otra cuenta');
  if (m.pend && m.pend.addr === addr && otcCooling(m.pend)) return acMsg('Espera ' + otcWait(m.pend) + ' s para pedir otro código.');
  const { code, rec } = await otcIssue();
  try { await sendMail(mailVerify(m, addr, code)); } catch (e) { return acMsg(e.message); }
  m.pend = { addr, ...rec };
  if (!m.emailOk) m.email = addr;   // queda guardado como "sin verificar"
  log('Código de verificación enviado a ' + addr); save();
  acFlashMsg(DB.mail.mode === 'demo' ? 'Código generado (modo demostración).' : 'Te enviamos un código. Revisa tu correo.', true);
}

async function emVerify() {
  const m = acUser(); if (!m) return;
  const st = await otcCheck(m.pend, v('em-code').replace(/\s/g, ''));
  if (st === 'expired' || st === 'locked') { m.pend = null; save(); return acFlashMsg('El código venció o se agotaron los intentos. Pide uno nuevo.'); }
  if (st === 'bad') { save(); return acMsg('Código incorrecto'); }
  const addr = m.pend.addr;
  if (DB.users.some(u => u.id !== m.id && u.emailOk && u.email === addr)) { m.pend = null; save(); return acFlashMsg('Ese correo ya está asociado a otra cuenta'); }
  m.email = addr; m.emailOk = true; m.pend = null;
  log('Correo verificado: ' + addr); save();
  acFlashMsg('Correo verificado.', true);
}

async function emRemove() {
  const m = acUser(); if (!m) return;
  if (m.emailOk && !await acPwOk(m, 'em-pw')) return acMsg('Escribe tu contraseña actual para quitar el correo');
  if (!confirm('¿Quitar el correo de tu cuenta? Ya no podrás recuperar la contraseña por correo.')) return;
  m.email = ''; m.emailOk = false; m.pend = null; delete DB.resets[m.id];
  log('Correo eliminado de la cuenta'); save();
  acFlashMsg('Correo eliminado.', true);
}

function openOutbox() {
  gm('Bandeja de demostración', `<p class="hint">Mensajes que la app "envió" en modo demostración (últimos 10).</p><div class="mail-list">${outboxHtml()}</div>`);
}
