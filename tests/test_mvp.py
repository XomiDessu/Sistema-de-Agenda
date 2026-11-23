"""Suite integral de pruebas automatizadas para Agenda de Citas MVP.
Cubre:
  1. Seguridad, autenticación, sesiones, CSRF, 2FA, bloqueo y rate limiting.
  2. Cuentas, perfil, verificación OTC, recuperación por correo y códigos, administración y SMTP/Demo.
  3. Agendas, horarios, descansos, servicios y reglas de validación de citas.
  4. Portal público, catálogo e historial de clientes, recordatorios, reportes y exportación CSV/.ICS.
"""
import json
import os
import re
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.api import create_server
from backend.scheduling import get_available_slots, validate_appointment
from backend.security import (
    _totp_at,
    check_totp,
    generate_totp_secret,
    hash_password,
    pw_ok,
    verify_password,
)


def next_workday_str(days_ahead: int = 3) -> str:
    d = datetime.now() + timedelta(days=days_ahead)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d.strftime('%Y-%m-%d')


def next_weekend_str(days_ahead: int = 2) -> str:
    d = datetime.now() + timedelta(days=days_ahead)
    while d.weekday() < 5:
        d += timedelta(days=1)
    return d.strftime('%Y-%m-%d')


class ApiClient:
    """Cliente HTTP con cookies HttpOnly por sesión y cierre limpio de respuestas."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.jar = CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.jar))

    def request(self, method: str, path: str, body=None, csrf: bool = True):
        headers = {}
        if csrf:
            headers['X-Requested-With'] = 'XMLHttpRequest'
        data = None
        if body is not None:
            data = json.dumps(body).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        req = Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=10) as resp:
                raw = resp.read()
                ctype = resp.headers.get('Content-Type', '')
                parsed = (
                    json.loads(raw.decode('utf-8'))
                    if 'application/json' in ctype
                    else raw.decode('utf-8', errors='replace')
                )
                return resp.status, parsed, resp.headers
        except HTTPError as e:
            raw = e.read()
            hdrs = e.headers
            code = e.code
            e.close()
            try:
                parsed = json.loads(raw.decode('utf-8'))
            except Exception:
                parsed = raw.decode('utf-8', errors='replace')
            return code, parsed, hdrs


class BaseServerTestCase(unittest.TestCase):
    setup_token = 'tok-inicial-seguro-2026'
    extra_config: dict = {}

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, 'test_agenda.db')
        cfg = {
            'HOST': '127.0.0.1',
            'PORT': 0,
            'DB_PATH': self.db_path,
            'PUBLIC_DIR': str(ROOT_DIR / 'public'),
            'APP_NAME': 'Agenda MVP Test',
            'COOKIE_SECURE': False,
            'ADMIN_USER': '',
            'ADMIN_PASSWORD': '',
            'SETUP_TOKEN': self.setup_token,
            'QUIET_LOGS': True,
        }
        cfg.update(self.extra_config)
        self.server, self.ctx = create_server(cfg)
        port = self.server.server_address[1]
        self.base_url = f'http://127.0.0.1:{port}'
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.tmpdir.cleanup()

    def register_admin(self, client: ApiClient, user='admin1', email='admin@test.com', pw='Password123'):
        st, body, hdrs = client.request('POST', '/api/auth/register', {
            'user': user, 'name': 'Admin Principal', 'email': email,
            'password': pw, 'setupToken': self.setup_token,
        })
        self.assertEqual(st, 201)
        return body['user'], hdrs


class Test1SecurityUnit(unittest.TestCase):
    """Pruebas unitarias de primitivas criptográficas, política de contraseñas y TOTP."""

    def test_password_policy_and_pbkdf2(self):
        self.assertFalse(pw_ok('corta1A'))
        self.assertFalse(pw_ok('sinmayusculas1'))
        self.assertFalse(pw_ok('SINMINUSCULAS1'))
        self.assertFalse(pw_ok('SinNumerosAqui'))
        self.assertTrue(pw_ok('Segura12345'))
        salt = '0123456789abcdef0123456789abcdef'
        h = hash_password('Segura12345', salt)
        self.assertTrue(verify_password('Segura12345', salt, h))
        self.assertFalse(verify_password('OtraClave123', salt, h))

    def test_totp_rfc6238_window(self):
        sec = generate_totp_secret()
        now = time.time()
        step = int(now // 30)
        self.assertTrue(check_totp(sec, _totp_at(sec, step), now=now))
        self.assertTrue(check_totp(sec, _totp_at(sec, step - 1), now=now))
        self.assertTrue(check_totp(sec, _totp_at(sec, step + 1), now=now))
        self.assertFalse(check_totp(sec, _totp_at(sec, step - 3), now=now))

    def test_scheduling_engine_rules(self):
        agenda = {
            'work_days': '[1,2,3,4,5]',
            'hour_start': '09:00',
            'hour_end': '18:00',
            'slot_dur': 60,
            'breaks': '[{"start":"13:00","end":"14:00","label":"Comida"}]',
        }
        wday = next_workday_str(5)
        wknd = next_weekend_str(2)
        past = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')

        self.assertTrue(validate_appointment(agenda, [], past, '10:00', 60))
        self.assertTrue(validate_appointment(agenda, [], wknd, '10:00', 60))
        self.assertTrue(validate_appointment(agenda, [], wday, '08:00', 60))
        self.assertTrue(validate_appointment(agenda, [], wday, '17:30', 60))
        self.assertTrue(validate_appointment(agenda, [], wday, '12:30', 60))

        existing = [{'id': 1, 'date': wday, 'time': '10:00', 'duration': 90, 'status': 'confirmed'}]
        self.assertTrue(validate_appointment(agenda, existing, wday, '11:00', 30))
        self.assertEqual(validate_appointment(agenda, existing, wday, '11:30', 60), [])

        slots = get_available_slots(agenda, existing, wday, 60)
        self.assertIn('09:00', slots)
        self.assertNotIn('10:00', slots)
        self.assertNotIn('11:00', slots)
        self.assertNotIn('13:00', slots)
        self.assertIn('14:00', slots)


class Test2SecurityAndAuthIntegration(BaseServerTestCase):
    """Pruebas dinámicas de seguridad: aprovisionamiento, sesiones, CSRF, cabeceras, 2FA y bloqueos."""

    def test_provisioning_csrf_headers_and_lockout(self):
        admin = ApiClient(self.base_url)
        user2 = ApiClient(self.base_url)

        # Cabeceras de seguridad HTTP en respuestas
        st, _, hdrs = admin.request('GET', '/api/health')
        self.assertEqual(st, 200)
        self.assertEqual(hdrs.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(hdrs.get('X-Frame-Options'), 'DENY')

        # Rechaza alta de primer administrador sin token válido
        st, _, _ = admin.request('POST', '/api/auth/register', {
            'user': 'intruso', 'name': 'Intruso', 'password': 'Password123', 'setupToken': 'invalido',
        })
        self.assertEqual(st, 403)

        # Alta exitosa y cookie HttpOnly
        u, hdrs = self.register_admin(admin)
        self.assertEqual(u['role'], 'admin')
        self.assertIn('HttpOnly', hdrs.get('Set-Cookie', ''))
        self.assertIn('SameSite=Lax', hdrs.get('Set-Cookie', ''))

        # Protección CSRF en POST sin JSON ni X-Requested-With
        st, _, _ = admin.request('POST', '/api/agendas', body=None, csrf=False)
        self.assertEqual(st, 403)

        # Segundo usuario tiene rol 'usuario' y no puede acceder a rutas de admin
        st, r2, _ = user2.request('POST', '/api/auth/register', {
            'user': 'operador', 'name': 'Operador', 'password': 'Password123',
        })
        self.assertEqual(st, 201)
        self.assertEqual(r2['user']['role'], 'usuario')
        st, _, _ = user2.request('GET', '/api/admin/users')
        self.assertEqual(st, 403)
        st, _, _ = user2.request('GET', '/api/admin/mail')
        self.assertEqual(st, 403)

        # Bloqueo tras 5 intentos fallidos de login
        attacker = ApiClient(self.base_url)
        for _ in range(5):
            st, _, _ = attacker.request('POST', '/api/auth/login', {'user': 'operador', 'password': 'WrongPassword1'})
            self.assertEqual(st, 401)
        st, locked, _ = attacker.request('POST', '/api/auth/login', {'user': 'operador', 'password': 'Password123'})
        self.assertEqual(st, 423)
        self.assertIn('bloqueada', locked['error'].lower())

    def test_2fa_backup_code_and_session_expiry(self):
        admin = ApiClient(self.base_url)
        self.register_admin(admin)

        # Activar 2FA
        st, tfa, _ = admin.request('POST', '/api/account/2fa/setup', {})
        self.assertEqual(st, 200)
        code = _totp_at(tfa['secret'], int(time.time() // 30))
        st, conf, _ = admin.request('POST', '/api/account/2fa/confirm', {'code': code})
        self.assertEqual(st, 200)
        backup_code = conf['backupCodes'][0]

        # Logout y login usando código de respaldo de un solo uso
        admin.request('POST', '/api/auth/logout', {})
        st, lres, _ = admin.request('POST', '/api/auth/login', {'user': 'admin1', 'password': 'Password123'})
        self.assertTrue(lres.get('mfaRequired'))
        st, mres, _ = admin.request('POST', '/api/auth/mfa', {'mfaToken': lres['mfaToken'], 'code': backup_code})
        self.assertEqual(st, 200)

        # Reutilizar el mismo código de respaldo debe fallar
        admin.request('POST', '/api/auth/logout', {})
        st, lres2, _ = admin.request('POST', '/api/auth/login', {'user': 'admin1', 'password': 'Password123'})
        st, _, _ = admin.request('POST', '/api/auth/mfa', {'mfaToken': lres2['mfaToken'], 'code': backup_code})
        self.assertEqual(st, 401)

        # Iniciar sesión con TOTP y simular expiración de sesión en servidor
        code2 = _totp_at(tfa['secret'], int(time.time() // 30))
        st, _, _ = admin.request('POST', '/api/auth/mfa', {'mfaToken': lres2['mfaToken'], 'code': code2})
        self.assertEqual(st, 200)
        with self.ctx.db.connect() as conn:
            conn.execute('UPDATE sessions SET expires_at = ?', (time.time() - 10,))
        st, _, _ = admin.request('GET', '/api/agendas')
        self.assertEqual(st, 401)


class Test3AccountsRecoveryAdminAndMail(BaseServerTestCase):
    """Pruebas de cuentas, perfil, verificación de correo, recuperación, administración y correo."""

    def test_profile_email_recovery_and_admin_controls(self):
        admin = ApiClient(self.base_url)
        user2 = ApiClient(self.base_url)
        anon = ApiClient(self.base_url)

        u_adm, _ = self.register_admin(admin, 'admin1', 'admin@test.com', 'Password123')
        st, r2, _ = user2.request('POST', '/api/auth/register', {
            'user': 'user2', 'name': 'Usuario Dos', 'password': 'Password123',
        })
        self.assertEqual(st, 201)
        u2_id = r2['user']['id']

        # Perfil: actualizar nombre
        st, p_res, _ = admin.request('PUT', '/api/account/profile', {'name': 'Admin Actualizado'})
        self.assertEqual(st, 200)
        self.assertEqual(p_res['name'], 'Admin Actualizado')

        # Verificación de correo con OTC de 6 dígitos
        st, _, _ = admin.request('POST', '/api/account/email/send', {'email': 'admin@test.com'})
        self.assertEqual(st, 200)
        # Enfriamiento de 60s al reenviar inmediatamente
        st, _, _ = admin.request('POST', '/api/account/email/send', {'email': 'admin@test.com'})
        self.assertEqual(st, 429)

        st, outbox, _ = admin.request('GET', '/api/outbox')
        code = re.search(r'\b(\d{6})\b', outbox['messages'][0]['text']).group(1)
        st, _, _ = admin.request('POST', '/api/account/email/verify', {'code': code})
        self.assertEqual(st, 200)

        # Otro usuario no puede usar el mismo correo verificado
        st, _, _ = user2.request('POST', '/api/account/email/send', {'email': 'admin@test.com'})
        self.assertEqual(st, 409)

        # Generar 8 códigos de recuperación y usar uno para restablecer contraseña
        st, rc_res, _ = admin.request('POST', '/api/account/recovery-codes', {'password': 'Password123'})
        self.assertEqual(st, 200)
        self.assertEqual(len(rc_res['codes']), 8)
        one_code = rc_res['codes'][0]

        st, rec_ok, _ = anon.request('POST', '/api/auth/recover', {
            'user': 'admin1', 'code': one_code, 'password': 'NuevaPassword123',
        })
        self.assertEqual(st, 200)

        # Login con nueva contraseña
        st, _, _ = admin.request('POST', '/api/auth/login', {'user': 'admin1', 'password': 'NuevaPassword123'})
        self.assertEqual(st, 200)

        # Recuperación por correo: respuesta genérica no revela si existe usuario
        st, fg1, _ = anon.request('POST', '/api/auth/forgot', {'identifier': 'no_existe_xyz'})
        st, fg2, _ = anon.request('POST', '/api/auth/forgot', {'identifier': 'admin1'})
        self.assertEqual(fg1['message'], fg2['message'])

        st, outbox2, _ = admin.request('GET', '/api/outbox')
        reset_code = re.search(r'\b(\d{6})\b', outbox2['messages'][0]['text']).group(1)
        st, _, _ = anon.request('POST', '/api/auth/reset', {
            'identifier': 'admin1', 'code': reset_code, 'password': 'FinalPassword123',
        })
        self.assertEqual(st, 200)
        st, _, _ = admin.request('POST', '/api/auth/login', {'user': 'admin1', 'password': 'FinalPassword123'})
        self.assertEqual(st, 200)

        # Protección del último administrador y autoeliminación prohibida
        st, _, _ = admin.request('PUT', f"/api/admin/users/{u_adm['id']}", {'role': 'usuario'})
        self.assertEqual(st, 400)
        st, _, _ = admin.request('DELETE', f"/api/admin/users/{u_adm['id']}")
        self.assertEqual(st, 400)

        # Desactivar y eliminar a user2 + bitácora registrada
        st, _, _ = admin.request('PUT', f'/api/admin/users/{u2_id}', {'active': False})
        self.assertEqual(st, 200)
        st, _, _ = user2.request('GET', '/api/agendas')
        self.assertEqual(st, 401)
        st, _, _ = admin.request('DELETE', f'/api/admin/users/{u2_id}')
        self.assertEqual(st, 200)
        st, adm_data, _ = admin.request('GET', '/api/admin/users')
        self.assertEqual(st, 200)
        self.assertTrue(len(adm_data['log']) >= 5)

        # Correo: prueba en modo demo y configuración SMTP bloqueando bandeja demo
        st, mtest, _ = admin.request('POST', '/api/admin/mail/test', {})
        self.assertEqual(st, 200)
        self.assertEqual(mtest['mode'], 'demo')

        st, _, _ = admin.request('PUT', '/api/admin/mail', {
            'mode': 'smtp', 'fromName': 'Mi Negocio', 'smtpHost': 'smtp.gmail.com',
            'smtpPort': 587, 'smtpUser': 'negocio@gmail.com', 'smtpPass': 'app-pass-demo', 'smtpTls': True,
        })
        self.assertEqual(st, 200)
        # En modo SMTP la bandeja demo queda bloqueada (403)
        st, _, _ = admin.request('GET', '/api/outbox')
        self.assertEqual(st, 403)


class Test4AgendasPortalClientsReports(BaseServerTestCase):
    """Pruebas de agendas, servicios, citas, portal público, clientes, recordatorios y exportaciones."""

    def test_full_business_operations(self):
        admin = ApiClient(self.base_url)
        user2 = ApiClient(self.base_url)
        anon = ApiClient(self.base_url)

        self.register_admin(admin)
        user2.request('POST', '/api/auth/register', {'user': 'otro', 'name': 'Otro', 'password': 'Password123'})

        # Crear segunda agenda y verificar aislamiento entre usuarios
        st, ag2, _ = admin.request('POST', '/api/agendas', {'name': 'Sucursal Norte'})
        self.assertEqual(st, 201)
        aid, slug = ag2['id'], ag2['slug']
        st, _, _ = user2.request('GET', f'/api/agendas/{aid}')
        self.assertEqual(st, 404)

        # Configurar horarios, descansos y agregar servicio
        st, _, _ = admin.request('PUT', f'/api/agendas/{aid}', {
            'name': 'Sucursal Norte', 'workDays': [1, 2, 3, 4, 5], 'hourStart': '09:00', 'hourEnd': '18:00',
            'slotDur': 60, 'breaks': [{'start': '13:00', 'end': '14:00', 'label': 'Comida'}],
            'phone': '3300001111', 'address': 'Av. Vallarta 100', 'publicBooking': True, 'autoConfirmPublic': False,
        })
        self.assertEqual(st, 200)
        st, svc, _ = admin.request('POST', f'/api/agendas/{aid}/services', {
            'name': 'Terapia Especial', 'dur': 90, 'price': '$1200',
        })
        self.assertEqual(st, 201)

        # Citas: crear válida, rechazar traslape, descanso y día no laborable
        wday = next_workday_str(4)
        wknd = next_weekend_str(2)
        st, apt1, _ = admin.request('POST', f'/api/agendas/{aid}/appointments', {
            'client': 'Ana López', 'phone': '3312345678', 'email': 'ana@cliente.com',
            'date': wday, 'time': '10:00', 'service': 'Terapia Especial', 'status': 'confirmed',
        })
        self.assertEqual(st, 201)
        self.assertEqual(apt1['duration'], 90)

        st, _, _ = admin.request('POST', f'/api/agendas/{aid}/appointments', {
            'client': 'Choque', 'date': wday, 'time': '11:00', 'service': 'Consulta general',
        })
        self.assertEqual(st, 409)
        st, _, _ = admin.request('POST', f'/api/agendas/{aid}/appointments', {
            'client': 'Descanso', 'date': wday, 'time': '13:00', 'service': 'Consulta general',
        })
        self.assertEqual(st, 409)
        st, _, _ = admin.request('POST', f'/api/agendas/{aid}/appointments', {
            'client': 'FinSemana', 'date': wknd, 'time': '10:00', 'service': 'Consulta general',
        })
        self.assertEqual(st, 409)

        # Portal público: HTML, metadata, slots disponibles y reserva
        st, html_pub, _ = anon.request('GET', f'/reservar/{slug}')
        self.assertEqual(st, 200)
        self.assertIn('booking-root', html_pub)

        st, pub_info, _ = anon.request('GET', f'/api/public/agendas/{slug}')
        self.assertEqual(st, 200)
        self.assertEqual(pub_info['name'], 'Sucursal Norte')

        st, slots_res, _ = anon.request('GET', f"/api/public/agendas/{slug}/slots?date={wday}&service_id={svc['id']}")
        self.assertEqual(st, 200)
        self.assertNotIn('10:00', slots_res['slots'])
        self.assertIn('14:00', slots_res['slots'])

        st, booked, _ = anon.request('POST', f'/api/public/agendas/{slug}/book', {
            'serviceId': svc['id'], 'date': wday, 'time': '14:00',
            'client': 'Carlos Público', 'phone': '3399887766', 'email': 'carlos@publico.com',
        })
        self.assertEqual(st, 201)
        self.assertEqual(booked['status'], 'pending')

        # Doble reserva pública rechazada
        st, _, _ = anon.request('POST', f'/api/public/agendas/{slug}/book', {
            'serviceId': svc['id'], 'date': wday, 'time': '14:00', 'client': 'Duplicado',
        })
        self.assertEqual(st, 409)

        # Cancelar cita pública libera el horario nuevamente
        st, _, _ = admin.request('PUT', f"/api/agendas/{aid}/appointments/{booked['id']}", {
            'client': 'Carlos Público', 'phone': '3399887766', 'email': 'carlos@publico.com',
            'date': wday, 'time': '14:00', 'service': 'Terapia Especial', 'status': 'cancelled',
        })
        self.assertEqual(st, 200)
        st, slots_after, _ = anon.request('GET', f"/api/public/agendas/{slug}/slots?date={wday}&service_id={svc['id']}")
        self.assertIn('14:00', slots_after['slots'])

        # Catálogo e historial de clientes
        st, cl_res, _ = admin.request('GET', f'/api/agendas/{aid}/clients')
        self.assertEqual(st, 200)
        self.assertEqual(len(cl_res['clients']), 2)
        ana_id = next(c['id'] for c in cl_res['clients'] if c['name'] == 'Ana López')
        st, hist, _ = admin.request('GET', f'/api/agendas/{aid}/clients/{ana_id}/history')
        self.assertEqual(st, 200)
        self.assertEqual(len(hist['appointments']), 1)

        # Recordatorio individual + reportes + exportaciones CSV e ICS
        st, rem, _ = admin.request('POST', f"/api/agendas/{aid}/appointments/{apt1['id']}/remind", {})
        self.assertEqual(st, 200)
        self.assertIn('ana@cliente.com', rem['message'])

        st, rep, _ = admin.request('GET', f'/api/agendas/{aid}/reports')
        self.assertEqual(st, 200)
        self.assertEqual(rep['totals']['total'], 2)
        self.assertEqual(rep['totals']['cancelled'], 1)
        self.assertEqual(rep['cancelRate'], 50.0)
        self.assertEqual(rep['revenueConfirmed'], 1200.0)

        st, csv_text, _ = admin.request('GET', f'/api/agendas/{aid}/export.csv')
        self.assertEqual(st, 200)
        self.assertIn('Ana López', csv_text)
        self.assertIn('Terapia Especial', csv_text)

        st, ics_text, _ = admin.request('GET', f'/api/agendas/{aid}/export.ics')
        self.assertEqual(st, 200)
        self.assertIn('BEGIN:VCALENDAR', ics_text)
        self.assertIn('Ana López - Terapia Especial', ics_text)
        self.assertNotIn('Carlos Público', ics_text)  # canceladas no se exportan al calendario

        # Desactivar reservas públicas bloquea el portal (404)
        st, _, _ = admin.request('PUT', f'/api/agendas/{aid}', {'publicBooking': False})
        self.assertEqual(st, 200)
        st, _, _ = anon.request('GET', f'/api/public/agendas/{slug}')
        self.assertEqual(st, 404)


if __name__ == '__main__':
    unittest.main()
