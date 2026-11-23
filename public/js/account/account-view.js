/* Vista "Mi cuenta" */
let acTab = 'perfil', acFlash = null;

const AC_TABS = {
  perfil:       { label: 'Perfil',             icon: 'ti-user',        html: m => tabPerfil(m) },
  correo:       { label: 'Correo',             icon: 'ti-mail',        html: m => tabCorreo(m) },
  recuperacion: { label: 'Recuperación',       icon: 'ti-lifebuoy',    html: m => tabRecuperacion(m) },
  seguridad:    { label: 'Seguridad',          icon: 'ti-shield-lock', html: m => tabSeguridad(m) },
  servicio:     { label: 'Servicio de correo', icon: 'ti-send',        html: m => tabServicio(m), admin: true }
};

async function refreshMe() {
  const st = await API.get('/api/auth/status');
  APP.user = st.user;
  APP.mailMode = st.mailMode;
  return st.user;
}

async function renderAccount() {
  const m = await refreshMe();
  if (!m) return;
  if (AC_TABS[acTab].admin && !isAdmin()) acTab = 'perfil';
  if (acTab === 'servicio') await loadMailConfig();
  const tabs = Object.entries(AC_TABS).filter(([, t]) => !t.admin || isAdmin())
    .map(([k, t]) => `<button class="tab${k === acTab ? ' active' : ''}" role="tab" aria-selected="${k === acTab}" onclick="acGo('${k}')"><i class="ti ${t.icon}"></i> ${t.label}</button>`).join('');
  $('view-account').innerHTML = `<div class="topbar"><button class="mobile-menu-btn" onclick="toggleMobileSidebar()" aria-label="Menú"><i class="ti ti-menu-2"></i></button><span class="topbar-title">Mi cuenta</span></div>
    <div class="tabs" role="tablist">${tabs}</div>
    <div class="settings-body"><div class="ac-wrap"><div class="err" id="ac-msg" role="alert"></div>${AC_TABS[acTab].html(m)}</div></div>`;
  if (acFlash) { acMsg(acFlash.text, acFlash.good); acFlash = null; }
}

const pill = (kind, t) => `<span class="pill pill-${kind}">${t}</span>`;
function acGo(t) { acTab = t; msDraft = null; renderAccount(); }
function acMsg(text, good) { const e = $('ac-msg'); if (e) { e.className = good ? 'msg-ok' : 'err'; e.textContent = text; } }
function acFlashMsg(text, good) { acFlash = { text, good }; renderAccount(); }
