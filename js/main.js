/* Arranque: muestra el login o retoma la sesión activa */
function boot() {
  $('auth').addEventListener('keydown', e => { if (e.key === 'Enter') $('auth').querySelector('.btn-primary')?.click(); });
  const m = me(); if (m) return start(m, true);
  sess = null; authView(DB.users.length ? 'login' : 'reg');
}
boot();
