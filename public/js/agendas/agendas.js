/* Carga y sincronización de agendas desde el backend */
async function refreshAgendasList() {
  const data = await API.get('/api/agendas');
  APP.agendas = data.agendas || [];
  renderSel(S.agendaId || APP.agendas[0]?.id);
}

function renderSel(selectedId) {
  $('ag-sel').innerHTML = APP.agendas.map(a =>
    `<option value="${a.id}"${a.id === selectedId ? ' selected' : ''}>${esc(a.name)}</option>`
  ).join('');
}

async function loadAgenda(id, keepView = false) {
  if (!id) return;
  const data = await API.get(`/api/agendas/${id}`);
  S.agendaId = data.id;
  S.slug = data.slug;
  S.publicBooking = data.publicBooking;
  S.autoConfirmPublic = data.autoConfirmPublic;
  S.workDays = data.workDays;
  S.hourStart = data.hourStart;
  S.hourEnd = data.hourEnd;
  S.slotDur = data.slotDur;
  S.breaks = data.breaks;
  S.phone = data.phone;
  S.address = data.address;
  S.services = data.services || [];
  S.appointments = data.appointments || [];
  S.clients = data.clients || [];
  if (!keepView) {
    S.today = new Date();
    S.calDate = new Date();
    S.miniDate = new Date();
    S.selectedDay = fmtKey(S.today);
  }
  $('biz-name').textContent = data.name;
  renderSel(id);
  if (keepView) {
    VIEWS[S.view]?.();
  } else {
    switchView('cal');
  }
}

function openPublicLink() {
  if (!S.slug) return;
  const url = `${window.location.origin}/reservar/${S.slug}`;
  gm('Portal público de reservas', `
    <p class="hint">${S.publicBooking ? 'Comparte este enlace o código QR para que tus clientes reserven citas en línea según tu disponibilidad real.' : '<b>Reservas públicas desactivadas.</b> Actívalas en Horarios → Información del negocio.'}</p>
    <div class="public-link-box">
      <input class="form-input" id="pub-url" value="${esc(url)}" readonly>
      <button class="btn btn-primary" onclick="navigator.clipboard?.writeText($('pub-url').value);this.textContent='¡Copiado!'"><i class="ti ti-copy"></i> Copiar</button>
      <a class="btn" href="${esc(url)}" target="_blank" rel="noopener"><i class="ti ti-external-link"></i> Abrir</a>
    </div>
    <div class="qr-wrap"><div id="pub-qr"></div></div>`);
  if (window.QRCode) {
    new QRCode($('pub-qr'), { text: url, width: 170, height: 170 });
  }
}
