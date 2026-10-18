# Secura AI — Forensic Media Intelligence Platform

Secura AI is an enterprise-grade digital media forensics and authenticity verification platform engineered for high-assurance deepfake detection, forensic provenance verification, and media integrity auditing.

## Architecture

Secura AI employs a decoupled, production-scalable architecture designed to respect compute and execution limits:

- **Frontend Client (Vercel)**:
  - React 18 + TypeScript + Vite 5
  - Interactive multi-spectral visualizers (ELA error level analysis, DCT 2D frequency spectra, noise residue analysis, C2PA cryptographic provenance inspection)
  - Live photo/video capture engine and real-time social quarantine suite
  - Responsive, accessibility-focused interface with clean text-only wordmark branding
  
- **Forensic Inference Engine (Dedicated Backend Host)**:
  - Python 3.12 + FastAPI + Uvicorn
  - Multi-Branch Deepfake Classifier: CLIP ViT-Large/14 & Swin Transformer ensemble
  - Temporal & rPPG biometric facial pulse consistency analyzer
  - NIST-compliant PBKDF2-HMAC-SHA256 authentication with sliding-window brute-force rate limiting

- **Managed Persistence (PostgreSQL)**:
  - Compatible with managed PostgreSQL providers (Neon, Supabase, Cloud SQL)
  - Connection pooling with pre-ping validation, automated reconnects, and transaction safety
  - Schema migrations managed via Alembic

## Database Setup & Migrations

1. Provision a PostgreSQL database instance on Neon, Supabase, or AWS RDS.
2. Set `DATABASE_URL` in your backend environment:
   ```bash
   DATABASE_URL=postgresql://user:password@host:5432/secura_db?sslmode=require
   ```
3. Run Alembic migrations to land persistent tables (`users`, `session_tokens`, `analysis_audits`):
   ```bash
   cd backend
   alembic upgrade head
   ```

## Local Development

### 1. Backend Service
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Client
```bash
cd frontend
npm install
npm run dev
```

## Production Deployment

- **Frontend**: Deployed to Vercel via Vercel CLI or Git GitHub integration.
- **Backend**: Deployed to containerized GPU/CPU hosting (Railway, Render, AWS ECS, GCP Cloud Run) with PyTorch dependencies and pre-trained weights mounted.
- **Database**: Managed PostgreSQL instance with automated backups and connection pooling.
