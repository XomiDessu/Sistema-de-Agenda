/* Vista Clientes: catálogo, búsqueda e historial de citas */
let clientSearch = '';

async function renderClients() {
  const body = $('clients-body');
  if (!S.agendaId) return;
  body.innerHTML = '<p class="hint">Cargando clientes...</p>';
  try {
    const data = await API.get(`/api/agendas/${S.agendaId}/clients`);
    S.clients = data.clients || [];
    drawClientsTable();
  } catch (e) {
    body.innerHTML = `<div class="err">${esc(e.message)}</div>`;
  }
}

function drawClientsTable() {
  const q = clientSearch.toLowerCase();
  const list = S.clients.filter(c => !q || (c.name + ' ' + c.phone + ' ' + c.email).toLowerCase().includes(q));
  const rows = list.length ? list.map(c => `<tr>
    <td><b>${esc(c.name)}</b><br><small>${esc(c.notes || '')}</small></td>
    <td>${esc(c.phone || '—')}<br><small>${esc(c.email || '')}</small></td>
    <td style="text-align:center">${c.total_apts || 0} <small>(${c.cancelled_apts || 0} canc.)</small></td>
    <td>${esc(c.last_visit || '—')}</td>
    <td style="text-align:right">
      <button class="btn" onclick="viewClientHistory(${c.id})">Historial</button>
      <button class="icon-btn" onclick="openClientModal(${c.id})" title="Editar"><i class="ti ti-edit"></i></button>
      <button class="icon-btn" onclick="deleteClient(${c.id})" title="Eliminar"><i class="ti ti-trash"></i></button>
    </td>
  </tr>`).join('') : '<tr><td colspan="5" style="text-align:center;color:var(--text3);padding:20px">Sin clientes registrados</td></tr>';

  $('clients-body').innerHTML = `
    <div class="settings-card">
      <div class="toolbar-inline">
        <input class="form-input" placeholder="Buscar por nombre, teléfono o correo..." value="${esc(clientSearch)}" oninput="clientSearch=this.value;drawClientsTable()" style="flex:1">
      </div>
      <table class="tbl">
        <thead><tr><th>Cliente</th><th>Contacto</th><th style="text-align:center">Citas</th><th>Última visita</th><th></th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

function openClientModal(cid) {
  const c = cid ? S.clients.find(x => x.id === cid) : null;
  gm(c ? 'Editar cliente' : 'Nuevo cliente', `
    <div class="err" id="cl-err"></div>
    <div class="form-group"><label class="form-label">Nombre</label><input class="form-input" id="cl-name" value="${esc(c?.name || '')}"></div>
    <div class="form-row">
      <div class="form-group"><label class="form-label">Teléfono</label><input class="form-input" id="cl-phone" value="${esc(c?.phone || '')}"></div>
      <div class="form-group"><label class="form-label">Correo</label><input class="form-input" id="cl-email" type="email" value="${esc(c?.email || '')}"></div>
    </div>
    <div class="form-group"><label class="form-label">Notas</label><input class="form-input" id="cl-notes" value="${esc(c?.notes || '')}"></div>
    <div class="btn-row"><button class="btn btn-primary" onclick="saveClient(${c ? c.id : 'null'})"><i class="ti ti-check"></i> Guardar</button></div>`);
}

async function saveClient(cid) {
  const payload = { name: v('cl-name'), phone: v('cl-phone'), email: v('cl-email'), notes: v('cl-notes') };
  try {
    if (cid) await API.put(`/api/agendas/${S.agendaId}/clients/${cid}`, payload);
    else await API.post(`/api/agendas/${S.agendaId}/clients`, payload);
    gmClose();
    renderClients();
  } catch (e) {
    const el = $('cl-err'); if (el) el.textContent = e.message;
  }
}

async function deleteClient(cid) {
  if (!confirm('¿Eliminar este cliente del catálogo? Las citas existentes se conservarán.')) return;
  await API.del(`/api/agendas/${S.agendaId}/clients/${cid}`);
  renderClients();
}

async function viewClientHistory(cid) {
  try {
    const data = await API.get(`/api/agendas/${S.agendaId}/clients/${cid}/history`);
    const rows = data.appointments.length ? data.appointments.map(a =>
      `<tr><td>${esc(a.date)} ${esc(a.time)}</td><td>${esc(a.service)}</td><td>${esc(a.status)}</td><td>${fmtMoney(a.price)}</td></tr>`
    ).join('') : '<tr><td colspan="4" style="text-align:center;color:var(--text3)">Sin citas registradas</td></tr>';
    gm(`Historial · ${data.client.name}`, `
      <p class="hint">${esc(data.client.phone || '')} ${data.client.email ? '· ' + esc(data.client.email) : ''}</p>
      <table class="tbl"><thead><tr><th>Fecha</th><th>Servicio</th><th>Estado</th><th>Precio</th></tr></thead><tbody>${rows}</tbody></table>`);
  } catch (e) {
    alert(e.message);
  }
}
