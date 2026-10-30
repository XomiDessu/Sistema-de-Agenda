/* Vista Servicios */
function renderServices() {
  const list=$('services-list');
  if (!S.services.length) { list.innerHTML='<p style="font-size:12px;color:var(--text3);padding:8px 0">Sin servicios registrados</p>'; return; }
  list.innerHTML = S.services.map((s,i)=>
    `<div class="service-row">
      <span class="service-name">${esc(s.name)}</span>
      <span class="service-detail">${s.dur}</span>
      <span class="service-detail">${esc(s.price)}</span>
      <button class="break-del" onclick="deleteService(${i})" aria-label="Eliminar"><i class="ti ti-trash"></i></button>
    </div>`
  ).join('');
}
function saveService() {
  const name=$('svc-name').value.trim();
  const dur=parseInt($('svc-dur').value)||30;
  const price=$('svc-price').value.trim()||'$0';
  if (!name) { alert('Escribe el nombre del servicio.'); return; }
  S.services.push({id:Date.now(),name,dur,price});
  $('svc-name').value=''; $('svc-dur').value=''; $('svc-price').value='';
  renderServices();
}
function deleteService(i) {
  if (!confirm('¿Eliminar servicio?')) return;
  S.services.splice(i,1); renderServices();
}

