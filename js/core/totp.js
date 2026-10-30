/* TOTP (RFC 6238) para la verificación en dos pasos */
const B32='ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
const b32e=u=>{let b='',o='';u.forEach(x=>b+=x.toString(2).padStart(8,'0'));for(let i=0;i<b.length;i+=5)o+=B32[parseInt(b.slice(i,i+5).padEnd(5,'0'),2)];return o};
const b32d=s=>{let b='';[...s].forEach(c=>b+=B32.indexOf(c).toString(2).padStart(5,'0'));const o=[];for(let i=0;i+8<=b.length;i+=8)o.push(parseInt(b.slice(i,i+8),2));return new Uint8Array(o)};
async function totp(sec,step){const k=await crypto.subtle.importKey('raw',b32d(sec),{name:'HMAC',hash:'SHA-1'},false,['sign']);const c=new Uint8Array(8);new DataView(c.buffer).setUint32(4,step);const h=new Uint8Array(await crypto.subtle.sign('HMAC',k,c));const o=h[19]&15;return String(((h[o]&127)<<24|h[o+1]<<16|h[o+2]<<8|h[o+3])%1e6).padStart(6,'0')}
async function checkTotp(sec,code){const t=Math.floor(Date.now()/3e4);for(const d of [-1,0,1])if(await totp(sec,t+d)===code)return true;return false}
