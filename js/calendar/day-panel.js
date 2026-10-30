/* Panel del día y generación de horarios */
function renderDayPanel() {
  if (!S.selectedDay) {
    $('panel-date-title').textContent = 'Selecciona un día';
    $('panel-date-sub').textContent = '';
    $('day-slots').innerHTML = '';
    return;
  }
  const date = parseKey(S.selectedDay);
  const dow  = date.getDay();
  $('panel-date-title').textContent = `${DAYS_FULL[dow]} ${date.getDate()} de ${MONTHS[date.getMonth()]}`;
  const isWork = S.workDays.includes(dow);
  if (!isWork) {
    $('panel-date-sub').textContent = 'Día no laborable';
    $('day-slots').innerHTML = `<div class="empty-hint"><i class="ti ti-moon"></i>Día de descanso</div>`;
    $('ps-count').textContent = 0;
    $('ps-avail').textContent = 0;
    return;
  }
  $('panel-date-sub').textContent = 'Día laborable';
  const slots = generateSlots();
  const apts  = S.appointments.filter(a => a.date===S.selectedDay);
  let html='', aptCount=0, availCount=0;
  slots.forEach(t => {
    const br = S.breaks.find(b => t>=b.start && t<b.end);
    if (br) {
      if (t===br.start)
        html += `<div class="time-slot"><span class="time-label">${t}</span><div class="slot-block filled break-slot"><span class="slot-client">${esc(br.label)}</span>&nbsp;<span class="slot-service">Descanso</span></div></div>`;
      return;
    }
    const apt = apts.find(a => a.time===t);
    if (apt) {
      aptCount++;
      html += `<div class="time-slot"><span class="time-label">${t}</span>
        <div class="slot-block filled ${apt.status}" onclick="editApt(${apt.id})">
          <div><div class="slot-client">${esc(apt.client)}</div><div class="slot-service">${esc(apt.service)}</div></div>
          <span class="slot-status ${apt.status}">${apt.status==='confirmed'?'✓ Conf':'⏳ Pend'}</span>
        </div></div>`;
    } else {
      availCount++;
      html += `<div class="time-slot"><span class="time-label">${t}</span>
        <div class="slot-block" onclick="openNewAptAt('${S.selectedDay}','${t}')">
          <span class="slot-add"><i class="ti ti-plus" style="font-size:12px"></i> Agregar cita</span>
        </div></div>`;
    }
  });
  $('day-slots').innerHTML = html || '<div class="empty-hint">Sin horarios configurados</div>';
  $('ps-count').textContent = aptCount;
  $('ps-avail').textContent = availCount;
}

function generateSlots() {
  const slots=[];
  const [sh,sm]=S.hourStart.split(':').map(Number);
  const [eh,em]=S.hourEnd.split(':').map(Number);
  let cur = sh*60+sm;
  const end = eh*60+em;
  while (cur < end) {
    slots.push(pad(Math.floor(cur/60))+':'+pad(cur%60));
    cur += S.slotDur;
  }
  return slots;
}

