/* Envío de correo.
   - modo "demo": guarda el mensaje en una bandeja local (solo para pruebas; no sale nada a Internet).
   - modo "emailjs": envía por la API de EmailJS (https://www.emailjs.com) desde el navegador. */
const APP_NAME = 'Agenda de Citas';
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

const mailConfigured = () => {
  const c = DB.mail;
  return c.mode === 'demo' || !!(c.serviceId && c.templateId && c.publicKey);
};

async function sendMail({ to, name, subject, text, code }) {
  const c = DB.mail;
  if (c.mode === 'emailjs') {
    if (!mailConfigured()) throw new Error('El servicio de correo no está configurado.');
    let r;
    try {
      r = await fetch('https://api.emailjs.com/api/v1.0/email/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          service_id: c.serviceId, template_id: c.templateId, user_id: c.publicKey,
          template_params: { to_email: to, to_name: name || to, subject, message: text, code: code || '', app_name: c.fromName || APP_NAME }
        })
      });
    } catch (e) { throw new Error('No se pudo conectar con el servicio de correo.'); }
    if (!r.ok) throw new Error('El servicio de correo rechazó el envío (' + r.status + ').');
    return 'sent';
  }
  DB.outbox.unshift({ t: new Date().toLocaleString(), to, subject, text });
  DB.outbox.length = Math.min(DB.outbox.length, 10);
  save();
  return 'demo';
}

/* Plantillas */
const mailVerify = (u, addr, code) => ({
  to: addr, name: u.name, code,
  subject: 'Verifica tu correo · ' + APP_NAME,
  text: `Hola ${u.name}, tu código para verificar este correo es ${code}. Vence en 10 minutos. Si no lo solicitaste, ignora este mensaje.`
});
const mailReset = (u, code) => ({
  to: u.email, name: u.name, code,
  subject: 'Recuperación de contraseña · ' + APP_NAME,
  text: `Hola ${u.name}, tu código para restablecer la contraseña de "${u.user}" es ${code}. Vence en 10 minutos. Si no lo solicitaste, ignora este mensaje: tu contraseña no cambiará.`
});

/* Bandeja del modo demostración */
function outboxHtml() {
  if (!DB.outbox.length) return '<p class="hint">La bandeja está vacía.</p>';
  return DB.outbox.map(m => `<div class="mail-item"><div class="mail-meta">${esc(m.t)} · Para: <b>${esc(m.to)}</b></div><div class="mail-subj">${esc(m.subject)}</div><div>${esc(m.text)}</div></div>`).join('');
}
