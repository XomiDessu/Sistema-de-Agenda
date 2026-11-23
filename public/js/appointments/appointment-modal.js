/* Modal para crear/editar citas con autocompletado de clientes, validación en servidor y recordatorios */
function populateServiceSelect() {
  $('apt-service').innerHTML = S.services.map(s =>
    `<option value="${esc(s.name)}">${esc(s.name)} (${s.dur}min · ${esc(s.price)})</option>`
  ).join('');
}
function populateClientsDatalist() {
  const dl = $('clients-datalist');
  if (!dl) return;
  dl.innerHTML = (S.clients || []).map(c => `<option value="${esc(c.name)}"></option>`).join('');
}
function autofillClient(nameVal) {
  const match = (S.clients || []).find(c => c.name.toLowerCase() === nameVal.trim().toLowerCase());
  if (match) {
    if (match.phone && !$('apt-phone').value) $('apt-phone').value = match.phone;
    if (match.email && !$('apt-email').value) $('apt-email').value = match.email;
  }
}
function setStatus(s, el) {
  S.modalStatus = s;
  document.querySelectorAll('.status-opt').forEach(x => x.classList.remove('active'));
  el.classList.add('active');
}
function openNewApt() {
  S.editingAptId = null;
  $('modal-title').textContent = 'Nueva cita';
  $('apt-err').textContent = '';
  $('apt-client').value = ''; $('apt-phone').value = ''; $('apt-email').value = '';
  $('apt-date').value = S.selectedDay || fmtKey(S.today);
  $('apt-time').value = S.hourStart;
  $('apt-notes').value = '';
  $('modal-del-btn').style.display = 'none';
  $('modal-remind-btn').style.display = 'none';
  S.modalStatus = 'confirmed';
  document.querySelectorAll('.status-opt').forEach(x => {
    x.classList.remove('active');
    if (x.classList.contains('confirmed')) x.classList.add('active');
  });
  populateServiceSelect();
  populateClientsDatalist();
  $('modal').classList.add('open');
  $('apt-client').focus();
}
function openNewAptAt(date, time) {
  openNewApt();
  $('apt-date').value = date;
  $('apt-time').value = time;
}
function editApt(id) {
  const apt = S.appointments.find(a => a.id === id);
  if (!apt) return;
  S.editingAptId = id;
  $('modal-title').textContent = 'Editar cita';
  $('apt-err').textContent = '';
  $('apt-client').value = apt.client;
  $('apt-phone').value = apt.phone || '';
  $('apt-email').value = apt.email || '';
  $('apt-date').value = apt.date;
  $('apt-time').value = apt.time;
  $('apt-notes').value = apt.notes || '';
  $('modal-del-btn').style.display = 'inline-flex';
  $('modal-remind-btn').style.display = apt.email ? 'inline-flex' : 'none';
  S.modalStatus = apt.status;
  populateServiceSelect();
  populateClientsDatalist();
  $('apt-service').value = apt.service;
  document.querySelectorAll('.status-opt').forEach(x => {
    x.classList.remove('active');
    if (x.classList.contains(apt.status)) x.classList.add('active');
  });
  $('modal').classList.add('open');
}
async function saveApt() {
  const errEl = $('apt-err');
  errEl.textContent = '';
  const payload = {
    client: v('apt-client'),
    phone: v('apt-phone'),
    email: v('apt-email'),
    date: $('apt-date').value,
    time: $('apt-time').value,
    service: $('apt-service').value,
    notes: v('apt-notes'),
    status: S.modalStatus
  };
  if (!payload.client || !payload.date || !payload.time) {
    errEl.textContent = 'Cliente, fecha y hora son obligatorios.';
    return;
  }
  try {
    if (S.editingAptId) {
      await API.put(`/api/agendas/${S.agendaId}/appointments/${S.editingAptId}`, payload);
    } else {
      await API.post(`/api/agendas/${S.agendaId}/appointments`, payload);
    }
    closeModal();
    await loadAgenda(S.agendaId, true);
  } catch (e) {
    errEl.textContent = e.message;
  }
}
async function deleteApt() {
  if (!confirm('¿Eliminar esta cita?')) return;
  try {
    await API.del(`/api/agendas/${S.agendaId}/appointments/${S.editingAptId}`);
    closeModal();
    await loadAgenda(S.agendaId, true);
  } catch (e) {
    $('apt-err').textContent = e.message;
  }
}
async function remindApt() {
  if (!S.editingAptId) return;
  try {
    const r = await API.post(`/api/agendas/${S.agendaId}/appointments/${S.editingAptId}/remind`, {});
    alert(r.message);
  } catch (e) {
    $('apt-err').textContent = e.message;
  }
}
async function sendTomorrowReminders() {
  if (!S.agendaId) return;
  try {
    const r = await API.post(`/api/agendas/${S.agendaId}/send-reminders`, {});
    alert(r.message);
  } catch (e) {
    alert(e.message);
  }
}
function closeModal() { $('modal').classList.remove('open'); }
function closeModalOutside(e) { if (e.target === $('modal')) closeModal(); }
