"""Reportes de negocio y exportación a CSV e iCalendar (.ics)."""
import csv
import io
from collections import defaultdict
from datetime import datetime, timedelta, timezone


def build_report(appointments: list[dict], date_from: str = '', date_to: str = '') -> dict:
    filtered = []
    for a in appointments:
        if date_from and a['date'] < date_from:
            continue
        if date_to and a['date'] > date_to:
            continue
        filtered.append(a)

    totals = {'total': len(filtered), 'confirmed': 0, 'pending': 0, 'cancelled': 0, 'completed': 0}
    revenue_confirmed = 0.0
    revenue_pending = 0.0
    clients_set = set()
    by_service = defaultdict(lambda: {'service': '', 'count': 0, 'cancelled': 0, 'revenue': 0.0})

    for a in filtered:
        st = a['status']
        if st in totals:
            totals[st] += 1
        price = float(a.get('service_price') or 0.0)
        svc = a.get('service_name') or 'Sin servicio'
        entry = by_service[svc]
        entry['service'] = svc
        entry['count'] += 1
        if st == 'cancelled':
            entry['cancelled'] += 1
        else:
            if st in ('confirmed', 'completed'):
                revenue_confirmed += price
                entry['revenue'] += price
            elif st == 'pending':
                revenue_pending += price
        clients_set.add((a.get('client_name') or '').strip().lower())

    cancel_rate = round((totals['cancelled'] / totals['total']) * 100, 1) if totals['total'] else 0.0
    services_list = sorted(by_service.values(), key=lambda x: (-x['count'], x['service']))

    return {
        'dateFrom': date_from,
        'dateTo': date_to,
        'totals': totals,
        'uniqueClients': len([c for c in clients_set if c]),
        'revenueConfirmed': round(revenue_confirmed, 2),
        'revenuePending': round(revenue_pending, 2),
        'cancelRate': cancel_rate,
        'byService': services_list,
    }


def export_csv(appointments: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['ID', 'Fecha', 'Hora', 'Duración (min)', 'Cliente', 'Teléfono', 'Correo', 'Servicio', 'Precio', 'Estado', 'Origen', 'Notas'])
    for a in sorted(appointments, key=lambda x: (x['date'], x['time'])):
        writer.writerow([
            a['id'], a['date'], a['time'], a['duration'],
            a['client_name'], a['client_phone'], a['client_email'],
            a['service_name'], a['service_price'], a['status'], a['source'], a['notes'],
        ])
    return buf.getvalue()


def _ics_escape(text: str) -> str:
    return str(text or '').replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')


def export_ics(agenda_name: str, appointments: list[dict]) -> str:
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Agenda de Citas MVP//ES',
        f'X-WR-CALNAME:{_ics_escape(agenda_name)}',
    ]
    now_utc = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    for a in appointments:
        if a['status'] == 'cancelled':
            continue
        start_dt = datetime.strptime(f"{a['date']} {a['time']}", '%Y-%m-%d %H:%M')
        end_dt = start_dt + timedelta(minutes=int(a.get('duration') or 60))
        summary = f"{a['client_name']} - {a['service_name']}"
        desc = f"Cliente: {a['client_name']}\nTeléfono: {a['client_phone']}\nEstado: {a['status']}\nNotas: {a['notes']}"
        lines.extend([
            'BEGIN:VEVENT',
            f"UID:apt-{a['id']}@agendacitas.local",
            f'DTSTAMP:{now_utc}',
            f"DTSTART:{start_dt.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{end_dt.strftime('%Y%m%dT%H%M%S')}",
            f'SUMMARY:{_ics_escape(summary)}',
            f'DESCRIPTION:{_ics_escape(desc)}',
            'END:VEVENT',
        ])
    lines.append('END:VCALENDAR')
    return '\r\n'.join(lines) + '\r\n'
