/* Registro, inicio de sesión y verificación en dos pasos */
function registerFail(x, why) {   // devuelve true si la cuenta quedó bloqueada
  x.fails = (x.fails || 0) + 1;
  if (x.fails >= 5) { x.fails = 0; x.lock = Date.now() + 3e5; log(why, x.user); save(); return true; }
  save(); return false;
}
async function verifySecondFactor(x, c) {   // true si no hay 2FA o el código es válido
  if (!x.totp?.on) return true;
  let ok = await checkTotp(x.totp.secret, c);
  if (!ok) { const i = x.backup.indexOf(await sha(c.toLowerCase())); if (i > -1) { x.backup.splice(i, 1); ok = true; log('Uso de código de respaldo', x.user); } }
  return ok;
}

async function doReg() {
  const u = v('a-user').toLowerCase(), n = v('a-name'), e = v('a-mail').toLowerCase(), p = $('a-pass').value;
  if (!/^[a-z0-9_.-]{3,20}$/.test(u)) return err('Usuario: 3-20 caracteres (a-z, 0-9, . _ -)');
  if (!n || n.length > 40) return err('Nombre requerido (máx. 40 caracteres)');
  if (e && (!EMAIL_RE.test(e) || e.length > 80)) return err('Correo no válido');
  if (!pwOk(p)) return err(POLICY_MSG);
  if (p !== $('a-pass2').value) return err('Las contraseñas no coinciden');
  if (DB.users.some(x => x.user === u)) return err('Usuario no disponible');
  const salt = rnd(16), x = { id: rnd(8), user: u, name: n, role: DB.users.length ? 'usuario' : 'admin', salt, hash: await hashPw(p, salt), active: true, fails: 0, lock: 0, totp: null, backup: [], email: e, emailOk: false, pend: null, recEmail: true, rec: [], timeout: 15 };
  DB.users.push(x); log('Alta de usuario ' + u + ' (' + x.role + ')', u); start(x);
}
async function doLogin() {
  const u = v('a-user').toLowerCase(), p = $('a-pass').value, x = DB.users.find(z => z.user === u);
  if (!x || !x.active) { await hashPw(p, rnd(16)); return err('Credenciales inválidas'); }
  if (x.lock > Date.now()) return err('Cuenta bloqueada. Intenta en ' + Math.ceil((x.lock - Date.now()) / 6e4) + ' min.');
  if (!eq(await hashPw(p, x.salt), x.hash)) { registerFail(x, 'Bloqueo por intentos fallidos'); return err('Credenciales inválidas'); }
  if (x.totp?.on) { pend = x.id; return authView('mfa'); }
  start(x);
}
async function doMfa() {
  const x = DB.users.find(u => u.id === pend); if (!x) return authView('login');
  if (!await verifySecondFactor(x, v('a-code').replace(/\s/g, ''))) {
    if (registerFail(x, 'Bloqueo por 2FA fallido')) { pend = null; return authView('login', 'Cuenta bloqueada 5 min.'); }
    return err('Código incorrecto');
  }
  x.fails = 0; pend = null; start(x);
}
function start(x, resume) {
  if (!resume) { x.fails = 0; sess = { uid: x.id, exp: Date.now() + 9e5 }; bump(); log('Inicio de sesión', x.user); }
  save(); $('auth').style.display = 'none';
  $('u-name').textContent = x.name; $('u-role').textContent = x.role === 'admin' ? 'Administrador' : 'Usuario';
  document.querySelectorAll('.adm').forEach(e => e.style.display = x.role === 'admin' ? '' : 'none');
  const mine = DB.agendas.filter(a => a.owner === x.id);
  loadAgenda((mine[0] || newAgenda('Mi negocio')).id);
}
