/* Pestaña Servicio de correo (solo administrador): cómo se envían los correos de la app */
let msDraft = null;   // modo elegido en el selector, aún sin guardar

function tabServicio(m) {
  if (!isAdmin()) return '';
  const c = DB.mail, mode = msDraft ?? c.mode, real = mode === 'emailjs';
  const fields = real ? `
    <div class="form-group"><label class="form-label" for="ms-name">Nombre que verá el destinatario</label><input class="form-input" id="ms-name" maxlength="40" value="${esc(c.fromName)}"></div>
    <div class="form-row">
      <div class="form-group"><label class="form-label" for="ms-service">Service ID</label><input class="form-input" id="ms-service" maxlength="60" autocomplete="off" value="${esc(c.serviceId)}"></div>
      <div class="form-group"><label class="form-label" for="ms-template">Template ID</label><input class="form-input" id="ms-template" maxlength="60" autocomplete="off" value="${esc(c.templateId)}"></div>
    </div>
    <div class="form-group"><label class="form-label" for="ms-key">Public Key</label><input class="form-input" id="ms-key" maxlength="80" autocomplete="off" value="${esc(c.publicKey)}"></div>`
    : `<p class="hint">En este modo ningún correo sale de este navegador: los mensajes se guardan en una bandeja de pruebas que cualquiera con acceso a este navegador puede ver. Úsalo solo para desarrollo.</p>`;
  return `<div class="settings-card"><div class="settings-card-title"><i class="ti ti-send"></i> Servicio de envío ${c.mode === 'emailjs' ? pill('ok', 'EmailJS activo') : pill('warn', 'Demostración')}</div>
    <div class="form-group"><label class="form-label" for="ms-mode">Modo</label>
      <select class="form-input" id="ms-mode" onchange="msMode(this.value)"><option value="demo"${!real ? ' selected' : ''}>Demostración (bandeja local)</option><option value="emailjs"${real ? ' selected' : ''}>EmailJS (envío real)</option></select></div>
    ${fields}
    <div class="btn-row"><button class="btn btn-primary" onclick="saveMailCfg()"><i class="ti ti-check"></i> Guardar</button><button class="btn" onclick="msTest()"><i class="ti ti-send"></i> Enviar correo de prueba</button>${c.mode === 'demo' ? '<button class="btn" onclick="openOutbox()">Ver bandeja</button>' : ''}</div>
    <p class="hint" style="margin-top:10px">La prueba se envía a tu correo verificado${m.emailOk ? ` (<b>${esc(m.email)}</b>)` : ' (primero verifica uno en la pestaña Correo)'} con la configuración ya guardada.</p>
  </div>
  <div class="settings-card"><div class="settings-card-title"><i class="ti ti-info-circle"></i> Cómo conectar EmailJS</div>
    <ol class="steps">
      <li>Crea una cuenta en emailjs.com y agrega un servicio de correo (Gmail, Outlook u otro).</li>
      <li>Crea una plantilla con destinatario <code>{{to_email}}</code>, asunto <code>{{subject}}</code> y cuerpo <code>{{message}}</code>.</li>
      <li>Copia el Service ID, el Template ID y tu Public Key en los campos de arriba y guarda.</li>
      <li>En el panel de EmailJS limita los dominios permitidos y los envíos por día: la Public Key es visible desde el navegador.</li>
    </ol>
  </div>`;
}

function msMode(val) { msDraft = val; renderAccount(); }

function saveMailCfg() {
  if (!isAdmin()) return;
  const mode = msDraft ?? DB.mail.mode, c = DB.mail;
  if (mode === 'emailjs') {
    const name = v('ms-name') || APP_NAME, s = v('ms-service'), t = v('ms-template'), k = v('ms-key');
    if (!s || !t || !k) return acMsg('Completa Service ID, Template ID y Public Key.');
    Object.assign(c, { mode, fromName: name, serviceId: s, templateId: t, publicKey: k });
  } else c.mode = 'demo';
  msDraft = null; log('Servicio de correo: ' + c.mode); save();
  acFlashMsg('Configuración guardada.', true);
}

async function msTest() {
  const m = acUser(); if (!m || !isAdmin()) return;
  if (!m.emailOk) return acMsg('Verifica primero tu correo en la pestaña Correo.');
  acMsg('Enviando…', true);
  try {
    const r = await sendMail({ to: m.email, name: m.name, code: '000000', subject: 'Correo de prueba · ' + APP_NAME, text: 'Este es un correo de prueba de ' + APP_NAME + '. Si lo recibiste, el envío funciona.' });
    acMsg(r === 'demo' ? 'Mensaje guardado en la bandeja de demostración.' : 'Correo de prueba enviado a ' + m.email + '.', true);
  } catch (e) { acMsg(e.message); }
}
