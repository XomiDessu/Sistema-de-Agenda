/* Vista Agenda */
function renderAgenda() {
  const body = $('agenda-body');
  const all  = [...S.appointments].sort((a,b)=>(a.date+a.time).localeCompare(b.date+b.time));
  if (!all.length) { body.innerHTML = '<div class="empty-hint" style="padding:60px 0"><i class="ti ti-calendar-off"></i>No hay citas registradas</div>'; return; }
  const grouped = {};
  all.forEach(a => { (grouped[a.date]||(grouped[a.date]=[])).push(a); });
  let html='';
  Object.keys(grouped).sort().forEach(key => {
    const date  = parseKey(key);
    const isToday = sameDay(date,S.today);
    const label = `${DAYS_FULL[date.getDay()]} ${date.getDate()} de ${MONTHS[date.getMonth()]} ${date.getFullYear()}`;
    html += `<div class="agenda-date-group">
      <div class="agenda-date-label">${isToday?'<span class="badge today">Hoy</span>&nbsp;':''}${label}</div>`;
    grouped[key].forEach(a => {
      html += `<div class="agenda-row" onclick="editApt(${a.id})">
        <div class="agenda-time-col"><div class="agenda-time">${a.time}</div><div class="agenda-dur">${S.slotDur}min</div></div>
        <div class="agenda-line ${a.status}"></div>
        <div class="agenda-info">
          <div class="agenda-client">${esc(a.client)}</div>
          <div class="agenda-service">${esc(a.service)}${a.notes?' · '+esc(a.notes):''}</div>
        </div>
        <div class="agenda-actions">
          <span class="agenda-badge ${a.status}">${a.status==='confirmed'?'Confirmada':a.status==='pending'?'Pendiente':'Cancelada'}</span>
          <button class="icon-btn" onclick="event.stopPropagation();editApt(${a.id})" aria-label="Editar"><i class="ti ti-edit"></i></button>
        </div>
      </div>`;
    });
    html += '</div>';
  });
  body.innerHTML = html;
}

