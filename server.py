#!/usr/bin/env python3
"""Punto de entrada del servidor Agenda de Citas MVP."""
from backend.api import create_server
from backend.config import get_config


def main():
    cfg = get_config()
    server, ctx = create_server(cfg)
    host = cfg['HOST']
    port = cfg['PORT']
    print(f"\n  Agenda de Citas MVP activo en: http://localhost:{port}")
    print(f"  Base de datos SQLite: {cfg['DB_PATH']}")
    setup_tok = ctx.db.get_setup_token()
    if setup_tok:
        print("  ──────────────────────────────────────────────────────────")
        print(f"  TOKEN DE CONFIGURACIÓN INICIAL (primer admin): {setup_tok}")
        print("  (O define ADMIN_USER y ADMIN_PASSWORD en tu archivo .env)")
        print("  ──────────────────────────────────────────────────────────")
    print("  Presiona Ctrl+C para detener el servidor.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
