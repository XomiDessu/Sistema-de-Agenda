/* Utilidades generales */
const fmtKey  = d => d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate());
const parseKey = k => { const [y,m,d]=k.split('-'); return new Date(+y,+m-1,+d); };
const sameDay  = (a,b) => a.getFullYear()===b.getFullYear() && a.getMonth()===b.getMonth() && a.getDate()===b.getDate();
const pad      = n => String(n).padStart(2,'0');
const $ = id => document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const v=id=>$(id).value.trim();
