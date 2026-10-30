/* Estado global de la agenda abierta (S) */
let S = {
  view:        'cal',
  today:       new Date(),
  calDate:     new Date(),
  miniDate:    new Date(),
  selectedDay: null,
  workDays:    [1, 2, 3, 4, 5],       // 0=Dom … 6=Sáb
  hourStart:   '09:00',
  hourEnd:     '18:00',
  slotDur:     60,                     // minutos
  breaks:      [{ start:'13:00', end:'14:00', label:'Comida' }],
  appointments: [],
  services: [
    { id:1, name:'Consulta general', dur:60,  price:'$500' },
    { id:2, name:'Seguimiento',      dur:30,  price:'$300' },
    { id:3, name:'Procedimiento',    dur:90,  price:'$800' }
  ],
  modalStatus:  'confirmed',
  editingAptId: null
};
