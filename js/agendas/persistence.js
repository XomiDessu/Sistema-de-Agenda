/* Guarda automáticamente la agenda abierta tras cada acción que la modifica.
   Debe cargarse DESPUÉS de los módulos de citas, horarios y servicios. */
['saveApt', 'deleteApt', 'saveSettings', 'saveService', 'deleteService', 'addBreak', 'deleteBreak', 'setDur', 'toggleDay'].forEach(n => {
  const f = window[n];
  window[n] = function () { if (!me()) { logout(true); return; } const r = f.apply(this, arguments); persist(); return r; };
});
