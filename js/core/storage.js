/* Base de datos local (localStorage) y bitácora */
const KEY = 'agenda_db_v1';
let DB = JSON.parse(localStorage.getItem(KEY) || 'null') || { users: [], agendas: [], log: [] };

/* Completa campos nuevos en datos guardados por versiones anteriores */
function migrateDB() {
  DB.users   ||= [];
  DB.agendas ||= [];
  DB.log     ||= [];
  DB.outbox  ||= [];   // bandeja del modo demostración
  DB.resets  ||= {};   // códigos de recuperación pendientes (por id de usuario)
  DB.mail    ||= { mode: 'demo', fromName: 'Agenda de Citas', serviceId: '', templateId: '', publicKey: '' };
  DB.users.forEach(u => {
    u.email    ??= '';     // correo en minúsculas
    u.emailOk  ??= false;  // true cuando el usuario verificó el código
    u.pend     ??= null;   // verificación de correo en curso
    u.recEmail ??= true;   // permitir recuperar contraseña por correo
    u.rec      ??= [];     // hashes de códigos de recuperación de un solo uso
    u.timeout  ??= 15;     // minutos de inactividad antes de cerrar sesión
  });
}
migrateDB();

const save = () => localStorage.setItem(KEY, JSON.stringify(DB));
function log(e, u) {
  DB.log.unshift({ t: new Date().toLocaleString(), u: u || me()?.user || '-', e });
  DB.log.length = Math.min(DB.log.length, 100);
  save();
}
