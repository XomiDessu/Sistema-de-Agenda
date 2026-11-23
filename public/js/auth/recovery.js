/* Recuperación de contraseña (por correo OTC o código de recuperación) */
let pendResetIdent = null;

async function doForgot() {
  const identifier = v('a-id').toLowerCase();
  if (!identifier) return err('Escribe tu usuario o tu correo');
  try {
    const res = await API.post('/api/auth/forgot', { identifier });
    pendResetIdent = identifier;
    authView('reset', res.message, true);
  } catch (e) {
    err(e.message);
  }
}

async function doReset() {
  const code = v('a-code'), password = $('a-pass').value, p2 = $('a-pass2').value, twoFactor = v('a-2fa');
  if (!pwOk(password)) return err(POLICY_MSG);
  if (password !== p2) return err('Las contraseñas no coinciden');
  try {
    const res = await API.post('/api/auth/reset', { identifier: pendResetIdent, code, password, twoFactor });
    pendResetIdent = null;
    authView('login', res.message, true);
  } catch (e) {
    err(e.message);
  }
}

async function doRecov() {
  const user = v('a-user').toLowerCase(), code = v('a-code'), password = $('a-pass').value, p2 = $('a-pass2').value, twoFactor = v('a-2fa');
  if (!pwOk(password)) return err(POLICY_MSG);
  if (password !== p2) return err('Las contraseñas no coinciden');
  try {
    const res = await API.post('/api/auth/recover', { user, code, password, twoFactor });
    authView('login', res.message, true);
  } catch (e) {
    err(e.message);
  }
}
