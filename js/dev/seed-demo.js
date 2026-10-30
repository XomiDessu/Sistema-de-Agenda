/* Datos de demostración (no se carga en index.html; úsalo desde la consola si lo necesitas) */
function seedAppointments() {
  const clients = ['Ana García','Luis Martínez','Sofía Herrera','Carlos López','Valentina Ruiz','Miguel Torres','Camila Pérez','Jorge Ramos','Daniela Cruz','Fernando Soto'];
  const statuses = ['confirmed','confirmed','confirmed','pending','pending'];
  let id = 1;
  for (let i = -3; i < 25; i++) {
    const d = new Date(S.today); d.setDate(S.today.getDate()+i);
    if (!S.workDays.includes(d.getDay())) continue;
    const n = Math.floor(Math.random()*3)+1;
    const hours = ['09:00','10:00','11:00','12:00','15:00','16:00'];
    const used = [];
    for (let s=0; s<n; s++) {
      const h = hours[Math.floor(Math.random()*hours.length)];
      if (used.includes(h)) continue;
      used.push(h);
      S.appointments.push({
        id: id++,
        client:  clients[Math.floor(Math.random()*clients.length)],
        phone:   '',
        date:    fmtKey(d),
        time:    h,
        service: S.services[Math.floor(Math.random()*S.services.length)].name,
        status:  statuses[Math.floor(Math.random()*statuses.length)],
        notes:   ''
      });
    }
  }
}
