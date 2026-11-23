"""Capa de base de datos SQLite (WAL, llaves foráneas, migraciones y aprovisionamiento inicial)."""
from contextlib import contextmanager
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from .security import hash_password, pw_ok, random_hex, USER_RE

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    user TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'usuario' CHECK (role IN ('admin', 'usuario')),
    salt TEXT NOT NULL,
    hash TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    fails INTEGER NOT NULL DEFAULT 0,
    lock_until REAL NOT NULL DEFAULT 0,
    totp_secret TEXT,
    totp_on INTEGER NOT NULL DEFAULT 0,
    backup_codes TEXT NOT NULL DEFAULT '[]',
    email TEXT NOT NULL DEFAULT '',
    email_ok INTEGER NOT NULL DEFAULT 0,
    rec_email INTEGER NOT NULL DEFAULT 1,
    rec_codes TEXT NOT NULL DEFAULT '[]',
    timeout_min INTEGER NOT NULL DEFAULT 15,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at REAL NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS mfa_pending (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS otc_codes (
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    purpose TEXT NOT NULL CHECK (purpose IN ('email_verify', 'password_reset')),
    target_email TEXT NOT NULL DEFAULT '',
    salt TEXT NOT NULL,
    hash TEXT NOT NULL,
    expires_at REAL NOT NULL,
    tries INTEGER NOT NULL DEFAULT 0,
    sent_at REAL NOT NULL,
    PRIMARY KEY (user_id, purpose)
);

CREATE TABLE IF NOT EXISTS agendas (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    public_booking INTEGER NOT NULL DEFAULT 1,
    auto_confirm_public INTEGER NOT NULL DEFAULT 0,
    work_days TEXT NOT NULL DEFAULT '[1,2,3,4,5]',
    hour_start TEXT NOT NULL DEFAULT '09:00',
    hour_end TEXT NOT NULL DEFAULT '18:00',
    slot_dur INTEGER NOT NULL DEFAULT 60,
    breaks TEXT NOT NULL DEFAULT '[{"start":"13:00","end":"14:00","label":"Comida"}]',
    phone TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agenda_id TEXT NOT NULL REFERENCES agendas(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    dur INTEGER NOT NULL DEFAULT 60,
    price TEXT NOT NULL DEFAULT '$0',
    price_num REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agenda_id TEXT NOT NULL REFERENCES agendas(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    phone TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agenda_id TEXT NOT NULL REFERENCES agendas(id) ON DELETE CASCADE,
    client_id INTEGER REFERENCES clients(id) ON DELETE SET NULL,
    client_name TEXT NOT NULL,
    client_phone TEXT NOT NULL DEFAULT '',
    client_email TEXT NOT NULL DEFAULT '',
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    duration INTEGER NOT NULL DEFAULT 60,
    service_name TEXT NOT NULL DEFAULT '',
    service_price REAL NOT NULL DEFAULT 0,
    notes TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'pending', 'cancelled', 'completed')),
    source TEXT NOT NULL DEFAULT 'admin' CHECK (source IN ('admin', 'public')),
    reminder_sent INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_apts_agenda_date ON appointments(agenda_id, date);
CREATE INDEX IF NOT EXISTS idx_clients_agenda ON clients(agenda_id);
CREATE INDEX IF NOT EXISTS idx_sessions_exp ON sessions(expires_at);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    username TEXT NOT NULL,
    event TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mail_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    mode TEXT NOT NULL DEFAULT 'demo' CHECK (mode IN ('demo', 'smtp')),
    from_name TEXT NOT NULL DEFAULT 'Agenda de Citas',
    smtp_host TEXT NOT NULL DEFAULT '',
    smtp_port INTEGER NOT NULL DEFAULT 587,
    smtp_user TEXT NOT NULL DEFAULT '',
    smtp_pass TEXT NOT NULL DEFAULT '',
    smtp_from TEXT NOT NULL DEFAULT '',
    smtp_tls INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    to_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL
);
"""


def now_str() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def parse_price(price_str: str) -> float:
    cleaned = re.sub(r'[^0-9.,]', '', str(price_str or '')).replace(',', '')
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


def slugify(text: str) -> str:
    s = re.sub(r'[^a-z0-9]+', '-', str(text or 'negocio').lower()).strip('-')
    return (s[:28] or 'negocio') + '-' + random_hex(3)


class Database:
    def __init__(self, db_path: str, config: dict):
        self.db_path = db_path
        self.config = config
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            row = conn.execute('SELECT id FROM mail_config WHERE id = 1').fetchone()
            if not row:
                mode = 'smtp' if self.config.get('SMTP_HOST') else 'demo'
                conn.execute(
                    """INSERT INTO mail_config (id, mode, from_name, smtp_host, smtp_port, smtp_user, smtp_pass, smtp_from, smtp_tls)
                       VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        mode,
                        self.config.get('APP_NAME', 'Agenda de Citas'),
                        self.config.get('SMTP_HOST', ''),
                        self.config.get('SMTP_PORT', 587),
                        self.config.get('SMTP_USER', ''),
                        self.config.get('SMTP_PASS', ''),
                        self.config.get('SMTP_FROM', '') or self.config.get('SMTP_USER', ''),
                        1 if self.config.get('SMTP_TLS', True) else 0,
                    ),
                )
            self._provision_initial_admin(conn)

    def _provision_initial_admin(self, conn: sqlite3.Connection) -> None:
        user_count = conn.execute('SELECT COUNT(*) AS c FROM users').fetchone()['c']
        if user_count > 0:
            return
        admin_user = self.config.get('ADMIN_USER', '')
        admin_pass = self.config.get('ADMIN_PASSWORD', '')
        admin_name = self.config.get('ADMIN_NAME', 'Administrador') or 'Administrador'
        admin_email = self.config.get('ADMIN_EMAIL', '')

        if admin_user and admin_pass and USER_RE.match(admin_user) and pw_ok(admin_pass):
            uid = random_hex(8)
            salt = random_hex(16)
            pw_hash = hash_password(admin_pass, salt)
            conn.execute(
                """INSERT INTO users (id, user, name, role, salt, hash, active, email, email_ok, created_at)
                   VALUES (?, ?, ?, 'admin', ?, ?, 1, ?, ?, ?)""",
                (uid, admin_user, admin_name[:40], salt, pw_hash, admin_email, 1 if admin_email else 0, now_str()),
            )
            self.create_default_agenda(conn, uid, 'Mi Negocio')
            conn.execute(
                'INSERT INTO audit_log (created_at, username, event) VALUES (?, ?, ?)',
                (now_str(), admin_user, 'Administrador inicial aprovisionado desde variables de entorno'),
            )
        else:
            setup_tok = self.config.get('SETUP_TOKEN') or random_hex(12)
            existing = conn.execute("SELECT value FROM meta WHERE key = 'setup_token'").fetchone()
            if not existing:
                conn.execute("INSERT INTO meta (key, value) VALUES ('setup_token', ?)", (setup_tok,))

    def get_setup_token(self) -> str | None:
        with self.connect() as conn:
            row = conn.execute("SELECT value FROM meta WHERE key = 'setup_token'").fetchone()
            return row['value'] if row else None

    def clear_setup_token(self, conn: sqlite3.Connection) -> None:
        conn.execute("DELETE FROM meta WHERE key = 'setup_token'")

    def create_default_agenda(self, conn: sqlite3.Connection, owner_id: str, name: str = 'Mi Negocio') -> str:
        aid = random_hex(6)
        slug = slugify(name)
        conn.execute(
            """INSERT INTO agendas (id, owner_id, name, slug, public_booking, auto_confirm_public,
               work_days, hour_start, hour_end, slot_dur, breaks, phone, address, created_at)
               VALUES (?, ?, ?, ?, 1, 0, '[1,2,3,4,5]', '09:00', '18:00', 60,
               '[{"start":"13:00","end":"14:00","label":"Comida"}]', '', '', ?)""",
            (aid, owner_id, name[:40], slug, now_str()),
        )
        defaults = [
            ('Consulta general', 60, '$500', 500.0),
            ('Seguimiento', 30, '$300', 300.0),
            ('Procedimiento', 90, '$800', 800.0),
        ]
        conn.executemany(
            'INSERT INTO services (agenda_id, name, dur, price, price_num) VALUES (?, ?, ?, ?, ?)',
            [(aid, n, d, p, pn) for n, d, p, pn in defaults],
        )
        return aid

    def add_log(self, event: str, username: str = '-', conn: sqlite3.Connection | None = None) -> None:
        if conn is not None:
            conn.execute(
                'INSERT INTO audit_log (created_at, username, event) VALUES (?, ?, ?)',
                (now_str(), username or '-', event[:240]),
            )
            return
        with self.connect() as c:
            c.execute(
                'INSERT INTO audit_log (created_at, username, event) VALUES (?, ?, ?)',
                (now_str(), username or '-', event[:240]),
            )

    def upsert_client(
        self,
        conn: sqlite3.Connection,
        agenda_id: str,
        name: str,
        phone: str = '',
        email: str = '',
        notes: str = '',
    ) -> int:
        clean_name = name.strip()[:80]
        clean_phone = phone.strip()[:40]
        clean_email = email.strip().lower()[:80]
        row = None
        if clean_email:
            row = conn.execute(
                'SELECT id FROM clients WHERE agenda_id = ? AND lower(email) = ?',
                (agenda_id, clean_email),
            ).fetchone()
        if not row and clean_phone:
            row = conn.execute(
                'SELECT id FROM clients WHERE agenda_id = ? AND phone = ?',
                (agenda_id, clean_phone),
            ).fetchone()
        if not row:
            row = conn.execute(
                'SELECT id FROM clients WHERE agenda_id = ? AND lower(name) = ?',
                (agenda_id, clean_name.lower()),
            ).fetchone()
        if row:
            cid = row['id']
            conn.execute(
                """UPDATE clients
                   SET name = COALESCE(NULLIF(?, ''), name),
                       phone = COALESCE(NULLIF(?, ''), phone),
                       email = COALESCE(NULLIF(?, ''), email)
                   WHERE id = ?""",
                (clean_name, clean_phone, clean_email, cid),
            )
            return cid
        cur = conn.execute(
            """INSERT INTO clients (agenda_id, name, phone, email, notes, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (agenda_id, clean_name, clean_phone, clean_email, notes.strip()[:300], now_str()),
        )
        return cur.lastrowid
