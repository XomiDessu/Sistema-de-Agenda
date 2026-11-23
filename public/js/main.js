/* Arranque de la aplicación */
async function boot() {
  $('auth').addEventListener('keydown', e => {
    if (e.key === 'Enter') $('auth').querySelector('.btn-primary')?.click();
  });
  try {
    const st = await API.get('/api/auth/status');
    APP.needsSetup = st.needsSetup;
    APP.mailMode = st.mailMode;
    APP.appName = st.appName || 'Agenda de Citas';
    if (st.user) return await startSession(st.user);
    $('auth').style.display = 'flex';
    authView(st.needsSetup ? 'reg' : 'login');
  } catch (e) {
    $('auth').style.display = 'flex';
    $('auth-card').innerHTML = `<h2>Sin conexión con el servidor</h2><p class="err">${esc(e.message)}</p>`;
  }
}
boot();
