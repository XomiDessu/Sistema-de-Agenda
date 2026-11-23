/* Vista Servicios */
function renderServices() {
  const list = $('services-list');
  if (!S.services.length) {
    list.innerHTML = '<p style="font-size:12px;color:var(--text3);padding:8px 0">Sin servicios registrados</p>';
    return;
  }
  list.innerHTML = S.services.map(s =>
    `<div class="service-row">
      <span class="service-name">${esc(s.name)}</span>
      <span class="service-detail">${s.dur}</span>
      <span class="service-detail">${esc(s.price)}</span>
      <button class="break-del" onclick="deleteService(${s.id})" aria-label="Eliminar"><i class="ti ti-trash"></i></button>
    </div>`
  ).join('');
}

async function saveService() {
  const name = v('svc-name');
  const dur = parseInt($('svc-dur').value) || 30;
  const price = v('svc-price') || '$0';
  if (!name) { alert('Escribe el nombre del servicio.'); return; }
  try {
    const created = await API.post(`/api/agendas/${S.agendaId}/services`, { name, dur, price });
    S.services.push(created);
    $('svc-name').value = ''; $('svc-dur').value = ''; $('svc-price').value = '';
    renderServices();
  } catch (e) {
    alert(e.message);
  }
}

async function deleteService(sid) {
  if (!confirm('¿Eliminar servicio?')) return;
  try {
    await API.del(`/api/agendas/${S.agendaId}/services/${sid}`);
    S.services = S.services.filter(s => s.id !== sid);
    renderServices();
  } catch (e) {
    alert(e.message);
  }
}
