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
function saveProfile() {
  const m = acUser(); if (!m) return;
  const n = v('pf-name');
  if (!n || n.length > 40) return acMsg('Nombre requerido (máx. 40 caracteres)');
  m.name = n; log('Perfil actualizado'); save();
  $('u-name').textContent = n;
  acMsg('Perfil actualizado.', true);
}
