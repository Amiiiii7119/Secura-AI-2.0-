# Secura AI 2.0 — Platform Runbook

## System Requirements
- **OS**: Windows 10/11 x64, Linux (Ubuntu 20.04+), or macOS
- **Python**: Python 3.12 (virtual environment at `D:\SecuraAI2\.venv`)
- **Node.js**: v18+ with npm
- **Hardware**: Minimum 8GB RAM (16GB recommended for simultaneous vision-transformer inference). CUDA GPU optional (CPU inference supported).
- **Network**: **Zero internet connectivity required at runtime.** All weights, tokenizers, and embeddings are 100% offline staged.

---

## Quickstart: Starting the Full Stack Locally

### 1. Backend Service (FastAPI)
Open a terminal in `D:\SecuraAI2`:
```powershell
# Activate virtual environment
& "D:\SecuraAI2\.venv\Scripts\Activate.ps1"

# Launch Uvicorn on localhost:8000
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Health check verification:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health"
# Returns: {"status":"healthy","service":"secura-ai-backend","version":"2.0.0"}
```

### 2. Frontend Application (React + Vite + TypeScript)
Open a second terminal in `D:\SecuraAI2\frontend`:
```powershell
npm install
npm run dev
# Starts Vite dev server at http://localhost:5173
```
Production Build & Verification:
```powershell
npm run build
# Compiles TypeScript and packages assets to dist/
```

---

## Operating the Secura Social Suite

Navigate to `http://localhost:5173` and click the **"🌐 Social Platform Simulations (Mission 26)"** dock button or route to the Social Suite.

### 1. Instagram Simulation
- **Feed Browsing**: View chronological posts with like/comment interactions. Permitted synthetic posts prominently display the `✨ AI Info: Created with AI` badge. Click the badge to inspect model confidence and regulatory citations.
- **Create Post Pre-Screening**: Click `+ Create` -> Select an image. Click `🔍 Run AI Pre-Screening` to trigger real-time inspection via `POST /api/v1/social/inspect-media` before publication.
- **Enforced Quarantine**: When synthetic interception is active in policy, attempting to share an AI image triggers HTTP 403 and launches the Quarantine Interception Engine modal.

### 2. WhatsApp Web Simulation
- **Phone Verification (OTP)**: Click `📱 Verify Phone (OTP)` in the top left header. Enter a mobile number and click `Request 6-Digit OTP Code`. A realistic push notification banner slides down with the demo code and an `⚡ Open & Auto-fill Code` button.
- **🛡️ Secura AI Forensic Bot**: Chat with the pinned official assistant. Send photos directly for immediate multi-layer forensic breakdowns (Swin, CLIP, ELA, C2PA) or click quick prompt chips (`⚖️ IT Rules 2021`, `📜 DPDP Act`, `🛡️ Secura Forensic Pipeline`) for policy answers.
- **Pre-Send Interception**: Attaching a synthetic image in personal or group chats intercepts the file pre-transmission when active policy is toggled.

### 3. Telegram Web Simulation
- **Channel Broadcast Bar**: Select a channel as an admin. The dock at the bottom of the feed provides text input, attachment upload, pin toggling, and a `🚀 Broadcast` button.
- **Subscriber Protection**: Attempting to broadcast deepfake media triggers the quarantine modal, preventing distribution to channel subscribers.
- **Reactions & Pinning**: Test instant reaction pills (`👍`, `🔥`, `❤️`, `⚡`, `⚠️`) and pin broadcasts to the top banner.

### 4. Moderation Dashboard & Policy RAG Console
- **Policy Control**: Toggle `block_ai_generated_media` between Strict Interception (HTTP 403 quarantine) and Transparency Mode (allow with AI badge).
- **Statutory Audit Log**: View SHA-256 hashes, timestamps, application source, and matched statutory rules.
- **Policy RAG Query**: Enter natural language compliance questions into the interactive query console.

---

## Database Management & Reset
The social simulation stores state in SQLite at `D:\SecuraAI2\backend\app\db\secura_social.db`.
To restore all demo users, pinned conversations, channels, and audit records to baseline:
```powershell
# Via API
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/social/demo/reset"

# Or via UI button in Social Suite header
Click "🔄 Reset Demo Sandbox"
```
