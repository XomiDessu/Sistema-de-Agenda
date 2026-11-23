/* Administración de usuarios y bitácora (solo admin) */
async function openUsers() {
  if (!isAdmin()) return;
  try {
    const data = await API.get('/api/admin/users');
    gm('Usuarios y bitácora', `<table class="tbl"><tr><th>Usuario</th><th>Rol</th><th>2FA</th><th>Activo</th><th></th></tr>${data.users.map(u => `<tr>
      <td>${esc(u.user)}<br><small>${esc(u.name)}</small></td>
      <td><select class="form-input" onchange="uSet('${u.id}',{role:this.value})"><option value="usuario"${u.role === 'usuario' ? ' selected' : ''}>Usuario</option><option value="admin"${u.role === 'admin' ? ' selected' : ''}>Admin</option></select></td>
      <td>${u.totpOn ? `Sí <button class="icon-btn" title="Restablecer 2FA" onclick="uSet('${u.id}',{reset2fa:true})"><i class="ti ti-refresh"></i></button>` : 'No'}</td>
      <td><input type="checkbox" ${u.active ? 'checked' : ''} onchange="uSet('${u.id}',{active:this.checked})"></td>
      <td><button class="icon-btn" onclick="uDel('${u.id}','${esc(u.user)}')"><i class="ti ti-trash"></i></button></td>
    </tr>`).join('')}</table>
    <h4 style="margin:16px 0 6px">Bitácora reciente</h4>
    <div style="max-height:160px;overflow:auto;font-size:11px">${data.log.map(l => `${esc(l.t)} · <b>${esc(l.u)}</b> · ${esc(l.e)}`).join('<br>')}</div>`);
  } catch (e) { alert(e.message); }
}
async function uSet(id, payload) {
  try { await API.put(`/api/admin/users/${id}`, payload); openUsers(); }
  catch (e) { alert(e.message); openUsers(); }
}
async function uDel(id, username) {
  if (!confirm(`¿Eliminar a ${username} y todas sus agendas?`)) return;
  try { await API.del(`/api/admin/users/${id}`); openUsers(); }
  catch (e) { alert(e.message); }
}
