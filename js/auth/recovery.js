/* Recuperación de contraseña (pantallas públicas, sin sesión):
   1) por correo: código de 6 dígitos enviado al correo verificado
   2) con código de recuperación de un solo uso
   Si la cuenta tiene 2FA, también se exige el código del autenticador.
   Las respuestas no revelan si un usuario o correo existe. */
let pendReset = null;
const findByIdentifier = id => DB.users.find(u => u.user === id || (u.emailOk && u.email === id));

async function applyNewPassword(x, p, via) {
  x.salt = rnd(16); x.hash = await hashPw(p, x.salt); x.fails = 0; x.lock = 0;
  log('Contraseña restablecida ' + via, x.user); save();
}

async function doForgot() {
  const id = v('a-id').toLowerCase();
  if (!id) return err('Escribe tu usuario o tu correo');
  const x = findByIdentifier(id);
  if (x && x.active && x.emailOk && x.recEmail !== false) {
    if (!otcCooling(DB.resets[x.id])) {
      const { code, rec } = await otcIssue();
      DB.resets[x.id] = rec;
      try { await sendMail(mailReset(x, code)); log('Código de recuperación enviado', x.user); }
      catch (e) { log('Fallo al enviar código de recuperación: ' + e.message, x.user); }
      save();
    }
  } else await hashPw(id, rnd(16));
  pendReset = id;
  authView('reset', 'Si la cuenta existe y tiene un correo verificado, enviamos un código. Vence en 10 minutos.', true);
}

async function doReset() {
  const x = pendReset && findByIdentifier(pendReset);
  const code = v('a-code').replace(/\s/g, ''), p = $('a-pass').value, tf = v('a-2fa').replace(/\s/g, '');
  const BAD = 'Código inválido o vencido. Si hace falta, pide uno nuevo.';
  if (!x || !x.active) { await hashPw(code, rnd(16)); return err(BAD); }
  const st = await otcCheck(DB.resets[x.id], code);
  save();
  if (st !== 'ok') return err(BAD);
  if (!pwOk(p)) return err(POLICY_MSG);
  if (p !== $('a-pass2').value) return err('Las contraseñas no coinciden');
  if (!await verifySecondFactor(x, tf)) { save(); return err('Verificación en dos pasos incorrecta'); }
  await applyNewPassword(x, p, 'por correo');
  delete DB.resets[x.id]; save(); pendReset = null;
  authView('login', 'Contraseña actualizada. Ya puedes iniciar sesión.', true);
}

async function doRecov() {
  const u = v('a-user').toLowerCase(), c = normCode(v('a-code')), p = $('a-pass').value, tf = v('a-2fa').replace(/\s/g, '');
  const x = DB.users.find(z => z.user === u);
  if (!x || !x.active) { await hashPw(p, rnd(16)); return err('Datos inválidos'); }
  if (x.lock > Date.now()) return err('Cuenta bloqueada. Intenta en ' + Math.ceil((x.lock - Date.now()) / 6e4) + ' min.');
  const i = x.rec.indexOf(await sha(c));
  if (i < 0) { registerFail(x, 'Bloqueo por códigos de recuperación fallidos'); return err('Datos inválidos'); }
  if (!pwOk(p)) return err(POLICY_MSG);
  if (p !== $('a-pass2').value) return err('Las contraseñas no coinciden');
  if (!await verifySecondFactor(x, tf)) { registerFail(x, 'Bloqueo por 2FA fallido en recuperación'); return err('Verificación en dos pasos incorrecta'); }
  x.rec.splice(i, 1);
  await applyNewPassword(x, p, 'con código de recuperación');
  authView('login', 'Contraseña actualizada. Ya puedes iniciar sesión.', true);
}
