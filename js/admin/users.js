/* Administración de usuarios y bitácora (solo admin) */
function openUsers(){
  if(!isAdmin())return;
  gm('Usuarios y bitácora',`<table class="tbl"><tr><th>Usuario</th><th>Rol</th><th>2FA</th><th>Activo</th><th></th></tr>${DB.users.map(u=>`<tr><td>${esc(u.user)}<br><small>${esc(u.name)}</small></td><td><select class="form-input" onchange="uSet('${u.id}','role',this.value)"><option value="usuario"${u.role==='usuario'?' selected':''}>Usuario</option><option value="admin"${u.role==='admin'?' selected':''}>Admin</option></select></td><td>${u.totp?`Sí <button class="icon-btn" title="Restablecer 2FA" onclick="uSet('${u.id}','2fa')"><i class="ti ti-refresh"></i></button>`:'No'}</td><td><input type="checkbox" ${u.active?'checked':''} onchange="uSet('${u.id}','active',this.checked)"></td><td><button class="icon-btn" onclick="uDel('${u.id}')"><i class="ti ti-trash"></i></button></td></tr>`).join('')}</table>
  <h4 style="margin:16px 0 6px">Bitácora reciente</h4><div style="max-height:150px;overflow:auto;font-size:11px">${DB.log.slice(0,25).map(l=>`${esc(l.t)} · <b>${esc(l.u)}</b> · ${esc(l.e)}`).join('<br>')}</div>`);
}
function uSet(id,k,val){
  const u=DB.users.find(x=>x.id===id);if(!isAdmin()||!u)return;
  const admins=DB.users.filter(x=>x.role==='admin'&&x.active).length;
  if(u.role==='admin'&&u.active&&admins<2&&((k==='role'&&val!=='admin')||(k==='active'&&!val))){alert('Debe existir al menos un administrador activo.');return openUsers()}
  if(k==='2fa'){u.totp=null;u.backup=[]}else u[k]=val;
  log('Admin modificó a '+u.user+': '+k);save();openUsers();
}
function uDel(id){
  const u=DB.users.find(x=>x.id===id);
  if(!isAdmin()||!u||u.id===me().id)return alert('No puedes eliminar tu propia cuenta.');
  if(!confirm('¿Eliminar a '+u.user+' y todas sus agendas?'))return;
  DB.users=DB.users.filter(x=>x.id!==id);DB.agendas=DB.agendas.filter(a=>a.owner!==id);log('Usuario eliminado: '+u.user);save();openUsers();
}

