"""Servidor HTTP y API REST completa para Agenda de Citas MVP."""
import json
import mimetypes
import re
import time
from datetime import datetime, timedelta
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from .db import Database, now_str, parse_price, slugify
from .export_utils import build_report, export_csv, export_ics
from .mail import MailService
from .scheduling import get_available_slots, validate_appointment
from .security import (
    EMAIL_RE,
    LOGIN_LOCK_SEC,
    LOGIN_MAX_FAILS,
    OTC_COOLDOWN_SEC,
    OTC_MAX_TRIES,
    OTC_TTL_SEC,
    POLICY_MSG,
    RateLimiter,
    USER_RE,
    check_totp,
    generate_backup_codes,
    generate_recovery_codes,
    generate_totp_secret,
    hash_password,
    norm_code,
    numeric_code,
    pw_ok,
    random_hex,
    sha256_hex,
    verify_password,
)


def serialize_user(row) -> dict:
    rec_codes = json.loads(row['rec_codes'] or '[]')
    return {
        'id': row['id'],
        'user': row['user'],
        'name': row['name'],
        'role': row['role'],
        'active': bool(row['active']),
        'totpOn': bool(row['totp_on']),
        'email': row['email'] or '',
        'emailOk': bool(row['email_ok']),
        'recEmail': bool(row['rec_email']),
        'recCount': len(rec_codes),
        'timeout': int(row['timeout_min'] or 15),
    }


def serialize_agenda_summary(row, owner_user: str = '') -> dict:
    return {
        'id': row['id'],
        'ownerId': row['owner_id'],
        'ownerUser': owner_user,
        'name': row['name'],
        'slug': row['slug'],
        'publicBooking': bool(row['public_booking']),
        'autoConfirmPublic': bool(row['auto_confirm_public']),
    }


class AppContext:
    def __init__(self, config: dict):
        self.config = config
        self.db = Database(config['DB_PATH'], config)
        self.mail = MailService(self.db, config.get('APP_NAME', 'Agenda de Citas'))
        self.limiter = RateLimiter()
        self.public_dir = Path(config['PUBLIC_DIR']).resolve()


