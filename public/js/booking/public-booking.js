/* Portal público de reservas en línea (/reservar/<slug>) */
const slug = decodeURIComponent(location.pathname.replace(/^\/reservar\//, '').replace(/\/+$/, ''));
let pubAgenda = null, pubSlot = '';

async function initBooking() {
  const root = $('booking-root');
  if (!slug) { root.innerHTML = '<div class="err">Enlace de agenda inválido.</div>'; return; }
  try {
    const res = await fetch(`/api/public/agendas/${encodeURIComponent(slug)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Agenda no disponible');
    pubAgenda = data;
    document.title = `Reservar · ${data.name}`;
    const today = fmtKey(new Date());
    root.innerHTML = `
      <div class="booking-header">
        <div class="brand-icon" style="margin:0"><i class="ti ti-calendar-event"></i></div>
        <div>
          <h2 style="font-size:18px;margin:0">${esc(data.name)}</h2>
          <p class="hint" style="margin:2px 0 0">${esc(data.address || '')}${data.phone ? ' · ' + esc(data.phone) : ''}</p>
        </div>
      </div>
      <div class="err" id="bk-err" role="alert"></div>
      <div class="form-group">
        <label class="form-label">1. Elige un servicio</label>
        <select class="form-input" id="bk-svc" onchange="loadPubSlots()">
          ${data.services.map(s => `<option value="${s.id}">${esc(s.name)} — ${s.dur} min (${esc(s.price)})</option>`).join('')}
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">2. Elige fecha</label>
        <input type="date" class="form-input" id="bk-date" min="${today}" value="${today}" onchange="loadPubSlots()">
      </div>
      <div class="form-group">
        <label class="form-label">3. Horarios disponibles</label>
        <div id="bk-slots" class="slots-grid"><p class="hint">Cargando...</p></div>
      </div>
      <div class="form-group"><label class="form-label">4. Tu nombre completo</label><input class="form-input" id="bk-name" placeholder="Nombre y apellido"></div>
      <div class="form-row">
        <div class="form-group"><label class="form-label">Teléfono / WhatsApp</label><input class="form-input" id="bk-phone" placeholder="+52 ..."></div>
        <div class="form-group"><label class="form-label">Correo electrónico (para confirmación)</label><input class="form-input" id="bk-email" type="email" placeholder="tu@correo.com"></div>
      </div>
      <div class="form-group"><label class="form-label">Notas (opcional)</label><input class="form-input" id="bk-notes" placeholder="Comentarios adicionales..."></div>
      <button class="btn btn-primary" style="width:100%;justify-content:center;padding:10px" onclick="submitBooking()"><i class="ti ti-check"></i> Confirmar reserva</button>`;
    loadPubSlots();
  } catch (e) {
    root.innerHTML = `<div class="err">${esc(e.message)}</div>`;
  }
}

async function loadPubSlots() {
  pubSlot = '';
  const date = $('bk-date').value, svcId = $('bk-svc').value, box = $('bk-slots');
  box.innerHTML = '<p class="hint">Buscando horarios...</p>';
  try {
    const res = await fetch(`/api/public/agendas/${encodeURIComponent(slug)}/slots?date=${encodeURIComponent(date)}&service_id=${encodeURIComponent(svcId)}`);
    const data = await res.json();
    if (!data.slots || !data.slots.length) {
      box.innerHTML = '<p class="hint" style="grid-column:1/-1">No hay horarios disponibles para esta fecha. Prueba otro día.</p>';
      return;
    }
    box.innerHTML = data.slots.map(t => `<button type="button" class="slot-chip" onclick="pickSlot('${t}',this)">${t}</button>`).join('');
  } catch (e) {
    box.innerHTML = `<div class="err">${esc(e.message)}</div>`;
  }
}

function pickSlot(t, el) {
  pubSlot = t;
  document.querySelectorAll('.slot-chip').forEach(x => x.classList.remove('active'));
  el.classList.add('active');
}

async function submitBooking() {
  const errEl = $('bk-err'); errEl.textContent = '';
  const payload = {
    serviceId: +$('bk-svc').value,
    date: $('bk-date').value,
    time: pubSlot,
    client: v('bk-name'),
    phone: v('bk-phone'),
    email: v('bk-email'),
    notes: v('bk-notes')
  };
  if (!payload.time) { errEl.textContent = 'Selecciona un horario disponible.'; return; }
  if (!payload.client) { errEl.textContent = 'Escribe tu nombre completo.'; return; }
  try {
    const res = await fetch(`/api/public/agendas/${encodeURIComponent(slug)}/book`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'No se pudo completar la reserva');
    $('booking-root').innerHTML = `
      <div style="text-align:center;padding:18px 8px">
        <div class="brand-icon" style="margin:0 auto 12px"><i class="ti ti-check"></i></div>
        <h2>${esc(data.message)}</h2>
        <p class="hint" style="margin:10px 0 18px">Fecha: <b>${esc(payload.date)}</b> a las <b>${esc(payload.time)}</b><br>${esc(pubAgenda.name)}</p>
        <button class="btn btn-primary" onclick="location.reload()">Hacer otra reserva</button>
      </div>`;
  } catch (e) {
    errEl.textContent = e.message;
  }
}

initBooking();
