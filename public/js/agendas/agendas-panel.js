/* Panel "Mis agendas" */
async function openAgendas() {
  await refreshAgendasList();
  const m = me();
  gm('Mis agendas', `<table class="tbl">${APP.agendas.map(a =>
    `<tr><td>${esc(a.name)}${a.ownerId !== m.id ? ` <small>(${esc(a.ownerUser)})</small>` : ''}</td>
     <td style="text-align:right">
       <button class="btn" onclick="loadAgenda('${a.id}');gmClose()">Abrir</button>
       <button class="btn" onclick="renAgenda('${a.id}','${esc(a.name)}')">Renombrar</button>
       <button class="btn btn-danger" onclick="delAgenda('${a.id}','${esc(a.name)}')">Eliminar</button>
     </td></tr>`
  ).join('')}</table>
  <div class="form-row" style="margin-top:14px">
    <input class="form-input" id="n-ag" maxlength="40" placeholder="Nombre del nuevo negocio">
    <button class="btn btn-primary" onclick="addAgenda()">Crear agenda</button>
  </div>`);
}

async function addAgenda() {
  const name = v('n-ag');
  if (!name) return;
  try {
    const a = await API.post('/api/agendas', { name });
    await refreshAgendasList();
    await loadAgenda(a.id);
    openAgendas();
  } catch (e) { alert(e.message); }
}

async function renAgenda(id, oldName) {
  const n = prompt('Nuevo nombre', oldName);
  if (!n || !n.trim()) return;
  try {
    await API.put(`/api/agendas/${id}`, { name: n.trim().slice(0, 40) });
    await refreshAgendasList();
    if (id === S.agendaId) $('biz-name').textContent = n.trim().slice(0, 40);
    openAgendas();
  } catch (e) { alert(e.message); }
}

async function delAgenda(id, name) {
  if (!confirm(`¿Eliminar la agenda "${name}" y todas sus citas? No se puede deshacer.`)) return;
  try {
    await API.del(`/api/agendas/${id}`);
    await refreshAgendasList();
    if (id === S.agendaId && APP.agendas.length) await loadAgenda(APP.agendas[0].id);
    openAgendas();
  } catch (e) { alert(e.message); }
}
