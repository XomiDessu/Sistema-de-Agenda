/* Panel "Mis agendas" */
function openAgendas(){
  const m=me(),L=DB.agendas.filter(a=>a.owner===m.id||isAdmin());
  gm('Mis agendas',`<table class="tbl">${L.map(a=>{const o=DB.users.find(u=>u.id===a.owner);return `<tr><td>${esc(a.name)}${a.owner!==m.id?` <small>(${esc(o?.user)})</small>`:''}</td><td style="text-align:right"><button class="btn" onclick="loadAgenda('${a.id}');gmClose()">Abrir</button> <button class="btn" onclick="renAgenda('${a.id}')">Renombrar</button> <button class="btn btn-danger" onclick="delAgenda('${a.id}')">Eliminar</button></td></tr>`}).join('')}</table>
  <div class="form-row" style="margin-top:14px"><input class="form-input" id="n-ag" maxlength="40" placeholder="Nombre del nuevo negocio"><button class="btn btn-primary" onclick="addAgenda()">Crear agenda</button></div>`);
}
function addAgenda(){const n=v('n-ag');if(!n)return;const a=newAgenda(n);save();loadAgenda(a.id);openAgendas()}
function renAgenda(id){
  const a=ag(id),n=a&&prompt('Nuevo nombre',a.name);if(!n||!n.trim())return;
  a.name=n.trim().slice(0,40);log('Agenda renombrada: '+a.name);save();
  if(id===S.agendaId)$('biz-name').textContent=a.name;renderSel(S.agendaId);openAgendas();
}
function delAgenda(id){
  const a=ag(id);if(!a||!confirm('¿Eliminar la agenda "'+a.name+'" y todas sus citas? No se puede deshacer.'))return;
  DB.agendas=DB.agendas.filter(x=>x.id!==id);log('Agenda eliminada: '+a.name);save();
  if(id===S.agendaId)loadAgenda((DB.agendas.find(x=>x.owner===me().id)||newAgenda('Mi negocio')).id);else renderSel(S.agendaId);
  openAgendas();
}

