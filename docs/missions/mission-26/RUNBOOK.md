# Mission 26 Runbook & Operations Guide

## 1. Quickstart Commands

### Start FastAPI Backend
```bash
cd D:\SecuraAI2\backend
& "..\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Start React + Vite Frontend
```bash
cd D:\SecuraAI2\frontend
npm run dev -- --port 5173
```

## 2. API Endpoints Reference
- **API Base:** `http://localhost:8000/api/v1/social`
- **Swagger Docs:** `http://localhost:8000/docs`
- **Web Interface:** `http://localhost:5173/?mode=social`

### Key Endpoints:
- `GET /api/v1/social/policy/config` - Get active moderation policies
- `POST /api/v1/social/policy/toggle` - Toggle demo synthetic blocking
- `POST /api/v1/social/inspect` - Shared media inspection API
- `POST /api/v1/social/otp/request` - Issue ephemeral WhatsApp OTP
- `POST /api/v1/social/otp/verify` - Verify OTP and obtain session
- `GET /api/v1/social/instagram/feed` - Instagram feed
- `POST /api/v1/social/instagram/posts` - Instagram post creation (with AI check)
- `GET /api/v1/social/whatsapp/conversations` - WhatsApp conversations
- `GET /api/v1/social/telegram/channels` - Telegram channels
- `GET /api/v1/social/moderation/stats` - Admin metrics & audit logs
- `POST /api/v1/social/reset` - Reset demo sandbox to pristine state

## 3. Verification Commands
```bash
& "D:\SecuraAI2\.venv\Scripts\python.exe" -m pytest "D:\SecuraAI2\backend\tests\test_mission26_social_suite.py" -v
```