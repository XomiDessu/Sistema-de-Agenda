/* Códigos de un solo uso (6 dígitos) para verificar correo y recuperar contraseña.
   Solo se guarda un hash con sal; el código en claro viaja únicamente en el correo. */
const OTC_TTL = 10 * 60e3;   // vigencia: 10 min
const OTC_MAX_TRIES = 5;     // intentos antes de invalidarlo
const OTC_COOLDOWN = 60e3;   // espera entre reenvíos

async function otcIssue() {
  const code = numCode(), salt = rnd(16);
  return { code, rec: { salt, hash: await hashPw(code, salt), exp: Date.now() + OTC_TTL, tries: 0, sent: Date.now() } };
}
const otcCooling = rec => !!rec && Date.now() - rec.sent < OTC_COOLDOWN;
const otcWait    = rec => Math.ceil((OTC_COOLDOWN - (Date.now() - rec.sent)) / 1000);

/* Devuelve 'ok' | 'bad' | 'expired' | 'locked' */
async function otcCheck(rec, code) {
  if (!rec || rec.exp < Date.now()) return 'expired';
  if (rec.tries >= OTC_MAX_TRIES)   return 'locked';
  if (eq(await hashPw(String(code), rec.salt), rec.hash)) return 'ok';
  rec.tries++;
  return 'bad';
}
