/* Pestaña Perfil */
function tabPerfil(m) {
  return `<div class="settings-card"><div class="settings-card-title"><i class="ti ti-user"></i> Datos de la cuenta</div>
    <div class="form-row">
      <div class="form-group"><label class="form-label" for="pf-user">Usuario</label><input class="form-input" id="pf-user" value="${esc(m.user)}" disabled></div>
      <div class="form-group"><label class="form-label" for="pf-role">Rol</label><input class="form-input" id="pf-role" value="${m.role === 'admin' ? 'Administrador' : 'Usuario'}" disabled></div>
    </div>
    <div class="form-group"><label class="form-label" for="pf-name">Nombre</label><input class="form-input" id="pf-name" maxlength="40" autocomplete="name" value="${esc(m.name)}"></div>
    <button class="btn btn-primary" onclick="saveProfile()"><i class="ti ti-check"></i> Guardar</button>
  </div>`;
}
async function saveProfile() {
  try {
    const res = await API.put('/api/account/profile', { name: v('pf-name') });
    $('u-name').textContent = res.name;
    acMsg(res.message, true);
  } catch (e) { acMsg(e.message); }
}
