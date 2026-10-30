/* Navegación entre vistas. Para añadir una vista: un <div id="view-X" class="view">,
   un botón con id="nav-X" y una entrada aquí. */
const VIEWS = {
  cal:      () => { renderCal(); renderMiniCal(); renderDayPanel(); },
  agenda:   () => renderAgenda(),
  settings: () => renderSettings(),
  services: () => renderServices(),
  account:  () => renderAccount()
};

function switchView(v) {
  Object.keys(VIEWS).forEach(x => {
    $('view-' + x).classList.remove('active');
    $('nav-' + x).classList.remove('active');
  });
  $('view-' + v).classList.add('active');
  $('nav-' + v).classList.add('active');
  $('day-panel').style.display = v === 'cal' ? 'flex' : 'none';
  S.view = v;
  VIEWS[v]();
}
