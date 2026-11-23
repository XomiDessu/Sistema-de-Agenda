"""Envío de correo en servidor: SMTP real (TLS/SSL) con respaldo en bandeja local de demostración."""
import smtplib
from email.message import EmailMessage

from .db import Database, now_str


class MailService:
    def __init__(self, db: Database, app_name: str = 'Agenda de Citas'):
        self.db = db
        self.app_name = app_name

    def get_config(self) -> dict:
        with self.db.connect() as conn:
            row = conn.execute('SELECT * FROM mail_config WHERE id = 1').fetchone()
            return dict(row) if row else {'mode': 'demo', 'from_name': self.app_name}

    def get_public_config(self) -> dict:
        cfg = self.get_config()
        return {
            'mode': cfg['mode'],
            'fromName': cfg['from_name'],
            'smtpHost': cfg['smtp_host'],
            'smtpPort': cfg['smtp_port'],
            'smtpUser': cfg['smtp_user'],
            'smtpFrom': cfg['smtp_from'],
            'smtpTls': bool(cfg['smtp_tls']),
            'hasPassword': bool(cfg['smtp_pass']),
        }

    def send(self, to_email: str, subject: str, body: str) -> str:
        if not to_email:
            return 'skipped'
        cfg = self.get_config()
        if cfg['mode'] == 'smtp':
            if not cfg['smtp_host'] or not cfg['smtp_user'] or not cfg['smtp_pass']:
                raise RuntimeError('El servidor SMTP no está configurado completamente.')
            msg = EmailMessage()
            from_addr = cfg['smtp_from'] or cfg['smtp_user']
            from_name = cfg['from_name'] or self.app_name
            msg['From'] = f'{from_name} <{from_addr}>'
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.set_content(body)

            port = int(cfg['smtp_port'] or 587)
            use_tls = bool(cfg['smtp_tls'])
            if port == 465:
                with smtplib.SMTP_SSL(cfg['smtp_host'], port, timeout=15) as srv:
                    srv.login(cfg['smtp_user'], cfg['smtp_pass'])
                    srv.send_message(msg)
            else:
                with smtplib.SMTP(cfg['smtp_host'], port, timeout=15) as srv:
                    if use_tls:
                        srv.starttls()
                    srv.login(cfg['smtp_user'], cfg['smtp_pass'])
                    srv.send_message(msg)
            return 'sent'

        with self.db.connect() as conn:
            conn.execute(
                'INSERT INTO outbox (created_at, to_email, subject, body) VALUES (?, ?, ?, ?)',
                (now_str(), to_email, subject, body),
            )
            conn.execute(
                'DELETE FROM outbox WHERE id NOT IN (SELECT id FROM outbox ORDER BY id DESC LIMIT 30)'
            )
        return 'demo'

    def send_verify_code(self, to_email: str, name: str, code: str) -> str:
        return self.send(
            to_email,
            f'Verifica tu correo · {self.app_name}',
            f'Hola {name},\n\nTu código para verificar este correo es: {code}\n'
            f'Vence en 10 minutos. Si no lo solicitaste, ignora este mensaje.',
        )

    def send_reset_code(self, to_email: str, name: str, username: str, code: str) -> str:
        return self.send(
            to_email,
            f'Recuperación de contraseña · {self.app_name}',
            f'Hola {name},\n\nTu código para restablecer la contraseña de "{username}" es: {code}\n'
            f'Vence en 10 minutos. Si no lo solicitaste, ignora este mensaje.',
        )

    def send_appointment_notice(
        self,
        to_email: str,
        biz_name: str,
        client_name: str,
        date_str: str,
        time_str: str,
        service_name: str,
        status: str,
        kind: str = 'confirmed',
        address: str = '',
        phone: str = '',
    ) -> str:
        labels = {
            'created': f'Cita registrada · {biz_name}',
            'confirmed': f'Cita confirmada · {biz_name}',
            'cancelled': f'Cita cancelada · {biz_name}',
            'rescheduled': f'Cita reagendada · {biz_name}',
            'reminder': f'Recordatorio de cita · {biz_name}',
        }
        status_es = {
            'confirmed': 'Confirmada',
            'pending': 'Pendiente de confirmación',
            'cancelled': 'Cancelada',
            'completed': 'Completada',
        }.get(status, status)
        extra = ''
        if address:
            extra += f'Dirección: {address}\n'
        if phone:
            extra += f'Contacto: {phone}\n'
        body = (
            f'Hola {client_name},\n\n'
            f'Detalles de tu cita en {biz_name}:\n'
            f'- Servicio: {service_name}\n'
            f'- Fecha: {date_str}\n'
            f'- Hora: {time_str}\n'
            f'- Estado: {status_es}\n'
            f'{extra}\nGracias por tu preferencia.'
        )
        return self.send(to_email, labels.get(kind, f'Aviso de cita · {biz_name}'), body)
