/* Registro, inicio de sesión y 2FA contra el backend */
let pendMfaToken = null;

async function doReg() {
  const user = v('a-user').toLowerCase(), name = v('a-name'), email = v('a-mail').toLowerCase();
  const password = $('a-pass').value, p2 = $('a-pass2').value;
  const setupToken = $('a-setup') ? v('a-setup') : '';
  if (!pwOk(password)) return err(POLICY_MSG);
  if (password !== p2) return err('Las contraseñas no coinciden');
  try {
    const res = await API.post('/api/auth/register', { user, name, email, password, setupToken });
    APP.needsSetup = false;
    await startSession(res.user);
  } catch (e) {
    err(e.message);
  }
}

async function doLogin() {
  const user = v('a-user').toLowerCase(), password = $('a-pass').value;
  try {
    const res = await API.post('/api/auth/login', { user, password });
    if (res.mfaRequired) {
      pendMfaToken = res.mfaToken;
      return authView('mfa');
    }
    await startSession(res.user);
  } catch (e) {
    err(e.message);
  }
}

async function doMfa() {
  try {
    const res = await API.post('/api/auth/mfa', { mfaToken: pendMfaToken, code: v('a-code') });
    pendMfaToken = null;
    await startSession(res.user);
  } catch (e) {
    if (e.data?.locked) {
      pendMfaToken = null;
      return authView('login', e.message);
    }
    err(e.message);
  }
}

async function startSession(u) {
  APP.user = u;
  $('auth').style.display = 'none';
  $('u-name').textContent = u.name;
  $('u-role').textContent = u.role === 'admin' ? 'Administrador' : 'Usuario';
  document.querySelectorAll('.adm').forEach(e => e.style.display = u.role === 'admin' ? '' : 'none');
  await refreshAgendasList();
  if (APP.agendas.length) await loadAgenda(APP.agendas[0].id);
}
