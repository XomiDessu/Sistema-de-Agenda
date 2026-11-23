"""Configuración de la aplicación desde variables de entorno y archivo .env."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def load_dotenv(env_path: Path | None = None) -> None:
    path = env_path or (BASE_DIR / '.env')
    if not path.exists():
        return
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


load_dotenv()


def get_config() -> dict:
    return {
        'HOST': os.environ.get('HOST', '0.0.0.0'),
        'PORT': int(os.environ.get('PORT', '8000')),
        'DB_PATH': os.environ.get('DB_PATH', str(BASE_DIR / 'data' / 'agenda.db')),
        'PUBLIC_DIR': str(BASE_DIR / 'public'),
        'APP_NAME': os.environ.get('APP_NAME', 'Agenda de Citas'),
        'APP_URL': os.environ.get('APP_URL', '').rstrip('/'),
        'COOKIE_SECURE': os.environ.get('COOKIE_SECURE', 'false').lower() == 'true',
        'ADMIN_USER': os.environ.get('ADMIN_USER', '').strip().lower(),
        'ADMIN_PASSWORD': os.environ.get('ADMIN_PASSWORD', ''),
        'ADMIN_NAME': os.environ.get('ADMIN_NAME', 'Administrador').strip(),
        'ADMIN_EMAIL': os.environ.get('ADMIN_EMAIL', '').strip().lower(),
        'SETUP_TOKEN': os.environ.get('SETUP_TOKEN', '').strip(),
        'SMTP_HOST': os.environ.get('SMTP_HOST', '').strip(),
        'SMTP_PORT': int(os.environ.get('SMTP_PORT', '587') or '587'),
        'SMTP_USER': os.environ.get('SMTP_USER', '').strip(),
        'SMTP_PASS': os.environ.get('SMTP_PASS', ''),
        'SMTP_FROM': os.environ.get('SMTP_FROM', '').strip(),
        'SMTP_TLS': os.environ.get('SMTP_TLS', 'true').lower() == 'true',
    }
