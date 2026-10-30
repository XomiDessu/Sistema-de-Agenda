/* Vista Horarios: días, horas, descansos, datos del negocio */
function renderSettings() {
  // Days
  $('days-grid').innerHTML = DAYS_SHORT.map((n,i)=>
    `<div class="day-toggle ${S.workDays.includes(i)?'on':'off'}" onclick="toggleDay(${i})">
      <span class="day-toggle-name">${n}</span>
      <div class="day-toggle-dot"></div>
    </div>`
  ).join('');
  // Hours
  const hs=$('hour-start'), he=$('hour-end');
  hs.innerHTML=''; he.innerHTML='';
  for (let h=6; h<24; h++) {
    for (let m=0; m<60; m+=30) {
      const val=pad(h)+':'+pad(m);
      hs.innerHTML+=`<option value="${val}"${val===S.hourStart?' selected':''}>${val}</option>`;
      he.innerHTML+=`<option value="${val}"${val===S.hourEnd?' selected':''}>${val}</option>`;
    }
  }
  // Durations
  $('dur-row').innerHTML = [15,20,30,45,60,90,120].map(d=>
    `<button class="dur-btn${d===S.slotDur?' active':''}" onclick="setDur(${d})">${d} min</button>`
  ).join('');
  renderBreaksList();
  // Biz info
  $('biz-input').value = $('biz-name').textContent;
}

function renderBreaksList() {
  const list=$('breaks-list');
  if (!S.breaks.length) { list.innerHTML='<p style="font-size:12px;color:var(--text3);padding:8px 0">Sin descansos configurados</p>'; return; }
  list.innerHTML = S.breaks.map((b,i)=>
    `<div class="break-item">
      <span class="break-time">${b.start} — ${b.end}</span>
      <span class="break-label">${esc(b.label)}</span>
      <button class="break-del" onclick="deleteBreak(${i})" aria-label="Eliminar"><i class="ti ti-trash"></i></button>
    </div>`
  ).join('');
}

function toggleDay(i) {
  if (S.workDays.includes(i)) S.workDays = S.workDays.filter(x=>x!==i);
  else S.workDays.push(i);
  renderSettings();
}
function setDur(d) { S.slotDur=d; renderSettings(); }
function addBreak() {
  const s=$('break-start').value, e=$('break-end').value, l=$('break-label').value||'Descanso';
  if (!s||!e||s>=e) { alert('La hora de inicio debe ser anterior al fin.'); return; }
  S.breaks.push({start:s,end:e,label:l});
  $('break-label').value='';
  renderBreaksList();
}
function deleteBreak(i) { S.breaks.splice(i,1); renderBreaksList(); }
function saveSettings() {
  S.hourStart = $('hour-start').value;
  S.hourEnd   = $('hour-end').value;
  const name  = $('biz-input').value.trim() || 'Mi Negocio';
  $('biz-name').textContent = name;
  renderCal(); renderMiniCal(); renderDayPanel();
  const btn=$('save-settings-btn');
  btn.innerHTML='<i class="ti ti-check"></i> ¡Guardado!';
  setTimeout(()=>{ btn.innerHTML='<i class="ti ti-check"></i> Guardar'; }, 1800);
}

