/* Modal para crear/editar citas */
function populateServiceSelect() {
  $('apt-service').innerHTML = S.services.map(s=>`<option value="${esc(s.name)}">${esc(s.name)} (${s.dur}min)</option>`).join('');
}
function setStatus(s, el) {
  S.modalStatus = s;
  document.querySelectorAll('.status-opt').forEach(x=>x.classList.remove('active'));
  el.classList.add('active');
}
function openNewApt() {
  S.editingAptId = null;
  $('modal-title').textContent = 'Nueva cita';
  $('apt-client').value = ''; $('apt-phone').value='';
  $('apt-date').value   = S.selectedDay || fmtKey(S.today);
  $('apt-time').value   = S.hourStart;
  $('apt-notes').value  = '';
  $('modal-del-btn').style.display='none';
  S.modalStatus='confirmed';
  document.querySelectorAll('.status-opt').forEach(x=>{
    x.classList.remove('active');
    if (x.classList.contains('confirmed')) x.classList.add('active');
  });
  populateServiceSelect();
  $('modal').classList.add('open');
  $('apt-client').focus();
}
function openNewAptAt(date,time) {
  openNewApt();
  $('apt-date').value=date;
  $('apt-time').value=time;
}
function editApt(id) {
  const apt=S.appointments.find(a=>a.id===id);
  if(!apt) return;
  S.editingAptId=id;
  $('modal-title').textContent='Editar cita';
  $('apt-client').value=apt.client;
  $('apt-phone').value=apt.phone||'';
  $('apt-date').value=apt.date;
  $('apt-time').value=apt.time;
  $('apt-notes').value=apt.notes||'';
  $('modal-del-btn').style.display='inline-flex';
  S.modalStatus=apt.status;
  populateServiceSelect();
  $('apt-service').value=apt.service;
  document.querySelectorAll('.status-opt').forEach(x=>{
    x.classList.remove('active');
    if (x.classList.contains(apt.status)) x.classList.add('active');
  });
  $('modal').classList.add('open');
}
function saveApt() {
  const client=$('apt-client').value.trim();
  const date=$('apt-date').value;
  const time=$('apt-time').value;
  const service=$('apt-service').value;
  if(!client||!date||!time){alert('Cliente, fecha y hora son obligatorios.');return;}
  const data={ client, phone:$('apt-phone').value.trim(), date, time, service, notes:$('apt-notes').value.trim(), status:S.modalStatus };
  if (S.editingAptId) {
    const idx=S.appointments.findIndex(a=>a.id===S.editingAptId);
    S.appointments[idx]={...S.appointments[idx],...data};
  } else {
    S.appointments.push({id:Date.now(),...data});
  }
  closeModal();
  renderCal(); renderMiniCal(); renderDayPanel();
  if (S.view==='agenda') renderAgenda();
}
function deleteApt() {
  if (!confirm('¿Eliminar esta cita?')) return;
  S.appointments=S.appointments.filter(a=>a.id!==S.editingAptId);
  closeModal(); renderCal(); renderMiniCal(); renderDayPanel();
  if (S.view==='agenda') renderAgenda();
}
function closeModal() { $('modal').classList.remove('open'); }
function closeModalOutside(e) { if(e.target===$('modal')) closeModal(); }
