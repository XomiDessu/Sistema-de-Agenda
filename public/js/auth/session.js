/* Sesión respaldada por servidor (cookie HttpOnly + verificación periódica) */
const me = () => APP.user;
const isAdmin = () => APP.user?.role === 'admin';

setInterval(async () => {
  if (!APP.user) return;
  try {
    const st = await API.get('/api/auth/status');
    if (!st.user) {
      APP.user = null;
      alert('Sesión expirada por inactividad.');
      $('auth').style.display = 'flex';
      authView('login');
    }
  } catch (e) {}
}, 60e3);

async function logout() {
  try { await API.post('/api/auth/logout', {}); } catch (e) {}
  APP.user = null;
  location.reload();
}
