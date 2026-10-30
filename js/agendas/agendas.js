/* Agendas: crear, cargar y guardar (cada una con sus horarios, servicios y citas) */
function newAgenda(name){
  const a={id:rnd(6),owner:me().id,name:name.slice(0,40),data:{workDays:[1,2,3,4,5],hourStart:'09:00',hourEnd:'18:00',slotDur:60,breaks:[{start:'13:00',end:'14:00',label:'Comida'}],appointments:[],services:[{id:1,name:'Servicio general',dur:60,price:'$0'}],phone:'',address:''}};
  DB.agendas.push(a);log('Agenda creada: '+a.name);return a;
}
function loadAgenda(id){
  const a=ag(id);if(!a)return;
  S.agendaId=id;Object.assign(S,JSON.parse(JSON.stringify(a.data)));
  S.today=new Date();S.calDate=new Date();S.miniDate=new Date();S.selectedDay=fmtKey(S.today);
  $('biz-name').textContent=a.name;$('biz-phone').value=a.data.phone||'';$('biz-address').value=a.data.address||'';
  renderSel(id);switchView('cal');
}
function renderSel(id){const m=me();$('ag-sel').innerHTML=DB.agendas.filter(a=>a.owner===m.id||(isAdmin()&&a.id===id)).map(a=>`<option value="${a.id}"${a.id===id?' selected':''}>${esc(a.name)}</option>`).join('')}
function persist(){
  const a=ag(S.agendaId);if(!a)return;
  a.name=$('biz-name').textContent.slice(0,40);
  a.data={workDays:S.workDays,hourStart:S.hourStart,hourEnd:S.hourEnd,slotDur:S.slotDur,breaks:S.breaks,appointments:S.appointments,services:S.services,phone:$('biz-phone').value.trim(),address:$('biz-address').value.trim()};
  save();renderSel(a.id);
}
