/* Calendario mensual y mini-calendario */
function renderCal() {
  const d = S.calDate;
  $('cal-month-title').textContent = MONTHS[d.getMonth()] + ' ' + d.getFullYear();

  // Week header
  const hdr = $('cal-week-header');
  hdr.innerHTML = DAYS_SHORT.map((n,i) =>
    `<div class="cal-week-day${new Date().getDay()===i?' today-col':''}">${n}</div>`
  ).join('');

  // Grid
  const grid = $('cal-grid');
  grid.innerHTML = '';
  const y=d.getFullYear(), m=d.getMonth();
  const first = new Date(y,m,1).getDay();
  const last  = new Date(y,m+1,0).getDate();
  const total = Math.ceil((first+last)/7)*7;

  for (let i=0; i<total; i++) {
    const dayN = i - first + 1;
    const date = new Date(y, m, dayN);
    const key  = fmtKey(date);
    const dow  = date.getDay();
    const isWork  = S.workDays.includes(dow);
    const isToday = sameDay(date, S.today);
    const isSel   = S.selectedDay && sameDay(date, parseKey(S.selectedDay));
    const isOther = date.getMonth() !== m;
    const apts    = S.appointments.filter(a => a.date===key);

    let cls = 'cal-cell';
    if (!isWork)  cls += ' off-day';
    if (isToday)  cls += ' today';
    if (isSel)    cls += ' selected-day';
    if (isOther)  cls += ' other-month';

    let inner = '';
    if (dayN > 0 && dayN <= last) {
      // Appointments (max 2)
      apts.slice(0,2).forEach(a => {
        inner += `<div class="cal-apt ${a.status}" onclick="event.stopPropagation();editApt(${a.id})">${a.time} ${esc(a.client.split(' ')[0])}</div>`;
      });
      if (apts.length > 2) inner += `<div class="cal-more">+${apts.length-2} más</div>`;
      // Breaks (only work days)
      if (isWork && !isOther) {
        S.breaks.forEach(b => { inner += `<div class="cal-apt break">${b.start} ${esc(b.label)}</div>`; });
      }
    }

    const numHtml = `<div class="cal-date"><div class="cal-date-num">${dayN>0&&dayN<=last ? dayN : ''}</div></div>`;
    grid.innerHTML += `<div class="${cls}" onclick="selectDay('${key}')">${numHtml}${inner}</div>`;
  }
  updateStats();
}

function renderMiniCal() {
  const d = S.miniDate;
  $('mini-month-label').textContent = MONTHS[d.getMonth()].slice(0,3)+' '+d.getFullYear();
  $('mini-day-labels').innerHTML = DAYS_SHORT.map(x=>`<div class="mini-day-label">${x[0]}</div>`).join('');
  const grid = $('mini-cal-grid');
  grid.innerHTML = '';
  const y=d.getFullYear(), m=d.getMonth();
  const first=new Date(y,m,1).getDay(), last=new Date(y,m+1,0).getDate();
  const total=Math.ceil((first+last)/7)*7;
  for (let i=0; i<total; i++) {
    const dayN=i-first+1, date=new Date(y,m,dayN), key=fmtKey(date);
    const isWork=S.workDays.includes(date.getDay());
    const isToday=sameDay(date,S.today);
    const isSel=S.selectedDay===key;
    const isOther=date.getMonth()!==m;
    const hasApt=S.appointments.some(a=>a.date===key);
    let cls='mini-day';
    if (isToday)      cls+=' today';
    else if (isSel)   cls+=' selected';
    if (isOther)      cls+=' other-month';
    if (!isWork)      cls+=' off-day';
    if (hasApt&&!isOther) cls+=' has-apt';
    grid.innerHTML += `<div class="${cls}" onclick="selectDay('${key}')">${dayN>0&&dayN<=last?dayN:''}</div>`;
  }
}

function selectDay(key) {
  S.selectedDay = key;
  // sync mini calendar month if needed
  const d = parseKey(key);
  S.miniDate = new Date(d);
  renderCal(); renderMiniCal(); renderDayPanel();
}

