# -*- coding: utf-8 -*-
import secrets

SECRET_KEY = secrets.token_hex(32)

content = """# =============================================================================
# SECURA AI - LOCAL HOST ENVIRONMENT CONFIGURATION (produced by setup script)
# =============================================================================
# Copy into version control ONLY as an example - never commit real secrets.

# --- Application Configuration ---
APP_NAME=Secura AI
APP_ENV=production
DEBUG=false
SECRET_KEY={}
""".format(SECRET_KEY)

content += """
# --- Database (PostgreSQL). For local dev a local Postgres is used.
# Format: postgresql+psycopg2://user:pass@host:5432/dbname?sslmode=require
DATABASE_URL=postgresql+psycopg2://secura:localdev@localhost:5432/secura_dev?sslmode=require

# --- Server & CORS (local dev) ---
PORT=8000
HOST=127.0.0.1
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# --- Bootstrap admin (created on first boot of a fresh local DB) ---
SECURA_ADMIN_USERNAME=admin
SECURA_ADMIN_EMAIL=admin@secura.ai
SECURA_ADMIN_PASSWORD=LocalDev2026!Secure

# --- Frontend client configuration ---
VITE_API_BASE_URL=http://localhost:8000
"""

open(r'd:\SecuraAI2\.env', 'w', encoding='utf-8').write(content)
print('Wrote d:\\SecuraAI2\.env (%d bytes)' % len(content))
