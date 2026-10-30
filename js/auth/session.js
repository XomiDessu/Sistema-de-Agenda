/* Sesión (cierre por inactividad configurable por usuario) y permisos */
let sess = JSON.parse(sessionStorage.getItem('sess') || 'null'), pend = null, tmp = null;
const idleMs = () => ((DB.users.find(u => u.id === sess?.uid)?.timeout) || 15) * 6e4;
function me() { if (!sess || sess.exp < Date.now()) return null; return DB.users.find(u => u.id === sess.uid && u.active) || null; }
const isAdmin = () => me()?.role === 'admin';
const ag = id => DB.agendas.find(a => a.id === id && me() && (a.owner === me().id || isAdmin()));
const bump = () => { if (sess && sess.exp > Date.now()) { sess.exp = Date.now() + idleMs(); sessionStorage.setItem('sess', JSON.stringify(sess)); } };
['click', 'keydown'].forEach(e => document.addEventListener(e, bump));
setInterval(() => { if (sess && !me()) { alert('Sesión expirada por inactividad.'); logout(true); } }, 3e4);
function logout(auto) {
  log(auto ? 'Sesión expirada' : 'Cierre de sesión', DB.users.find(u => u.id === sess?.uid)?.user);
  sessionStorage.removeItem('sess'); location.reload();
}
