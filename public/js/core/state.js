/* Estado global de la sesión y la agenda abierta */
let APP = {
  user: null,
  needsSetup: false,
  mailMode: 'demo',
  appName: 'Agenda de Citas',
  agendas: []
};

let S = {
  agendaId: null,
  slug: '',
  publicBooking: true,
  autoConfirmPublic: false,
  view: 'cal',
  today: new Date(),
  calDate: new Date(),
  miniDate: new Date(),
  selectedDay: null,
  workDays: [1, 2, 3, 4, 5],
  hourStart: '09:00',
  hourEnd: '18:00',
  slotDur: 60,
  breaks: [{ start: '13:00', end: '14:00', label: 'Comida' }],
  phone: '',
  address: '',
  appointments: [],
  services: [],
  clients: [],
  modalStatus: 'confirmed',
  editingAptId: null
};
