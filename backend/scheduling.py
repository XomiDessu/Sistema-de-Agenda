"""Lógica de negocio de citas: validación de horarios, descansos, fechas pasadas y prevención de traslapes."""
import json
from datetime import datetime, date as date_cls


def time_to_min(hhmm: str) -> int:
    parts = str(hhmm or '').split(':')
    if len(parts) != 2:
        raise ValueError('Formato de hora inválido (usa HH:MM)')
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError('Hora fuera de rango')
    return h * 60 + m


def min_to_time(minutes: int) -> str:
    return f'{minutes // 60:02d}:{minutes % 60:02d}'


def js_weekday(d: date_cls) -> int:
    """Devuelve día de la semana estilo JS: 0=Dom, 1=Lun ... 6=Sáb."""
    return (d.weekday() + 1) % 7


def parse_date(date_str: str) -> date_cls:
    try:
        return datetime.strptime(str(date_str), '%Y-%m-%d').date()
    except ValueError as exc:
        raise ValueError('Formato de fecha inválido (usa YYYY-MM-DD)') from exc


def ranges_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


def validate_appointment(
    agenda: dict,
    existing_appointments: list[dict],
    date_str: str,
    time_str: str,
    duration: int,
    status: str = 'confirmed',
    exclude_apt_id: int | None = None,
    allow_past: bool = False,
    now_dt: datetime | None = None,
) -> list[str]:
    """Valida reglas de negocio para una cita. Devuelve lista de errores (vacía si es válida)."""
    errors: list[str] = []
    try:
        apt_date = parse_date(date_str)
    except ValueError as e:
        return [str(e)]
    try:
        start_min = time_to_min(time_str)
    except ValueError as e:
        return [str(e)]

    dur = int(duration or agenda.get('slot_dur') or 60)
    if dur < 5 or dur > 480:
        return ['La duración del servicio debe estar entre 5 y 480 minutos.']
    end_min = start_min + dur

    if status in ('cancelled', 'completed'):
        return []

    now = now_dt or datetime.now()
    apt_dt = datetime(apt_date.year, apt_date.month, apt_date.day, start_min // 60, start_min % 60)
    if not allow_past and apt_dt < now:
        errors.append('No se pueden agendar citas en fechas u horas pasadas.')

    work_days = json.loads(agenda['work_days']) if isinstance(agenda['work_days'], str) else agenda['work_days']
    if js_weekday(apt_date) not in work_days:
        errors.append('La fecha seleccionada corresponde a un día no laborable.')

    open_min = time_to_min(agenda['hour_start'])
    close_min = time_to_min(agenda['hour_end'])
    if start_min < open_min or end_min > close_min:
        errors.append(
            f"La cita ({time_str}–{min_to_time(end_min)}) está fuera del horario de atención ({agenda['hour_start']}–{agenda['hour_end']})."
        )

    breaks = json.loads(agenda['breaks']) if isinstance(agenda['breaks'], str) else agenda['breaks']
    for br in breaks:
        bs, be = time_to_min(br['start']), time_to_min(br['end'])
        if ranges_overlap(start_min, end_min, bs, be):
            lbl = br.get("label", "Descanso")
            errors.append(f"El horario se cruza con el descanso \"{lbl}\" ({br['start']}–{br['end']}).")
            break

    for apt in existing_appointments:
        if exclude_apt_id is not None and apt['id'] == exclude_apt_id:
            continue
        if apt['status'] == 'cancelled':
            continue
        if apt['date'] != date_str:
            continue
        other_start = time_to_min(apt['time'])
        other_dur = int(apt.get('duration') or agenda.get('slot_dur') or 60)
        other_end = other_start + other_dur
        if ranges_overlap(start_min, end_min, other_start, other_end):
            errors.append(
                f"El horario se traslapa con otra cita existente ({apt['time']}–{min_to_time(other_end)})."
            )
            break

    return errors


def get_available_slots(
    agenda: dict,
    existing_appointments: list[dict],
    date_str: str,
    service_dur: int | None = None,
    now_dt: datetime | None = None,
) -> list[str]:
    """Calcula los horarios disponibles exactos para una fecha y duración de servicio."""
    try:
        apt_date = parse_date(date_str)
    except ValueError:
        return []

    work_days = json.loads(agenda['work_days']) if isinstance(agenda['work_days'], str) else agenda['work_days']
    if js_weekday(apt_date) not in work_days:
        return []

    step = int(agenda.get('slot_dur') or 30)
    dur = int(service_dur or step)
    open_min = time_to_min(agenda['hour_start'])
    close_min = time_to_min(agenda['hour_end'])
    now = now_dt or datetime.now()

    slots = []
    cur = open_min
    while cur + dur <= close_min:
        t_str = min_to_time(cur)
        errs = validate_appointment(
            agenda, existing_appointments, date_str, t_str, dur,
            status='confirmed', allow_past=False, now_dt=now,
        )
        if not errs:
            slots.append(t_str)
        cur += step
    return slots
