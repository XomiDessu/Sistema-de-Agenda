/* Menú móvil responsivo */
function toggleMobileSidebar(force) {
  const sb = $('sidebar'), bd = $('sidebar-backdrop');
  if (!sb || !bd) return;
  const open = typeof force === 'boolean' ? force : !sb.classList.contains('open');
  sb.classList.toggle('open', open);
  bd.classList.toggle('open', open);
}
