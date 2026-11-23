/* Vista Reportes y Exportación CSV / .ICS */
let repFrom = '', repTo = '';

async function renderReports() {
  const body = $('reports-body');
  if (!S.agendaId) return;
  const qs = new URLSearchParams();
  if (repFrom) qs.set('from', repFrom);
  if (repTo) qs.set('to', repTo);
  try {
    const r = await API.get(`/api/agendas/${S.agendaId}/reports?${qs.toString()}`);
    const svcRows = r.byService.length ? r.byService.map(s =>
      `<tr><td>${esc(s.service)}</td><td style="text-align:center">${s.count}</td><td style="text-align:center">${s.cancelled}</td><td style="text-align:right">${fmtMoney(s.revenue)}</td></tr>`
    ).join('') : '<tr><td colspan="4" style="text-align:center;color:var(--text3);padding:16px">Sin datos en el rango seleccionado</td></tr>';

    body.innerHTML = `
      <div class="settings-card">
        <div class="toolbar-inline">
          <label class="form-label" style="margin:0">Desde</label>
          <input type="date" class="form-input" value="${esc(repFrom)}" onchange="repFrom=this.value;renderReports()">
          <label class="form-label" style="margin:0">Hasta</label>
          <input type="date" class="form-input" value="${esc(repTo)}" onchange="repTo=this.value;renderReports()">
          <button class="btn" onclick="repFrom='';repTo='';renderReports()">Limpiar</button>
        </div>
        <div class="kpi-grid">
          <div class="kpi-card"><div class="kpi-val">${fmtMoney(r.revenueConfirmed)}</div><div class="kpi-label">Ingresos confirmados/completados</div></div>
          <div class="kpi-card"><div class="kpi-val">${fmtMoney(r.revenuePending)}</div><div class="kpi-label">Ingresos pendientes</div></div>
          <div class="kpi-card"><div class="kpi-val">${r.totals.total}</div><div class="kpi-label">Citas totales (${r.totals.confirmed + r.totals.completed} activas)</div></div>
          <div class="kpi-card"><div class="kpi-val">${r.cancelRate}%</div><div class="kpi-label">Tasa de cancelación (${r.totals.cancelled})</div></div>
          <div class="kpi-card"><div class="kpi-val">${r.uniqueClients}</div><div class="kpi-label">Clientes únicos atendidos</div></div>
        </div>
      </div>
      <div class="settings-card">
        <div class="settings-card-title"><i class="ti ti-chart-pie"></i> Desglose por servicio</div>
        <table class="tbl">
          <thead><tr><th>Servicio</th><th style="text-align:center">Citas</th><th style="text-align:center">Canceladas</th><th style="text-align:right">Ingresos</th></tr></thead>
          <tbody>${svcRows}</tbody>
        </table>
      </div>`;
  } catch (e) {
    body.innerHTML = `<div class="err">${esc(e.message)}</div>`;
  }
}

function downloadExport(fmt) {
  if (!S.agendaId) return;
  window.location.href = `/api/agendas/${S.agendaId}/export.${fmt}`;
}
