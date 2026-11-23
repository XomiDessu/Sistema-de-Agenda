"""Seguridad en servidor: PBKDF2-SHA256, TOTP (RFC 6238), OTC, códigos de respaldo y rate limiting."""
import base64
import hashlib
import hmac
import re
import secrets
import struct
import time
from collections import defaultdict
from threading import Lock

PBKDF2_ITERATIONS = 150_000
OTC_TTL_SEC = 10 * 60
OTC_MAX_TRIES = 5
OTC_COOLDOWN_SEC = 60
LOGIN_MAX_FAILS = 5
LOGIN_LOCK_SEC = 5 * 60

EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]{2,}$')
USER_RE = re.compile(r'^[a-z0-9_.-]{3,20}$')
POLICY_MSG = 'Contraseña: mínimo 10 caracteres con mayúscula, minúscula y número'


def pw_ok(password: str) -> bool:
    if not isinstance(password, str) or len(password) < 10:
        return False
    return bool(re.search(r'[a-z]', password) and re.search(r'[A-Z]', password) and re.search(r'\d', password))


def random_hex(n_bytes: int = 16) -> str:
    return secrets.token_hex(n_bytes)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def hash_password(password: str, salt_hex: str) -> str:
    dk = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        bytes.fromhex(salt_hex),
        PBKDF2_ITERATIONS,
        dklen=32,
    )
    return dk.hex()


def verify_password(password: str, salt_hex: str, expected_hash: str) -> bool:
    computed = hash_password(password, salt_hex)
    return hmac.compare_digest(computed, expected_hash)


def norm_code(code: str) -> str:
    return re.sub(r'[^a-z0-9]', '', str(code or '').lower())


def numeric_code(digits: int = 6) -> str:
    return str(secrets.randbelow(10 ** digits)).zfill(digits)


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode('ascii').rstrip('=')


def _totp_at(secret_b32: str, step: int) -> str:
    pad = '=' * ((8 - len(secret_b32) % 8) % 8)
    key = base64.b32decode(secret_b32.upper() + pad, casefold=True)
    msg = struct.pack('>Q', step)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(code % 1_000_000).zfill(6)


def check_totp(secret_b32: str, code: str, now: float | None = None) -> bool:
    clean = re.sub(r'\s+', '', str(code or ''))
    if not clean.isdigit() or len(clean) != 6:
        return False
    step = int((now if now is not None else time.time()) // 30)
    for delta in (-1, 0, 1):
        if hmac.compare_digest(_totp_at(secret_b32, step + delta), clean):
            return True
    return False


def generate_recovery_codes(count: int = 8) -> tuple[list[str], list[str]]:
    plain = []
    hashed = []
    for _ in range(count):
        raw = secrets.token_hex(8)
        formatted = '-'.join(raw[i:i + 4] for i in range(0, len(raw), 4))
        plain.append(formatted)
        hashed.append(sha256_hex(norm_code(formatted)))
    return plain, hashed


def generate_backup_codes(count: int = 8) -> tuple[list[str], list[str]]:
    plain = [secrets.token_hex(4) for _ in range(count)]
    hashed = [sha256_hex(c.lower()) for c in plain]
    return plain, hashed


class RateLimiter:
    """Limitador de tasa en memoria por clave (IP + ruta)."""

    def __init__(self):
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def allow(self, key: str, max_requests: int, window_sec: int) -> tuple[bool, int]:
        now = time.time()
        cutoff = now - window_sec
        with self._lock:
            entries = [t for t in self._hits[key] if t > cutoff]
            if len(entries) >= max_requests:
                retry_after = max(1, int(entries[0] + window_sec - now))
                self._hits[key] = entries
                return False, retry_after
            entries.append(now)
            self._hits[key] = entries
            return True, 0

    def reset(self):
        with self._lock:
            self._hits.clear()
