/* Vista "Mi cuenta": estructura de pestañas.
   Para añadir una pestaña: nueva entrada en AC_TABS + una función que devuelva su HTML. */
let acTab = 'perfil', acFlash = null;

const AC_TABS = {
  perfil:       { label: 'Perfil',             icon: 'ti-user',        html: m => tabPerfil(m) },
  correo:       { label: 'Correo',             icon: 'ti-mail',        html: m => tabCorreo(m) },
  recuperacion: { label: 'Recuperación',       icon: 'ti-lifebuoy',    html: m => tabRecuperacion(m) },
  seguridad:    { label: 'Seguridad',          icon: 'ti-shield-lock', html: m => tabSeguridad(m) },
  servicio:     { label: 'Servicio de correo', icon: 'ti-send',        html: m => tabServicio(m), admin: true }
};

function renderAccount() {
  const m = me(); if (!m) return;
  if (AC_TABS[acTab].admin && !isAdmin()) acTab = 'perfil';
  const tabs = Object.entries(AC_TABS).filter(([, t]) => !t.admin || isAdmin())
    .map(([k, t]) => `<button class="tab${k === acTab ? ' active' : ''}" role="tab" aria-selected="${k === acTab}" onclick="acGo('${k}')"><i class="ti ${t.icon}"></i> ${t.label}</button>`).join('');
  $('view-account').innerHTML = `<div class="topbar"><span class="topbar-title">Mi cuenta</span></div>
    <div class="tabs" role="tablist">${tabs}</div>
    <div class="settings-body"><div class="ac-wrap"><div class="err" id="ac-msg" role="alert"></div>${AC_TABS[acTab].html(m)}</div></div>`;
  if (acFlash) { acMsg(acFlash.text, acFlash.good); acFlash = null; }
}

/* Utilidades compartidas por las pestañas */
const pill = (kind, t) => `<span class="pill pill-${kind}">${t}</span>`;
function acGo(t) { acTab = t; msDraft = null; renderAccount(); }
function acMsg(text, good) { const e = $('ac-msg'); if (e) { e.className = good ? 'msg-ok' : 'err'; e.textContent = text; } }
function acFlashMsg(text, good) { acFlash = { text, good }; renderAccount(); }
function acUser() { const m = me(); if (!m) logout(true); return m; }
async function acPwOk(m, inputId) { return eq(await hashPw($(inputId).value, m.salt), m.hash); }
