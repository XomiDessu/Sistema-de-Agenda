/* Navegación entre vistas */
const VIEWS = {
  cal:      () => { renderCal(); renderMiniCal(); renderDayPanel(); },
  agenda:   () => renderAgenda(),
  clients:  () => renderClients(),
  reports:  () => renderReports(),
  settings: () => renderSettings(),
  services: () => renderServices(),
  account:  () => renderAccount()
};

function switchView(name) {
  Object.keys(VIEWS).forEach(x => {
    $('view-' + x)?.classList.remove('active');
    $('nav-' + x)?.classList.remove('active');
  });
  $('view-' + name)?.classList.add('active');
  $('nav-' + name)?.classList.add('active');
  $('day-panel').style.display = name === 'cal' ? 'flex' : 'none';
  S.view = name;
  toggleMobileSidebar(false);
  VIEWS[name]();
}
