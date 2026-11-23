/* Cliente HTTP contra el backend REST (sesiones por cookie HttpOnly + cabecera CSRF) */
const API = {
  async req(method, url, body) {
    const opts = {
      method,
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    };
    if (body !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(url, opts);
    const data = await res.json().catch(() => ({}));
    if (res.status === 401 && url !== '/api/auth/login' && url !== '/api/auth/mfa' && url !== '/api/auth/status') {
      APP.user = null;
      $('auth').style.display = 'flex';
      authView('login', data.error || 'Tu sesión ha expirado.');
      throw new Error(data.error || 'Sesión expirada');
    }
    if (!res.ok) {
      const e = new Error(data.error || 'Error de servidor (' + res.status + ')');
      e.status = res.status;
      e.data = data;
      throw e;
    }
    return data;
  },
  get:  url => API.req('GET', url),
  post: (url, body) => API.req('POST', url, body),
  put:  (url, body) => API.req('PUT', url, body),
  del:  (url, body) => API.req('DELETE', url, body)
};
