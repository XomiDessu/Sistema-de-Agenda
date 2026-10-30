/* Estadísticas y navegación del calendario */
function updateStats() {
  const todayKey = fmtKey(S.today);
  const now=new Date();
  const ws=new Date(now); ws.setDate(now.getDate()-now.getDay());
  const we=new Date(ws); we.setDate(ws.getDate()+6);
  $('st-today').textContent   = S.appointments.filter(a=>a.date===todayKey).length;
  $('st-week').textContent    = S.appointments.filter(a=>{ const d=parseKey(a.date); return d>=ws&&d<=we; }).length;
  $('st-month').textContent   = S.appointments.filter(a=>{ const d=parseKey(a.date); return d.getMonth()===S.calDate.getMonth()&&d.getFullYear()===S.calDate.getFullYear(); }).length;
  $('st-pending').textContent = S.appointments.filter(a=>a.status==='pending').length;
}

/* ── Nav ── */
function calNav(dir) {
  S.calDate.setMonth(S.calDate.getMonth()+dir);
  S.miniDate = new Date(S.calDate);
  renderCal(); renderMiniCal();
}
function miniNav(dir) { S.miniDate.setMonth(S.miniDate.getMonth()+dir); renderMiniCal(); }
function goToday() {
  S.calDate     = new Date(S.today);
  S.miniDate    = new Date(S.today);
  S.selectedDay = fmtKey(S.today);
  renderCal(); renderMiniCal(); renderDayPanel();
}

