/* Pestaña Servicio de correo (solo admin): SMTP real en servidor o modo demostración */
let msDraft = null, msCfg = { mode: 'demo', fromName: 'Agenda de Citas', smtpHost: '', smtpPort: 587, smtpUser: '', smtpFrom: '', smtpTls: true, hasPassword: false };

async function loadMailConfig() {
  try { msCfg = await API.get('/api/admin/mail'); } catch (e) {}
}

function tabServicio(m) {
  if (!isAdmin()) return '';
  const c = msCfg, mode = msDraft ?? c.mode, real = mode === 'smtp';
  const fields = real ? `
    <div class="form-row">
      <div class="form-group"><label class="form-label" for="ms-name">Nombre remitente</label><input class="form-input" id="ms-name" maxlength="40" value="${esc(c.fromName)}"></div>
      <div class="form-group"><label class="form-label" for="ms-from">Correo remitente</label><input class="form-input" id="ms-from" type="email" value="${esc(c.smtpFrom)}"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label class="form-label" for="ms-host">Servidor SMTP</label><input class="form-input" id="ms-host" placeholder="smtp.gmail.com" value="${esc(c.smtpHost)}"></div>
      <div class="form-group"><label class="form-label" for="ms-port">Puerto</label><input class="form-input" id="ms-port" type="number" value="${c.smtpPort || 587}"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label class="form-label" for="ms-user">Usuario SMTP</label><input class="form-input" id="ms-user" value="${esc(c.smtpUser)}"></div>
      <div class="form-group"><label class="form-label" for="ms-pass">Contraseña / App Password ${c.hasPassword ? '(guardada)' : ''}</label><input class="form-input" id="ms-pass" type="password" placeholder="${c.hasPassword ? 'Dejar vacío para conservar' : 'Contraseña de aplicación'}"></div>
    </div>
    <label class="check-row"><input type="checkbox" id="ms-tls" ${c.smtpTls ? 'checked' : ''}> <span>Usar STARTTLS (puerto 587)</span></label>`
    : `<p class="hint">En modo demostración los correos se guardan en la base de datos local sin salir a Internet. Ideal para pruebas antes de configurar SMTP.</p>`;

  return `<div class="settings-card"><div class="settings-card-title"><i class="ti ti-send"></i> Servicio de correo en servidor ${c.mode === 'smtp' ? pill('ok', 'SMTP activo') : pill('warn', 'Demostración')}</div>
    <div class="form-group"><label class="form-label" for="ms-mode">Modo</label>
      <select class="form-input" id="ms-mode" onchange="msMode(this.value)"><option value="demo"${!real ? ' selected' : ''}>Demostración (bandeja local)</option><option value="smtp"${real ? ' selected' : ''}>SMTP real (Gmail, Resend, SendGrid, Brevo)</option></select></div>
    ${fields}
    <div class="btn-row" style="margin-top:12px">
      <button class="btn btn-primary" onclick="saveMailCfg()"><i class="ti ti-check"></i> Guardar</button>
      <button class="btn" onclick="msTest()"><i class="ti ti-send"></i> Enviar correo de prueba</button>
      ${c.mode === 'demo' ? '<button class="btn" onclick="openPublicOutbox()">Ver bandeja</button>' : ''}
    </div>
    <p class="hint" style="margin-top:10px">Las credenciales SMTP se almacenan exclusivamente en el servidor y nunca se exponen en el navegador.</p>
  </div>`;
}
function msMode(val) { msDraft = val; renderAccount(); }
async function saveMailCfg() {
  const mode = msDraft ?? msCfg.mode;
  const payload = mode === 'smtp' ? {
    mode: 'smtp', fromName: v('ms-name'), smtpFrom: v('ms-from'), smtpHost: v('ms-host'),
    smtpPort: +($('ms-port').value || 587), smtpUser: v('ms-user'), smtpPass: $('ms-pass').value,
    smtpTls: $('ms-tls').checked
  } : { mode: 'demo' };
  try {
    const res = await API.put('/api/admin/mail', payload);
    msDraft = null; msCfg = res.config; APP.mailMode = res.config.mode;
    acFlashMsg(res.message, true);
  } catch (e) { acMsg(e.message); }
}
async function msTest() {
  acMsg('Enviando…', true);
  try {
    const res = await API.post('/api/admin/mail/test', {});
    acMsg(res.message, true);
  } catch (e) { acMsg(e.message); }
}