def make_handler(ctx: AppContext):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, fmt, *args):
            if ctx.config.get('QUIET_LOGS'):
                return
            super().log_message(fmt, *args)

        def _client_ip(self) -> str:
            fwd = self.headers.get('X-Forwarded-For', '').split(',')[0].strip()
            return fwd or self.client_address[0]

        def _send_security_headers(self):
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')

        def _send_json(self, data: dict | list, status: int = 200, extra_headers: list[tuple[str, str]] | None = None):
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self._send_security_headers()
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            for k, v in (extra_headers or []):
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _send_bytes(self, content: bytes, content_type: str, status: int = 200, extra_headers: list[tuple[str, str]] | None = None):
            self.send_response(status)
            self._send_security_headers()
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            for k, v in (extra_headers or []):
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(content)

        def _read_json(self) -> dict:
            length = int(self.headers.get('Content-Length', '0') or '0')
            if length <= 0:
                return {}
            if length > 1_000_000:
                raise ValueError('Cuerpo demasiado grande')
            raw = self.rfile.read(length)
            return json.loads(raw.decode('utf-8')) if raw else {}

        def _cookie_header(self, token: str, max_age: int) -> tuple[str, str]:
            parts = [f'agenda_sess={token}', 'Path=/', 'HttpOnly', 'SameSite=Lax', f'Max-Age={max_age}']
            if ctx.config.get('COOKIE_SECURE'):
                parts.append('Secure')
            return ('Set-Cookie', '; '.join(parts))

        def _get_session_token(self) -> str | None:
            raw = self.headers.get('Cookie', '')
            if not raw:
                return None
            c = cookies.SimpleCookie()
            c.load(raw)
            m = c.get('agenda_sess')
            return m.value if m else None

        def _current_user(self, touch: bool = True):
            tok = self._get_session_token()
            if not tok:
                return None
            now = time.time()
            with ctx.db.connect() as conn:
                row = conn.execute(
                    """SELECT s.token, s.expires_at, u.*
                       FROM sessions s JOIN users u ON u.id = s.user_id
                       WHERE s.token = ?""",
                    (tok,),
                ).fetchone()
                if not row:
                    return None
                if row['expires_at'] < now or not row['active']:
                    conn.execute('DELETE FROM sessions WHERE token = ?', (tok,))
                    return None
                if touch:
                    new_exp = now + int(row['timeout_min'] or 15) * 60
                    conn.execute('UPDATE sessions SET expires_at = ? WHERE token = ?', (new_exp, tok))
                return row

        def _create_session(self, conn, user_row) -> tuple[str, int]:
            tok = random_hex(24)
            now = time.time()
            ttl = int(user_row['timeout_min'] or 15) * 60
            conn.execute(
                'INSERT INTO sessions (token, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)',
                (tok, user_row['id'], now + ttl, now),
            )
            return tok, ttl

        def _require_csrf(self) -> bool:
            if self.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return True
            ct = self.headers.get('Content-Type', '')
            if 'application/json' in ct:
                return True
            self._send_json({'error': 'Solicitud rechazada por verificación CSRF.'}, 403)
            return False

        def _get_authorized_agenda(self, conn, agenda_id: str, user_row):
            row = conn.execute('SELECT * FROM agendas WHERE id = ?', (agenda_id,)).fetchone()
            if not row:
                return None
            if row['owner_id'] != user_row['id'] and user_row['role'] != 'admin':
                return None
            return row

        def _verify_second_factor(self, conn, user_row, code: str) -> bool:
            if not user_row['totp_on']:
                return True
            clean = re.sub(r'\s+', '', str(code or ''))
            if check_totp(user_row['totp_secret'], clean):
                return True
            backups = json.loads(user_row['backup_codes'] or '[]')
            h = sha256_hex(clean.lower())
            if h in backups:
                backups.remove(h)
                conn.execute('UPDATE users SET backup_codes = ? WHERE id = ?', (json.dumps(backups), user_row['id']))
                ctx.db.add_log('Uso de código de respaldo 2FA', user_row['user'], conn)
                return True
            return False

        def _register_fail(self, conn, user_row, reason: str) -> bool:
            fails = int(user_row['fails'] or 0) + 1
            if fails >= LOGIN_MAX_FAILS:
                conn.execute(
                    'UPDATE users SET fails = 0, lock_until = ? WHERE id = ?',
                    (time.time() + LOGIN_LOCK_SEC, user_row['id']),
                )
                ctx.db.add_log(reason, user_row['user'], conn)
                return True
            conn.execute('UPDATE users SET fails = ? WHERE id = ?', (fails, user_row['id']))
            return False

        def _serve_static(self, rel_path: str):
            clean = rel_path.lstrip('/')
            if not clean or clean == 'index.html':
                target = ctx.public_dir / 'index.html'
            elif clean.startswith('reservar/') or clean == 'reservar':
                target = ctx.public_dir / 'reservar.html'
            else:
                target = (ctx.public_dir / clean).resolve()
                if not str(target).startswith(str(ctx.public_dir)) or not target.is_file():
                    self._send_bytes(b'Not Found', 'text/plain; charset=utf-8', 404)
                    return
            ctype, _ = mimetypes.guess_type(str(target))
            ctype = ctype or 'application/octet-stream'
            if ctype.startswith('text/') or ctype in ('application/javascript', 'application/json'):
                ctype += '; charset=utf-8'
            self._send_bytes(target.read_bytes(), ctype, 200)

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path
            qs = parse_qs(parsed.query)
            if not path.startswith('/api/'):
                return self._serve_static(path)
            try:
                self._route_get(path, qs)
            except Exception as exc:
                self._send_json({'error': f'Error interno: {exc}'}, 500)

        def do_POST(self):
            parsed = urlparse(self.path)
            if not self._require_csrf():
                return
            try:
                body = self._read_json()
                self._route_post(parsed.path, body)
            except ValueError as exc:
                self._send_json({'error': str(exc)}, 400)
            except Exception as exc:
                self._send_json({'error': f'Error interno: {exc}'}, 500)

        def do_PUT(self):
            parsed = urlparse(self.path)
            if not self._require_csrf():
                return
            try:
                body = self._read_json()
                self._route_put(parsed.path, body)
            except ValueError as exc:
                self._send_json({'error': str(exc)}, 400)
            except Exception as exc:
                self._send_json({'error': f'Error interno: {exc}'}, 500)

        def do_DELETE(self):
            parsed = urlparse(self.path)
            if not self._require_csrf():
                return
            try:
                body = self._read_json()
                self._route_delete(parsed.path, body)
            except ValueError as exc:
                self._send_json({'error': str(exc)}, 400)
            except Exception as exc:
                self._send_json({'error': f'Error interno: {exc}'}, 500)

        # ──────────────────── GET ROUTES ────────────────────
        def _route_get(self, path: str, qs: dict):
            if path == '/api/health':
                return self._send_json({'status': 'ok'})

            if path == '/api/auth/status':
                u = self._current_user(touch=True)
                with ctx.db.connect() as conn:
                    ucount = conn.execute('SELECT COUNT(*) AS c FROM users').fetchone()['c']
                    pending_email = None
                    if u:
                        p = conn.execute(
                            "SELECT target_email, expires_at FROM otc_codes WHERE user_id = ? AND purpose = 'email_verify'",
                            (u['id'],),
                        ).fetchone()
                        if p and p['expires_at'] > time.time():
                            pending_email = {'addr': p['target_email'], 'exp': p['expires_at']}
                mcfg = ctx.mail.get_public_config()
                return self._send_json({
                    'needsSetup': ucount == 0,
                    'mailMode': mcfg['mode'],
                    'appName': ctx.config.get('APP_NAME', 'Agenda de Citas'),
                    'user': ({**serialize_user(u), 'pendingEmail': pending_email} if u else None),
                })

            if path == '/api/outbox':
                if ctx.mail.get_config()['mode'] != 'demo':
                    return self._send_json({'error': 'La bandeja de demostración solo está disponible en modo demo.'}, 403)
                with ctx.db.connect() as conn:
                    rows = conn.execute('SELECT created_at AS t, to_email AS "to", subject, body AS text FROM outbox ORDER BY id DESC LIMIT 20').fetchall()
                return self._send_json({'messages': [dict(r) for r in rows]})

            # Public booking endpoints
            m = re.match(r'^/api/public/agendas/([^/]+)$', path)
            if m:
                slug = m.group(1)
                with ctx.db.connect() as conn:
                    ag = conn.execute('SELECT * FROM agendas WHERE slug = ? AND public_booking = 1', (slug,)).fetchone()
                    if not ag:
                        return self._send_json({'error': 'Agenda no encontrada o reservas públicas desactivadas.'}, 404)
                    svcs = conn.execute('SELECT id, name, dur, price FROM services WHERE agenda_id = ? ORDER BY id', (ag['id'],)).fetchall()
                return self._send_json({
                    'name': ag['name'],
                    'slug': ag['slug'],
                    'phone': ag['phone'],
                    'address': ag['address'],
                    'workDays': json.loads(ag['work_days']),
                    'hourStart': ag['hour_start'],
                    'hourEnd': ag['hour_end'],
                    'slotDur': ag['slot_dur'],
                    'services': [dict(s) for s in svcs],
                })

            m = re.match(r'^/api/public/agendas/([^/]+)/slots$', path)
            if m:
                slug = m.group(1)
                date_str = (qs.get('date') or [''])[0]
                svc_id = (qs.get('service_id') or [''])[0]
                with ctx.db.connect() as conn:
                    ag = conn.execute('SELECT * FROM agendas WHERE slug = ? AND public_booking = 1', (slug,)).fetchone()
                    if not ag:
                        return self._send_json({'error': 'Agenda no disponible.'}, 404)
                    dur = ag['slot_dur']
                    if svc_id.isdigit():
                        s = conn.execute('SELECT dur FROM services WHERE id = ? AND agenda_id = ?', (int(svc_id), ag['id'])).fetchone()
                        if s:
                            dur = s['dur']
                    apts = conn.execute(
                        "SELECT * FROM appointments WHERE agenda_id = ? AND date = ? AND status != 'cancelled'",
                        (ag['id'], date_str),
                    ).fetchall()
                slots = get_available_slots(dict(ag), [dict(a) for a in apts], date_str, dur)
                return self._send_json({'date': date_str, 'duration': dur, 'slots': slots})

            # Authenticated routes below
            u = self._current_user()
            if not u:
                return self._send_json({'error': 'Sesión requerida.'}, 401)

            if path == '/api/admin/users':
                if u['role'] != 'admin':
                    return self._send_json({'error': 'Acceso restringido a administradores.'}, 403)
                with ctx.db.connect() as conn:
                    users = [serialize_user(r) for r in conn.execute('SELECT * FROM users ORDER BY created_at').fetchall()]
                    logs = [dict(r) for r in conn.execute('SELECT created_at AS t, username AS u, event AS e FROM audit_log ORDER BY id DESC LIMIT 40').fetchall()]
                return self._send_json({'users': users, 'log': logs})

            if path == '/api/admin/mail':
                if u['role'] != 'admin':
                    return self._send_json({'error': 'Acceso restringido a administradores.'}, 403)
                return self._send_json(ctx.mail.get_public_config())

            if path == '/api/agendas':
                with ctx.db.connect() as conn:
                    if u['role'] == 'admin':
                        rows = conn.execute(
                            'SELECT a.*, u.user AS owner_user FROM agendas a JOIN users u ON u.id = a.owner_id ORDER BY a.created_at'
                        ).fetchall()
                    else:
                        rows = conn.execute(
                            'SELECT a.*, u.user AS owner_user FROM agendas a JOIN users u ON u.id = a.owner_id WHERE a.owner_id = ? ORDER BY a.created_at',
                            (u['id'],),
                        ).fetchall()
                    if not rows:
                        aid = ctx.db.create_default_agenda(conn, u['id'], 'Mi Negocio')
                        rows = conn.execute(
                            'SELECT a.*, u.user AS owner_user FROM agendas a JOIN users u ON u.id = a.owner_id WHERE a.id = ?',
                            (aid,),
                        ).fetchall()
                return self._send_json({'agendas': [serialize_agenda_summary(r, r['owner_user']) for r in rows]})

            m = re.match(r'^/api/agendas/([^/]+)$', path)
            if m:
                aid = m.group(1)
                with ctx.db.connect() as conn:
                    ag = self._get_authorized_agenda(conn, aid, u)
                    if not ag:
                        return self._send_json({'error': 'Agenda no encontrada.'}, 404)
                    svcs = [dict(r) for r in conn.execute('SELECT id, name, dur, price, price_num AS priceNum FROM services WHERE agenda_id = ? ORDER BY id', (aid,)).fetchall()]
                    apts = [
                        {
                            'id': r['id'], 'clientId': r['client_id'], 'client': r['client_name'],
                            'phone': r['client_phone'], 'email': r['client_email'], 'date': r['date'],
                            'time': r['time'], 'duration': r['duration'], 'service': r['service_name'],
                            'price': r['service_price'], 'notes': r['notes'], 'status': r['status'],
                            'source': r['source'], 'reminderSent': bool(r['reminder_sent']),
                        }
                        for r in conn.execute('SELECT * FROM appointments WHERE agenda_id = ? ORDER BY date, time', (aid,)).fetchall()
                    ]
                    clients = [dict(r) for r in conn.execute('SELECT id, name, phone, email, notes FROM clients WHERE agenda_id = ? ORDER BY name', (aid,)).fetchall()]
                return self._send_json({
                    'id': ag['id'],
                    'name': ag['name'],
                    'slug': ag['slug'],
                    'publicBooking': bool(ag['public_booking']),
                    'autoConfirmPublic': bool(ag['auto_confirm_public']),
                    'workDays': json.loads(ag['work_days']),
                    'hourStart': ag['hour_start'],
                    'hourEnd': ag['hour_end'],
                    'slotDur': ag['slot_dur'],
                    'breaks': json.loads(ag['breaks']),
                    'phone': ag['phone'],
                    'address': ag['address'],
                    'services': svcs,
                    'appointments': apts,
                    'clients': clients,
                })

            m = re.match(r'^/api/agendas/([^/]+)/clients$', path)
            if m:
                aid = m.group(1)
                with ctx.db.connect() as conn:
                    if not self._get_authorized_agenda(conn, aid, u):
                        return self._send_json({'error': 'Agenda no encontrada.'}, 404)
                    rows = conn.execute(
                        """SELECT c.id, c.name, c.phone, c.email, c.notes, c.created_at,
                                  COUNT(a.id) AS total_apts,
                                  SUM(CASE WHEN a.status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled_apts,
                                  MAX(a.date) AS last_visit
                           FROM clients c
                           LEFT JOIN appointments a ON a.client_id = c.id
                           WHERE c.agenda_id = ?
                           GROUP BY c.id
                           ORDER BY c.name""",
                        (aid,),
                    ).fetchall()
                return self._send_json({'clients': [dict(r) for r in rows]})

            m = re.match(r'^/api/agendas/([^/]+)/clients/(\d+)/history$', path)
            if m:
                aid, cid = m.group(1), int(m.group(2))
                with ctx.db.connect() as conn:
                    if not self._get_authorized_agenda(conn, aid, u):
                        return self._send_json({'error': 'Agenda no encontrada.'}, 404)
                    c = conn.execute('SELECT * FROM clients WHERE id = ? AND agenda_id = ?', (cid, aid)).fetchone()
                    if not c:
                        return self._send_json({'error': 'Cliente no encontrado.'}, 404)
                    apts = [dict(r) for r in conn.execute(
                        'SELECT id, date, time, duration, service_name AS service, service_price AS price, status, notes FROM appointments WHERE agenda_id = ? AND client_id = ? ORDER BY date DESC, time DESC',
                        (aid, cid),
                    ).fetchall()]
                return self._send_json({'client': dict(c), 'appointments': apts})

            m = re.match(r'^/api/agendas/([^/]+)/reports$', path)
            if m:
                aid = m.group(1)
                d_from = (qs.get('from') or [''])[0]
                d_to = (qs.get('to') or [''])[0]
                with ctx.db.connect() as conn:
                    if not self._get_authorized_agenda(conn, aid, u):
                        return self._send_json({'error': 'Agenda no encontrada.'}, 404)
                    apts = [dict(r) for r in conn.execute('SELECT * FROM appointments WHERE agenda_id = ?', (aid,)).fetchall()]
                return self._send_json(build_report(apts, d_from, d_to))

            m = re.match(r'^/api/agendas/([^/]+)/export\.csv$', path)
            if m:
                aid = m.group(1)
                with ctx.db.connect() as conn:
                    ag = self._get_authorized_agenda(conn, aid, u)
                    if not ag:
                        return self._send_json({'error': 'Agenda no encontrada.'}, 404)
                    apts = [dict(r) for r in conn.execute('SELECT * FROM appointments WHERE agenda_id = ?', (aid,)).fetchall()]
                csv_data = export_csv(apts).encode('utf-8-sig')
                fname = f"citas-{ag['slug']}.csv"
                return self._send_bytes(csv_data, 'text/csv; charset=utf-8', 200, [('Content-Disposition', f'attachment; filename="{fname}"')])

            m = re.match(r'^/api/agendas/([^/]+)/export\.ics$', path)
            if m:
                aid = m.group(1)
                with ctx.db.connect() as conn:
                    ag = self._get_authorized_agenda(conn, aid, u)
                    if not ag:
                        return self._send_json({'error': 'Agenda no encontrada.'}, 404)
                    apts = [dict(r) for r in conn.execute('SELECT * FROM appointments WHERE agenda_id = ?', (aid,)).fetchall()]
                ics_data = export_ics(ag['name'], apts).encode('utf-8')
                fname = f"agenda-{ag['slug']}.ics"
                return self._send_bytes(ics_data, 'text/calendar; charset=utf-8', 200, [('Content-Disposition', f'attachment; filename="{fname}"')])

            return self._send_json({'error': 'Ruta no encontrada.'}, 404)

        # ──────────────────── POST ROUTES ────────────────────
        def _route_post(self, path: str, body: dict):
            ip = self._client_ip()

            if path == '/api/auth/register':
                ok, retry = ctx.limiter.allow(f'reg:{ip}', 10, 600)
                if not ok:
                    return self._send_json({'error': f'Demasiados intentos. Espera {retry} s.'}, 429)
                username = str(body.get('user', '')).strip().lower()
                name = str(body.get('name', '')).strip()
                email = str(body.get('email', '')).strip().lower()
                pw = str(body.get('password', ''))
                setup_token = str(body.get('setupToken', '')).strip()

                if not USER_RE.match(username):
                    return self._send_json({'error': 'Usuario: 3-20 caracteres (a-z, 0-9, . _ -)'}, 400)
                if not name or len(name) > 40:
                    return self._send_json({'error': 'Nombre requerido (máx. 40 caracteres)'}, 400)
                if email and (not EMAIL_RE.match(email) or len(email) > 80):
                    return self._send_json({'error': 'Correo no válido'}, 400)
                if not pw_ok(pw):
                    return self._send_json({'error': POLICY_MSG}, 400)

                with ctx.db.connect() as conn:
                    ucount = conn.execute('SELECT COUNT(*) AS c FROM users').fetchone()['c']
                    role = 'usuario'
                    if ucount == 0:
                        expected_tok = ctx.db.get_setup_token()
                        if expected_tok and setup_token != expected_tok:
                            return self._send_json({'error': 'Token de configuración inicial inválido. Consúltalo en la consola del servidor o en .env.'}, 403)
                        role = 'admin'
                        ctx.db.clear_setup_token(conn)
                    if conn.execute('SELECT 1 FROM users WHERE user = ?', (username,)).fetchone():
                        return self._send_json({'error': 'Usuario no disponible'}, 409)
                    uid = random_hex(8)
                    salt = random_hex(16)
                    pw_hash = hash_password(pw, salt)
                    conn.execute(
                        """INSERT INTO users (id, user, name, role, salt, hash, active, email, email_ok, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, 1, ?, 0, ?)""",
                        (uid, username, name, role, salt, pw_hash, email, now_str()),
                    )
                    ctx.db.create_default_agenda(conn, uid, 'Mi Negocio')
                    ctx.db.add_log(f'Alta de usuario {username} ({role})', username, conn)
                    user_row = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
                    tok, ttl = self._create_session(conn, user_row)
                return self._send_json({'user': serialize_user(user_row)}, 201, [self._cookie_header(tok, ttl)])

            if path == '/api/auth/login':
                ok, retry = ctx.limiter.allow(f'login:{ip}', 20, 300)
                if not ok:
                    return self._send_json({'error': f'Demasiados intentos. Espera {retry} s.'}, 429)
                username = str(body.get('user', '')).strip().lower()
                pw = str(body.get('password', ''))
                with ctx.db.connect() as conn:
                    u = conn.execute('SELECT * FROM users WHERE user = ?', (username,)).fetchone()
                    if not u or not u['active']:
                        hash_password(pw, random_hex(16))
                        return self._send_json({'error': 'Credenciales inválidas'}, 401)
                    if u['lock_until'] > time.time():
                        mins = max(1, int((u['lock_until'] - time.time() + 59) // 60))
                        return self._send_json({'error': f'Cuenta bloqueada. Intenta en {mins} min.'}, 423)
                    if not verify_password(pw, u['salt'], u['hash']):
                        self._register_fail(conn, u, 'Bloqueo por intentos fallidos')
                        return self._send_json({'error': 'Credenciales inválidas'}, 401)
                    if u['totp_on']:
                        mtok = random_hex(20)
                        conn.execute('INSERT INTO mfa_pending (token, user_id, expires_at) VALUES (?, ?, ?)', (mtok, u['id'], time.time() + 300))
                        return self._send_json({'mfaRequired': True, 'mfaToken': mtok})
                    conn.execute('UPDATE users SET fails = 0 WHERE id = ?', (u['id'],))
                    tok, ttl = self._create_session(conn, u)
                    ctx.db.add_log('Inicio de sesión', u['user'], conn)
                return self._send_json({'user': serialize_user(u)}, 200, [self._cookie_header(tok, ttl)])

            if path == '/api/auth/mfa':
                mtok = str(body.get('mfaToken', ''))
                code = str(body.get('code', ''))
                with ctx.db.connect() as conn:
                    m = conn.execute('SELECT * FROM mfa_pending WHERE token = ?', (mtok,)).fetchone()
                    if not m or m['expires_at'] < time.time():
                        return self._send_json({'error': 'Sesión MFA vencida. Inicia sesión de nuevo.'}, 401)
                    u = conn.execute('SELECT * FROM users WHERE id = ? AND active = 1', (m['user_id'],)).fetchone()
                    if not u:
                        return self._send_json({'error': 'Cuenta no disponible.'}, 401)
                    if not self._verify_second_factor(conn, u, code):
                        locked = self._register_fail(conn, u, 'Bloqueo por 2FA fallido')
                        if locked:
                            conn.execute('DELETE FROM mfa_pending WHERE token = ?', (mtok,))
                            return self._send_json({'error': 'Cuenta bloqueada 5 min.', 'locked': True}, 423)
                        return self._send_json({'error': 'Código incorrecto'}, 401)
                    conn.execute('DELETE FROM mfa_pending WHERE token = ?', (mtok,))
                    conn.execute('UPDATE users SET fails = 0 WHERE id = ?', (u['id'],))
                    tok, ttl = self._create_session(conn, u)
                    ctx.db.add_log('Inicio de sesión (2FA)', u['user'], conn)
                return self._send_json({'user': serialize_user(u)}, 200, [self._cookie_header(tok, ttl)])

            if path == '/api/auth/logout':
                tok = self._get_session_token()
                u = self._current_user(touch=False)
                with ctx.db.connect() as conn:
                    if tok:
                        conn.execute('DELETE FROM sessions WHERE token = ?', (tok,))
                    if u:
                        ctx.db.add_log('Cierre de sesión', u['user'], conn)
                return self._send_json({'ok': True}, 200, [self._cookie_header('', 0)])

            if path == '/api/auth/forgot':
                ok, retry = ctx.limiter.allow(f'forgot:{ip}', 10, 600)
                if not ok:
                    return self._send_json({'error': f'Demasiados intentos. Espera {retry} s.'}, 429)
                ident = str(body.get('identifier', '')).strip().lower()
                if not ident:
                    return self._send_json({'error': 'Escribe tu usuario o tu correo'}, 400)
                with ctx.db.connect() as conn:
                    u = conn.execute(
                        'SELECT * FROM users WHERE active = 1 AND (user = ? OR (email_ok = 1 AND email = ?))',
                        (ident, ident),
                    ).fetchone()
                    mail_job = None
                    if u and u['email_ok'] and u['rec_email']:
                        prev = conn.execute(
                            "SELECT sent_at FROM otc_codes WHERE user_id = ? AND purpose = 'password_reset'",
                            (u['id'],),
                        ).fetchone()
                        if not prev or (time.time() - prev['sent_at'] >= OTC_COOLDOWN_SEC):
                            code = numeric_code(6)
                            salt = random_hex(16)
                            h = hash_password(code, salt)
                            now = time.time()
                            conn.execute(
                                """INSERT OR REPLACE INTO otc_codes (user_id, purpose, target_email, salt, hash, expires_at, tries, sent_at)
                                   VALUES (?, 'password_reset', ?, ?, ?, ?, 0, ?)""",
                                (u['id'], u['email'], salt, h, now + OTC_TTL_SEC, now),
                            )
                            mail_job = (u['email'], u['name'], u['user'], code)
                    else:
                        hash_password(ident, random_hex(16))
                if mail_job:
                    try:
                        ctx.mail.send_reset_code(*mail_job)
                        ctx.db.add_log('Código de recuperación enviado', mail_job[2])
                    except Exception as exc:
                        ctx.db.add_log(f'Fallo envío recuperación: {exc}', mail_job[2])
                return self._send_json({'message': 'Si la cuenta existe y tiene un correo verificado, enviamos un código. Vence en 10 minutos.'})

            if path == '/api/auth/reset':
                ident = str(body.get('identifier', '')).strip().lower()
                code = re.sub(r'\s+', '', str(body.get('code', '')))
                pw = str(body.get('password', ''))
                tf = str(body.get('twoFactor', ''))
                bad = 'Código inválido o vencido. Si hace falta, pide uno nuevo.'
                with ctx.db.connect() as conn:
                    u = conn.execute(
                        'SELECT * FROM users WHERE active = 1 AND (user = ? OR (email_ok = 1 AND email = ?))',
                        (ident, ident),
                    ).fetchone()
                    if not u:
                        hash_password(code, random_hex(16))
                        return self._send_json({'error': bad}, 400)
                    rec = conn.execute(
                        "SELECT * FROM otc_codes WHERE user_id = ? AND purpose = 'password_reset'",
                        (u['id'],),
                    ).fetchone()
                    if not rec or rec['expires_at'] < time.time() or rec['tries'] >= OTC_MAX_TRIES:
                        return self._send_json({'error': bad}, 400)
                    if not verify_password(code, rec['salt'], rec['hash']):
                        conn.execute(
                            "UPDATE otc_codes SET tries = tries + 1 WHERE user_id = ? AND purpose = 'password_reset'",
                            (u['id'],),
                        )
                        return self._send_json({'error': bad}, 400)
                    if not pw_ok(pw):
                        return self._send_json({'error': POLICY_MSG}, 400)
                    if not self._verify_second_factor(conn, u, tf):
                        return self._send_json({'error': 'Verificación en dos pasos incorrecta'}, 400)
                    salt = random_hex(16)
                    conn.execute(
                        'UPDATE users SET salt = ?, hash = ?, fails = 0, lock_until = 0 WHERE id = ?',
                        (salt, hash_password(pw, salt), u['id']),
                    )
                    conn.execute("DELETE FROM otc_codes WHERE user_id = ? AND purpose = 'password_reset'", (u['id'],))
                    conn.execute('DELETE FROM sessions WHERE user_id = ?', (u['id'],))
                    ctx.db.add_log('Contraseña restablecida por correo', u['user'], conn)
                return self._send_json({'message': 'Contraseña actualizada. Ya puedes iniciar sesión.'})

            if path == '/api/auth/recover':
                username = str(body.get('user', '')).strip().lower()
                rc = norm_code(body.get('code', ''))
                pw = str(body.get('password', ''))
                tf = str(body.get('twoFactor', ''))
                with ctx.db.connect() as conn:
                    u = conn.execute('SELECT * FROM users WHERE user = ? AND active = 1', (username,)).fetchone()
                    if not u:
                        hash_password(pw, random_hex(16))
                        return self._send_json({'error': 'Datos inválidos'}, 400)
                    if u['lock_until'] > time.time():
                        mins = max(1, int((u['lock_until'] - time.time() + 59) // 60))
                        return self._send_json({'error': f'Cuenta bloqueada. Intenta en {mins} min.'}, 423)
                    codes_list = json.loads(u['rec_codes'] or '[]')
                    h = sha256_hex(rc)
                    if h not in codes_list:
                        self._register_fail(conn, u, 'Bloqueo por códigos de recuperación fallidos')
                        return self._send_json({'error': 'Datos inválidos'}, 400)
                    if not pw_ok(pw):
                        return self._send_json({'error': POLICY_MSG}, 400)
                    if not self._verify_second_factor(conn, u, tf):
                        self._register_fail(conn, u, 'Bloqueo por 2FA fallido en recuperación')
                        return self._send_json({'error': 'Verificación en dos pasos incorrecta'}, 400)
                    codes_list.remove(h)
                    salt = random_hex(16)
                    conn.execute(
                        'UPDATE users SET salt = ?, hash = ?, rec_codes = ?, fails = 0, lock_until = 0 WHERE id = ?',
                        (salt, hash_password(pw, salt), json.dumps(codes_list), u['id']),
                    )
                    conn.execute('DELETE FROM sessions WHERE user_id = ?', (u['id'],))
                    ctx.db.add_log('Contraseña restablecida con código de recuperación', u['user'], conn)
                return self._send_json({'message': 'Contraseña actualizada. Ya puedes iniciar sesión.'})

            # Public booking submission
            m = re.match(r'^/api/public/agendas/([^/]+)/book$', path)
            if m:
                ok, retry = ctx.limiter.allow(f'book:{ip}', 15, 600)
                if not ok:
                    return self._send_json({'error': f'Demasiadas reservas desde tu red. Intenta en {retry} s.'}, 429)
                slug = m.group(1)
                client_name = str(body.get('client', '')).strip()[:80]
                client_phone = str(body.get('phone', '')).strip()[:40]
                client_email = str(body.get('email', '')).strip().lower()[:80]
                date_str = str(body.get('date', '')).strip()
                time_str = str(body.get('time', '')).strip()
                notes = str(body.get('notes', '')).strip()[:300]
                svc_id = body.get('serviceId')

                if not client_name or not date_str or not time_str:
                    return self._send_json({'error': 'Nombre, fecha y hora son obligatorios.'}, 400)
                if client_email and not EMAIL_RE.match(client_email):
                    return self._send_json({'error': 'Correo electrónico no válido.'}, 400)

                with ctx.db.connect() as conn:
                    ag = conn.execute('SELECT * FROM agendas WHERE slug = ? AND public_booking = 1', (slug,)).fetchone()
                    if not ag:
                        return self._send_json({'error': 'Esta agenda no acepta reservas en línea.'}, 404)
                    svc = None
                    if svc_id is not None:
                        svc = conn.execute('SELECT * FROM services WHERE id = ? AND agenda_id = ?', (int(svc_id), ag['id'])).fetchone()
                    if not svc:
                        svc = conn.execute('SELECT * FROM services WHERE agenda_id = ? ORDER BY id LIMIT 1', (ag['id'],)).fetchone()
                    svc_name = svc['name'] if svc else 'Cita general'
                    dur = int(svc['dur']) if svc else int(ag['slot_dur'])
                    price_num = float(svc['price_num']) if svc else 0.0

                    existing = [dict(r) for r in conn.execute('SELECT * FROM appointments WHERE agenda_id = ? AND date = ?', (ag['id'], date_str)).fetchall()]
                    errs = validate_appointment(dict(ag), existing, date_str, time_str, dur, status='pending', allow_past=False)
                    if errs:
                        return self._send_json({'error': errs[0], 'errors': errs}, 409)

                    status = 'confirmed' if ag['auto_confirm_public'] else 'pending'
                    cid = ctx.db.upsert_client(conn, ag['id'], client_name, client_phone, client_email)
                    cur = conn.execute(
                        """INSERT INTO appointments
                           (agenda_id, client_id, client_name, client_phone, client_email, date, time, duration,
                            service_name, service_price, notes, status, source, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'public', ?)""",
                        (ag['id'], cid, client_name, client_phone, client_email, date_str, time_str, dur,
                         svc_name, price_num, notes, status, now_str()),
                    )
                    apt_id = cur.lastrowid
                    owner = conn.execute('SELECT email, email_ok, name FROM users WHERE id = ?', (ag['owner_id'],)).fetchone()
                    ctx.db.add_log(f'Reserva pública #{apt_id} en {ag["name"]} ({client_name})', 'public', conn)

                # Send notifications outside DB lock
                try:
                    if client_email:
                        ctx.mail.send_appointment_notice(
                            client_email, ag['name'], client_name, date_str, time_str, svc_name, status,
                            kind='confirmed' if status == 'confirmed' else 'created',
                            address=ag['address'], phone=ag['phone'],
                        )
                    if owner and owner['email_ok'] and owner['email']:
                        ctx.mail.send(
                            owner['email'],
                            f'Nueva reserva en {ag["name"]} · {date_str} {time_str}',
                            f'Cliente: {client_name}\nTeléfono: {client_phone}\nCorreo: {client_email}\nServicio: {svc_name}\nFecha: {date_str} {time_str}\nEstado: {status}',
                        )
                except Exception:
                    pass

                return self._send_json({
                    'id': apt_id,
                    'status': status,
                    'message': '¡Reserva confirmada!' if status == 'confirmed' else '¡Reserva recibida! Queda pendiente de confirmación.',
                }, 201)

            # Authenticated POST routes
            u = self._current_user()
            if not u:
                return self._send_json({'error': 'Sesión requerida.'}, 401)

            if path == '/api/account/email/send':
                addr = str(body.get('email', '')).strip().lower() or (u['email'] if not u['email_ok'] else '')
                pw = str(body.get('password', ''))
                if not EMAIL_RE.match(addr) or len(addr) > 80:
                    return self._send_json({'error': 'Escribe un correo válido'}, 400)
                if u['email_ok'] and addr == u['email']:
                    return self._send_json({'error': 'Ese ya es tu correo verificado.'}, 400)
                if u['email_ok'] and not verify_password(pw, u['salt'], u['hash']):
                    return self._send_json({'error': 'Contraseña incorrecta'}, 400)
                with ctx.db.connect() as conn:
                    dup = conn.execute('SELECT 1 FROM users WHERE id != ? AND email_ok = 1 AND email = ?', (u['id'], addr)).fetchone()
                    if dup:
                        return self._send_json({'error': 'Ese correo ya está asociado a otra cuenta'}, 409)
                    prev = conn.execute("SELECT target_email, sent_at FROM otc_codes WHERE user_id = ? AND purpose = 'email_verify'", (u['id'],)).fetchone()
                    if prev and prev['target_email'] == addr and (time.time() - prev['sent_at'] < OTC_COOLDOWN_SEC):
                        wait = int(OTC_COOLDOWN_SEC - (time.time() - prev['sent_at'])) + 1
                        return self._send_json({'error': f'Espera {wait} s para pedir otro código.'}, 429)
                    code = numeric_code(6)
                    salt = random_hex(16)
                    h = hash_password(code, salt)
                    now = time.time()
                    try:
                        mode_res = ctx.mail.send_verify_code(addr, u['name'], code)
                    except Exception as exc:
                        return self._send_json({'error': str(exc)}, 502)
                    conn.execute(
                        """INSERT OR REPLACE INTO otc_codes (user_id, purpose, target_email, salt, hash, expires_at, tries, sent_at)
                           VALUES (?, 'email_verify', ?, ?, ?, ?, 0, ?)""",
                        (u['id'], addr, salt, h, now + OTC_TTL_SEC, now),
                    )
                    if not u['email_ok']:
                        conn.execute('UPDATE users SET email = ? WHERE id = ?', (addr, u['id']))
                    ctx.db.add_log(f'Código de verificación enviado a {addr}', u['user'], conn)
                return self._send_json({'message': 'Código generado (modo demostración).' if mode_res == 'demo' else 'Te enviamos un código. Revisa tu correo.'})

            if path == '/api/account/email/verify':
                code = re.sub(r'\s+', '', str(body.get('code', '')))
                with ctx.db.connect() as conn:
                    rec = conn.execute("SELECT * FROM otc_codes WHERE user_id = ? AND purpose = 'email_verify'", (u['id'],)).fetchone()
                    if not rec or rec['expires_at'] < time.time() or rec['tries'] >= OTC_MAX_TRIES:
                        conn.execute("DELETE FROM otc_codes WHERE user_id = ? AND purpose = 'email_verify'", (u['id'],))
                        return self._send_json({'error': 'El código venció o se agotaron los intentos. Pide uno nuevo.'}, 400)
                    if not verify_password(code, rec['salt'], rec['hash']):
                        conn.execute("UPDATE otc_codes SET tries = tries + 1 WHERE user_id = ? AND purpose = 'email_verify'", (u['id'],))
                        return self._send_json({'error': 'Código incorrecto'}, 400)
                    addr = rec['target_email']
                    dup = conn.execute('SELECT 1 FROM users WHERE id != ? AND email_ok = 1 AND email = ?', (u['id'], addr)).fetchone()
                    if dup:
                        conn.execute("DELETE FROM otc_codes WHERE user_id = ? AND purpose = 'email_verify'", (u['id'],))
                        return self._send_json({'error': 'Ese correo ya está asociado a otra cuenta'}, 409)
                    conn.execute('UPDATE users SET email = ?, email_ok = 1 WHERE id = ?', (addr, u['id']))
                    conn.execute("DELETE FROM otc_codes WHERE user_id = ? AND purpose = 'email_verify'", (u['id'],))
                    ctx.db.add_log(f'Correo verificado: {addr}', u['user'], conn)
                return self._send_json({'message': 'Correo verificado.'})

            if path == '/api/account/recovery-codes':
                pw = str(body.get('password', ''))
                if not verify_password(pw, u['salt'], u['hash']):
                    return self._send_json({'error': 'Contraseña incorrecta'}, 400)
                plain, hashed = generate_recovery_codes(8)
                with ctx.db.connect() as conn:
                    conn.execute('UPDATE users SET rec_codes = ? WHERE id = ?', (json.dumps(hashed), u['id']))
                    ctx.db.add_log('Códigos de recuperación generados', u['user'], conn)
                return self._send_json({'codes': plain})

            if path == '/api/account/2fa/setup':
                secret = generate_totp_secret()
                with ctx.db.connect() as conn:
                    conn.execute('UPDATE users SET totp_secret = ?, totp_on = 0 WHERE id = ?', (secret, u['id']))
                uri = f"otpauth://totp/AgendaCitas:{quote(u['user'])}?secret={secret}&issuer=AgendaCitas"
                return self._send_json({'secret': secret, 'otpauthUri': uri})

            if path == '/api/account/2fa/confirm':
                code = str(body.get('code', ''))
                if not u['totp_secret'] or not check_totp(u['totp_secret'], code):
                    return self._send_json({'error': 'Código incorrecto'}, 400)
                plain, hashed = generate_backup_codes(8)
                with ctx.db.connect() as conn:
                    conn.execute('UPDATE users SET totp_on = 1, backup_codes = ? WHERE id = ?', (json.dumps(hashed), u['id']))
                    ctx.db.add_log('2FA activada', u['user'], conn)
                return self._send_json({'backupCodes': plain})

            if path == '/api/account/2fa/disable':
                pw = str(body.get('password', ''))
                if not verify_password(pw, u['salt'], u['hash']):
                    return self._send_json({'error': 'Contraseña incorrecta'}, 400)
                with ctx.db.connect() as conn:
                    conn.execute("UPDATE users SET totp_on = 0, totp_secret = NULL, backup_codes = '[]' WHERE id = ?", (u['id'],))
                    ctx.db.add_log('2FA desactivada', u['user'], conn)
                return self._send_json({'message': 'Verificación en dos pasos desactivada.'})

            if path == '/api/admin/mail/test':
                if u['role'] != 'admin':
                    return self._send_json({'error': 'Solo administradores.'}, 403)
                if not u['email_ok']:
                    return self._send_json({'error': 'Verifica primero tu correo en la pestaña Correo.'}, 400)
                try:
                    res = ctx.mail.send(
                        u['email'],
                        f"Correo de prueba · {ctx.config.get('APP_NAME', 'Agenda de Citas')}",
                        'Este es un correo de prueba. Si lo recibiste, la configuración SMTP funciona correctamente.',
                    )
                except Exception as exc:
                    return self._send_json({'error': f'Error enviando correo: {exc}'}, 502)
                return self._send_json({'mode': res, 'message': 'Mensaje guardado en bandeja de demostración.' if res == 'demo' else f'Correo de prueba enviado a {u["email"]}.'})

            if path == '/api/agendas':
                name = str(body.get('name', '')).strip()[:40]
                if not name:
                    return self._send_json({'error': 'Nombre requerido.'}, 400)
                with ctx.db.connect() as conn:
                    aid = ctx.db.create_default_agenda(conn, u['id'], name)
                    ctx.db.add_log(f'Agenda creada: {name}', u['user'], conn)
                    row = conn.execute('SELECT * FROM agendas WHERE id = ?', (aid,)).fetchone()
                return self._send_json(serialize_agenda_summary(row, u['user']), 201)

            m = re.match(r'^/api/agendas/([^/]+)/services$', path)
            if m:
                aid = m.group(1)
                name = str(body.get('name', '')).strip()[:60]
                dur = int(body.get('dur') or 30)
                price = str(body.get('price', '$0')).strip()[:20] or '$0'
                if not name:
                    return self._send_json({'error': 'Nombre del servicio requerido.'}, 400)
                if dur < 5 or dur > 480:
                    return self._send_json({'error': 'Duración inválida (5-480 min).'}, 400)
                with ctx.db.connect() as conn:
                    if not self._get_authorized_agenda(conn, aid, u):
                        return self._send_json({'error': 'Agenda no encontrada.'}, 404)
                    cur = conn.execute(
                        'INSERT INTO services (agenda_id, name, dur, price, price_num) VALUES (?, ?, ?, ?, ?)',
                        (aid, name, dur, price, parse_price(price)),
                    )
                    sid = cur.lastrowid
                return self._send_json({'id': sid, 'name': name, 'dur': dur, 'price': price, 'priceNum': parse_price(price)}, 201)

            m = re.match(r'^/api/agendas/([^/]+)/clients$', path)
            if m:
                aid = m.group(1)
                name = str(body.get('name', '')).strip()[:80]
                phone = str(body.get('phone', '')).strip()[:40]
                email = str(body.get('email', '')).strip().lower()[:80]
                notes = str(body.get('notes', '')).strip()[:300]
                if not name:
                    return self._send_json({'error': 'El nombre del cliente es obligatorio.'}, 400)
                if email and not EMAIL_RE.match(email):
                    return self._send_json({'error': 'Correo electrónico inválido.'}, 400)
                with ctx.db.connect() as conn:
                    if not self._get_authorized_agenda(conn, aid, u):
                        return self._send_json({'error': 'Agenda no encontrada.'}, 404)
                    cid = ctx.db.upsert_client(conn, aid, name, phone, email, notes)
                return self._send_json({'id': cid, 'name': name, 'phone': phone, 'email': email, 'notes': notes}, 201)

            m = re.match(r'^/api/agendas/([^/]+)/appointments$', path)
            if m:
                aid = m.group(1)
                client_name = str(body.get('client', '')).strip()[:80]
                phone = str(body.get('phone', '')).strip()[:40]
                email = str(body.get('email', '')).strip().lower()[:80]
                date_str = str(body.get('date', '')).strip()
                time_str = str(body.get('time', '')).strip()
                svc_name = str(body.get('service', '')).strip()[:60]
                notes = str(body.get('notes', '')).strip()[:300]
                status = str(body.get('status', 'confirmed')).strip()
                notify = bool(body.get('notify', True))

                if not client_name or not date_str or not time_str:
                    return self._send_json({'error': 'Cliente, fecha y hora son obligatorios.'}, 400)
                if status not in ('confirmed', 'pending', 'cancelled', 'completed'):
                    return self._send_json({'error': 'Estado de cita inválido.'}, 400)
                if email and not EMAIL_RE.match(email):
                    return self._send_json({'error': 'Correo del cliente inválido.'}, 400)

                with ctx.db.connect() as conn:
                    ag = self._get_authorized_agenda(conn, aid, u)
                    if not ag:
                        return self._send_json({'error': 'Agenda no encontrada.'}, 404)
                    svc = conn.execute('SELECT * FROM services WHERE agenda_id = ? AND name = ?', (aid, svc_name)).fetchone()
                    dur = int(body.get('duration') or (svc['dur'] if svc else ag['slot_dur']))
                    price_num = float(svc['price_num']) if svc else 0.0
                    existing = [dict(r) for r in conn.execute('SELECT * FROM appointments WHERE agenda_id = ? AND date = ?', (aid, date_str)).fetchall()]
                    errs = validate_appointment(dict(ag), existing, date_str, time_str, dur, status=status, allow_past=False)
                    if errs:
                        return self._send_json({'error': errs[0], 'errors': errs}, 409)
                    cid = ctx.db.upsert_client(conn, aid, client_name, phone, email)
                    cur = conn.execute(
                        """INSERT INTO appointments
                           (agenda_id, client_id, client_name, client_phone, client_email, date, time, duration,
                            service_name, service_price, notes, status, source, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'admin', ?)""",
                        (aid, cid, client_name, phone, email, date_str, time_str, dur, svc_name, price_num, notes, status, now_str()),
                    )
                    apt_id = cur.lastrowid

                if notify and email:
                    try:
                        ctx.mail.send_appointment_notice(
                            email, ag['name'], client_name, date_str, time_str, svc_name, status,
                            kind='confirmed' if status == 'confirmed' else 'created',
                            address=ag['address'], phone=ag['phone'],
                        )
                    except Exception:
                        pass
                return self._send_json({'id': apt_id, 'clientId': cid, 'duration': dur}, 201)

            m = re.match(r'^/api/agendas/([^/]+)/appointments/(\d+)/remind$', path)
            if m:
                aid, apt_id = m.group(1), int(m.group(2))
                with ctx.db.connect() as conn:
                    ag = self._get_authorized_agenda(conn, aid, u)
                    if not ag:
                        return self._send_json({'error': 'Agenda no encontrada.'}, 404)
                    apt = conn.execute('SELECT * FROM appointments WHERE id = ? AND agenda_id = ?', (apt_id, aid)).fetchone()
                    if not apt:
                        return self._send_json({'error': 'Cita no encontrada.'}, 404)
                    if not apt['client_email']:
                        return self._send_json({'error': 'Esta cita no tiene un correo de cliente registrado.'}, 400)
                    try:
                        ctx.mail.send_appointment_notice(
                            apt['client_email'], ag['name'], apt['client_name'], apt['date'], apt['time'],
                            apt['service_name'], apt['status'], kind='reminder', address=ag['address'], phone=ag['phone'],
                        )
                    except Exception as exc:
                        return self._send_json({'error': f'Error enviando recordatorio: {exc}'}, 502)
                    conn.execute('UPDATE appointments SET reminder_sent = 1 WHERE id = ?', (apt_id,))
                return self._send_json({'message': f"Recordatorio enviado a {apt['client_email']}."})

            m = re.match(r'^/api/agendas/([^/]+)/send-reminders$', path)
            if m:
                aid = m.group(1)
                tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                sent = 0
                with ctx.db.connect() as conn:
                    ag = self._get_authorized_agenda(conn, aid, u)
                    if not ag:
                        return self._send_json({'error': 'Agenda no encontrada.'}, 404)
                    ag_dict = dict(ag)
                    apts = [dict(r) for r in conn.execute(
                        """SELECT * FROM appointments
                           WHERE agenda_id = ? AND date = ? AND status IN ('confirmed', 'pending')
                             AND client_email != '' AND reminder_sent = 0""",
                        (aid, tomorrow),
                    ).fetchall()]
                sent_ids = []
                for apt in apts:
                    try:
                        ctx.mail.send_appointment_notice(
                            apt['client_email'], ag_dict['name'], apt['client_name'], apt['date'], apt['time'],
                            apt['service_name'], apt['status'], kind='reminder', address=ag_dict['address'], phone=ag_dict['phone'],
                        )
                        sent_ids.append(apt['id'])
                        sent += 1
                    except Exception:
                        pass
                if sent_ids:
                    with ctx.db.connect() as conn:
                        conn.executemany('UPDATE appointments SET reminder_sent = 1 WHERE id = ?', [(i,) for i in sent_ids])
                return self._send_json({'sent': sent, 'date': tomorrow, 'message': f'Se enviaron {sent} recordatorio(s) para mañana ({tomorrow}).'})

            return self._send_json({'error': 'Ruta no encontrada.'}, 404)

        # ──────────────────── PUT ROUTES ────────────────────
        def _route_put(self, path: str, body: dict):
            u = self._current_user()
            if not u:
                return self._send_json({'error': 'Sesión requerida.'}, 401)

            if path == '/api/account/profile':
                name = str(body.get('name', '')).strip()
                if not name or len(name) > 40:
                    return self._send_json({'error': 'Nombre requerido (máx. 40 caracteres)'}, 400)
                with ctx.db.connect() as conn:
                    conn.execute('UPDATE users SET name = ? WHERE id = ?', (name, u['id']))
                    ctx.db.add_log('Perfil actualizado', u['user'], conn)
                return self._send_json({'message': 'Perfil actualizado.', 'name': name})

            if path == '/api/account/recovery-email':
                on = 1 if body.get('enabled') else 0
                with ctx.db.connect() as conn:
                    conn.execute('UPDATE users SET rec_email = ? WHERE id = ?', (on, u['id']))
                    ctx.db.add_log('Recuperación por correo ' + ('activada' if on else 'desactivada'), u['user'], conn)
                return self._send_json({'message': 'Preferencia guardada.'})

            if path == '/api/account/timeout':
                val = int(body.get('timeout') or 15)
                if val not in (5, 15, 30, 60):
                    val = 15
                with ctx.db.connect() as conn:
                    conn.execute('UPDATE users SET timeout_min = ? WHERE id = ?', (val, u['id']))
                    ctx.db.add_log(f'Tiempo de inactividad: {val} min', u['user'], conn)
                return self._send_json({'message': 'Preferencia guardada.', 'timeout': val})

            if path == '/api/account/password':
                old_pw = str(body.get('oldPassword', ''))
                new_pw = str(body.get('newPassword', ''))
                if not verify_password(old_pw, u['salt'], u['hash']):
                    return self._send_json({'error': 'Contraseña actual incorrecta'}, 400)
                if not pw_ok(new_pw):
                    return self._send_json({'error': POLICY_MSG}, 400)
                salt = random_hex(16)
                with ctx.db.connect() as conn:
                    conn.execute('UPDATE users SET salt = ?, hash = ? WHERE id = ?', (salt, hash_password(new_pw, salt), u['id']))
                    conn.execute('DELETE FROM sessions WHERE user_id = ?', (u['id'],))
                    u2 = conn.execute('SELECT * FROM users WHERE id = ?', (u['id'],)).fetchone()
                    tok, ttl = self._create_session(conn, u2)
                    ctx.db.add_log('Cambio de contraseña', u['user'], conn)
                return self._send_json({'message': 'Contraseña actualizada.'}, 200, [self._cookie_header(tok, ttl)])

            if path == '/api/admin/mail':
                if u['role'] != 'admin':
                    return self._send_json({'error': 'Solo administradores.'}, 403)
                mode = body.get('mode', 'demo')
                if mode not in ('demo', 'smtp'):
                    return self._send_json({'error': 'Modo de correo inválido.'}, 400)
                with ctx.db.connect() as conn:
                    cur = conn.execute('SELECT * FROM mail_config WHERE id = 1').fetchone()
                    if mode == 'smtp':
                        host = str(body.get('smtpHost', '')).strip()
                        port = int(body.get('smtpPort') or 587)
                        suser = str(body.get('smtpUser', '')).strip()
                        spass = str(body.get('smtpPass', '')) or cur['smtp_pass']
                        sfrom = str(body.get('smtpFrom', '')).strip() or suser
                        fname = str(body.get('fromName', '')).strip() or 'Agenda de Citas'
                        tls = 1 if body.get('smtpTls', True) else 0
                        if not host or not suser or not spass:
                            return self._send_json({'error': 'Completa host, usuario y contraseña SMTP.'}, 400)
                        conn.execute(
                            """UPDATE mail_config SET mode='smtp', from_name=?, smtp_host=?, smtp_port=?, smtp_user=?, smtp_pass=?, smtp_from=?, smtp_tls=? WHERE id=1""",
                            (fname[:40], host, port, suser, spass, sfrom, tls),
                        )
                    else:
                        conn.execute("UPDATE mail_config SET mode='demo' WHERE id=1")
                    ctx.db.add_log(f'Servicio de correo actualizado: {mode}', u['user'], conn)
                return self._send_json({'message': 'Configuración guardada.', 'config': ctx.mail.get_public_config()})

            m = re.match(r'^/api/admin/users/([^/]+)$', path)
            if m:
                if u['role'] != 'admin':
                    return self._send_json({'error': 'Solo administradores.'}, 403)
                tid = m.group(1)
                with ctx.db.connect() as conn:
                    target = conn.execute('SELECT * FROM users WHERE id = ?', (tid,)).fetchone()
                    if not target:
                        return self._send_json({'error': 'Usuario no encontrado.'}, 404)
                    admins = conn.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'admin' AND active = 1").fetchone()['c']
                    new_role = body.get('role', target['role'])
                    new_active = 1 if body.get('active', bool(target['active'])) else 0
                    if target['role'] == 'admin' and target['active'] and admins < 2 and (new_role != 'admin' or not new_active):
                        return self._send_json({'error': 'Debe existir al menos un administrador activo.'}, 400)
                    if body.get('reset2fa'):
                        conn.execute("UPDATE users SET totp_on = 0, totp_secret = NULL, backup_codes = '[]' WHERE id = ?", (tid,))
                        ctx.db.add_log(f'Admin restableció 2FA de {target["user"]}', u['user'], conn)
                    else:
                        conn.execute('UPDATE users SET role = ?, active = ? WHERE id = ?', (new_role, new_active, tid))
                        if not new_active:
                            conn.execute('DELETE FROM sessions WHERE user_id = ?', (tid,))
                        ctx.db.add_log(f'Admin modificó a {target["user"]}', u['user'], conn)
                return self._send_json({'ok': True})

            m = re.match(r'^/api/agendas/([^/]+)$', path)
            if m:
                aid = m.group(1)
                with ctx.db.connect() as conn:
                    ag = self._get_authorized_agenda(conn, aid, u)
                    if not ag:
                        return self._send_json({'error': 'Agenda no encontrada.'}, 404)
                    name = str(body.get('name', ag['name'])).strip()[:40] or ag['name']
                    work_days = body.get('workDays', json.loads(ag['work_days']))
                    hour_start = str(body.get('hourStart', ag['hour_start']))
                    hour_end = str(body.get('hourEnd', ag['hour_end']))
                    if hour_start >= hour_end:
                        return self._send_json({'error': 'La hora de apertura debe ser anterior al cierre.'}, 400)
                    slot_dur = int(body.get('slotDur', ag['slot_dur']))
                    breaks = body.get('breaks', json.loads(ag['breaks']))
                    phone = str(body.get('phone', ag['phone'])).strip()[:40]
                    address = str(body.get('address', ag['address'])).strip()[:160]
                    pub = 1 if body.get('publicBooking', bool(ag['public_booking'])) else 0
                    auto_c = 1 if body.get('autoConfirmPublic', bool(ag['auto_confirm_public'])) else 0
                    conn.execute(
                        """UPDATE agendas
                           SET name=?, work_days=?, hour_start=?, hour_end=?, slot_dur=?, breaks=?, phone=?, address=?, public_booking=?, auto_confirm_public=?
                           WHERE id=?""",
                        (name, json.dumps(work_days), hour_start, hour_end, slot_dur, json.dumps(breaks), phone, address, pub, auto_c, aid),
                    )
                return self._send_json({'ok': True, 'name': name})

            m = re.match(r'^/api/agendas/([^/]+)/clients/(\d+)$', path)
            if m:
                aid, cid = m.group(1), int(m.group(2))
                name = str(body.get('name', '')).strip()[:80]
                phone = str(body.get('phone', '')).strip()[:40]
                email = str(body.get('email', '')).strip().lower()[:80]
                notes = str(body.get('notes', '')).strip()[:300]
                if not name:
                    return self._send_json({'error': 'Nombre requerido.'}, 400)
                with ctx.db.connect() as conn:
                    if not self._get_authorized_agenda(conn, aid, u):
                        return self._send_json({'error': 'Agenda no encontrada.'}, 404)
                    conn.execute(
                        'UPDATE clients SET name=?, phone=?, email=?, notes=? WHERE id=? AND agenda_id=?',
                        (name, phone, email, notes, cid, aid),
                    )
                return self._send_json({'ok': True})

            m = re.match(r'^/api/agendas/([^/]+)/appointments/(\d+)$', path)
            if m:
                aid, apt_id = m.group(1), int(m.group(2))
                client_name = str(body.get('client', '')).strip()[:80]
                phone = str(body.get('phone', '')).strip()[:40]
                email = str(body.get('email', '')).strip().lower()[:80]
                date_str = str(body.get('date', '')).strip()
                time_str = str(body.get('time', '')).strip()
                svc_name = str(body.get('service', '')).strip()[:60]
                notes = str(body.get('notes', '')).strip()[:300]
                status = str(body.get('status', 'confirmed')).strip()

                if not client_name or not date_str or not time_str:
                    return self._send_json({'error': 'Cliente, fecha y hora son obligatorios.'}, 400)
                with ctx.db.connect() as conn:
                    ag = self._get_authorized_agenda(conn, aid, u)
                    if not ag:
                        return self._send_json({'error': 'Agenda no encontrada.'}, 404)
                    prev = conn.execute('SELECT * FROM appointments WHERE id = ? AND agenda_id = ?', (apt_id, aid)).fetchone()
                    if not prev:
                        return self._send_json({'error': 'Cita no encontrada.'}, 404)
                    svc = conn.execute('SELECT * FROM services WHERE agenda_id = ? AND name = ?', (aid, svc_name)).fetchone()
                    dur = int(body.get('duration') or (svc['dur'] if svc else prev['duration']))
                    price_num = float(svc['price_num']) if svc else prev['service_price']
                    existing = [dict(r) for r in conn.execute('SELECT * FROM appointments WHERE agenda_id = ? AND date = ?', (aid, date_str)).fetchall()]
                    rescheduled = (prev['date'] != date_str or prev['time'] != time_str)
                    errs = validate_appointment(
                        dict(ag), existing, date_str, time_str, dur,
                        status=status, exclude_apt_id=apt_id, allow_past=not rescheduled,
                    )
                    if errs:
                        return self._send_json({'error': errs[0], 'errors': errs}, 409)
                    cid = ctx.db.upsert_client(conn, aid, client_name, phone, email)
                    conn.execute(
                        """UPDATE appointments
                           SET client_id=?, client_name=?, client_phone=?, client_email=?, date=?, time=?, duration=?,
                               service_name=?, service_price=?, notes=?, status=?
                           WHERE id=? AND agenda_id=?""",
                        (cid, client_name, phone, email, date_str, time_str, dur, svc_name, price_num, notes, status, apt_id, aid),
                    )
                if email and (rescheduled or prev['status'] != status):
                    kind = 'cancelled' if status == 'cancelled' else ('rescheduled' if rescheduled else 'confirmed')
                    try:
                        ctx.mail.send_appointment_notice(
                            email, ag['name'], client_name, date_str, time_str, svc_name, status,
                            kind=kind, address=ag['address'], phone=ag['phone'],
                        )
                    except Exception:
                        pass
                return self._send_json({'ok': True})

            return self._send_json({'error': 'Ruta no encontrada.'}, 404)

        # ──────────────────── DELETE ROUTES ────────────────────
        def _route_delete(self, path: str, body: dict):
            u = self._current_user()
            if not u:
                return self._send_json({'error': 'Sesión requerida.'}, 401)

            if path == '/api/account/email':
                pw = str(body.get('password', ''))
                if u['email_ok'] and not verify_password(pw, u['salt'], u['hash']):
                    return self._send_json({'error': 'Escribe tu contraseña actual para quitar el correo'}, 400)
                with ctx.db.connect() as conn:
                    conn.execute("UPDATE users SET email = '', email_ok = 0 WHERE id = ?", (u['id'],))
                    conn.execute('DELETE FROM otc_codes WHERE user_id = ?', (u['id'],))
                    ctx.db.add_log('Correo eliminado de la cuenta', u['user'], conn)
                return self._send_json({'message': 'Correo eliminado.'})

            m = re.match(r'^/api/admin/users/([^/]+)$', path)
            if m:
                if u['role'] != 'admin':
                    return self._send_json({'error': 'Solo administradores.'}, 403)
                tid = m.group(1)
                if tid == u['id']:
                    return self._send_json({'error': 'No puedes eliminar tu propia cuenta.'}, 400)
                with ctx.db.connect() as conn:
                    target = conn.execute('SELECT * FROM users WHERE id = ?', (tid,)).fetchone()
                    if not target:
                        return self._send_json({'error': 'Usuario no encontrado.'}, 404)
                    conn.execute('DELETE FROM users WHERE id = ?', (tid,))
                    ctx.db.add_log(f'Usuario eliminado: {target["user"]}', u['user'], conn)
                return self._send_json({'ok': True})

            m = re.match(r'^/api/agendas/([^/]+)$', path)
            if m:
                aid = m.group(1)
                with ctx.db.connect() as conn:
                    ag = self._get_authorized_agenda(conn, aid, u)
                    if not ag:
                        return self._send_json({'error': 'Agenda no encontrada.'}, 404)
                    conn.execute('DELETE FROM agendas WHERE id = ?', (aid,))
                    ctx.db.add_log(f'Agenda eliminada: {ag["name"]}', u['user'], conn)
                return self._send_json({'ok': True})

            m = re.match(r'^/api/agendas/([^/]+)/services/(\d+)$', path)
            if m:
                aid, sid = m.group(1), int(m.group(2))
                with ctx.db.connect() as conn:
                    if not self._get_authorized_agenda(conn, aid, u):
                        return self._send_json({'error': 'Agenda no encontrada.'}, 404)
                    conn.execute('DELETE FROM services WHERE id = ? AND agenda_id = ?', (sid, aid))
                return self._send_json({'ok': True})

            m = re.match(r'^/api/agendas/([^/]+)/clients/(\d+)$', path)
            if m:
                aid, cid = m.group(1), int(m.group(2))
                with ctx.db.connect() as conn:
                    if not self._get_authorized_agenda(conn, aid, u):
                        return self._send_json({'error': 'Agenda no encontrada.'}, 404)
                    conn.execute('DELETE FROM clients WHERE id = ? AND agenda_id = ?', (cid, aid))
                return self._send_json({'ok': True})

            m = re.match(r'^/api/agendas/([^/]+)/appointments/(\d+)$', path)
            if m:
                aid, apt_id = m.group(1), int(m.group(2))
                with ctx.db.connect() as conn:
                    if not self._get_authorized_agenda(conn, aid, u):
                        return self._send_json({'error': 'Agenda no encontrada.'}, 404)
                    conn.execute('DELETE FROM appointments WHERE id = ? AND agenda_id = ?', (apt_id, aid))
                return self._send_json({'ok': True})

            return self._send_json({'error': 'Ruta no encontrada.'}, 404)

    return Handler


def create_server(config: dict) -> tuple[ThreadingHTTPServer, AppContext]:
    ctx = AppContext(config)
    server = ThreadingHTTPServer((config['HOST'], config['PORT']), make_handler(ctx))
    return server, ctx
