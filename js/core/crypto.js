/* Hash de contraseñas (PBKDF2) y utilidades criptográficas */
const enc = new TextEncoder();
const b2h=b=>[...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,'0')).join('');
const h2b=h=>new Uint8Array(h.match(/../g).map(x=>parseInt(x,16)));
const rnd=n=>b2h(crypto.getRandomValues(new Uint8Array(n)));
const sha=async s=>b2h(await crypto.subtle.digest('SHA-256',enc.encode(s)));
async function hashPw(p,salt){const k=await crypto.subtle.importKey('raw',enc.encode(p),'PBKDF2',false,['deriveBits']);return b2h(await crypto.subtle.deriveBits({name:'PBKDF2',hash:'SHA-256',salt:h2b(salt),iterations:150000},k,256))}
const eq=(a,b)=>{if(a.length!==b.length)return false;let r=0;for(let i=0;i<a.length;i++)r|=a.charCodeAt(i)^b.charCodeAt(i);return r===0};
const normCode=s=>String(s).toLowerCase().replace(/[^a-z0-9]/g,'');
const numCode=()=>String(crypto.getRandomValues(new Uint32Array(1))[0]%1e6).padStart(6,'0');
