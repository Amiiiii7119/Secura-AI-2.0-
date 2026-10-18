# SECURA AI 2.0 — PHASE 0 IMPLEMENTATION AUDIT REPORT

**Date:** 2026-10-18  
**Audit Target:** `D:\SecuraAI2`  
**Baseline Test Execution:** `pytest backend/tests/` (153 tests: 152 passed, 1 failed)  
**Frontend Build Execution:** `tsc && vite build` (35 modules transformed, 0 errors, 504ms)

---

## 1. Inventory of Current Components

### Backend Architecture
- **Framework:** FastAPI with Uvicorn (ASGI)
- **Primary Routes:**
  - `app.api.routes`: Core forensic analysis (`/api/v1/analyze`, `/api/v1/analyze-video`, `/api/v1/health`, `/api/v1/models/registry/status`)
  - `app.api.auth_routes`: Superuser and department login, session validation (`/api/v1/auth/*`)
  - `app.api.social_routes`: Social media simulations (`/api/v1/social/instagram/*`, `/api/v1/social/whatsapp/*`, `/api/v1/social/telegram/*`, `/api/v1/social/moderation/*`)
- **Core Services:**
  - `ai_image_detector.py`: UniversalFakeDetect linear probe (`fc_weights.pth`), HuggingFace CLIP ViT-L/14 backbone (`openai/clip-vit-large-patch14`), Swin transformer (`umm-maybe/AI-image-detector`), SecuraCustom probe.
  - `policy_rag.py`: Government Policy RAG engine using `sentence-transformers/all-MiniLM-L6-v2`.
  - `secura_social_service.py`: Central shared moderation service for Instagram, WhatsApp, and Telegram.
  - `video_orchestrator.py`, `video_sampler.py`, `video_forensics.py`, `video_fusion.py`: Multi-branch video forensics (RGB chromatic, Farneback optical flow, temporal trajectory curvature, spatial frequency, face consistency, container provenance).
- **Database:**
  - SQLite database at `D:\SecuraAI2\backend\data\secura_social.db`.
  - Tables: `social_users`, `social_posts`, `social_comments`, `social_conversations`, `social_messages`, `social_groups`, `social_channels`, `social_channel_posts`, `social_moderation_audits`, `social_policy_configs`.

### Frontend Architecture
- **Framework:** React 18 with TypeScript and Vite.
- **Key Components:**
  - `App.tsx`: Main application shell with mode switching (`forensics`, `video`, `social`).
  - `SecuraSocialSuite.tsx`: Multi-platform simulation suite hosting Instagram, WhatsApp, Telegram, and Compliance Dashboard.

---

## 2. Model Checkpoints & Weight Locations (Observed Facts)

| Model Component | File/Identifier | Current Location | Status / Issue |
|---|---|---|---|
| UniversalFakeDetect Linear Probe | `fc_weights.pth` | `D:\SecuraAI2\backend\models\weights\fc_weights.pth` | **Present** (4,083 B). SHA256 matches `477100745713bcc957beb2b40859536859b6483fd6301b3b9293151b194c7847`. |
| SecuraCustom Linear Probe | `custom_fc_weights.pth` | `D:\SecuraAI2\backend\models\weights\custom_fc_weights.pth` | **Present** (3,318 B). |
| CLIP ViT-L/14 Vision Backbone | `openai/clip-vit-large-patch14` | Host cache: `C:\Users\ammur\.cache\huggingface\hub\models--openai--clip-vit-large-patch14` | **Downloaded in cache, NOT staged in project directory.** Backend attempts online HF Hub requests if not explicitly configured with `local_files_only=True`. |
| Swin AI Image Detector | `umm-maybe/AI-image-detector` | Host cache: `C:\Users\ammur\.cache\huggingface\hub\models--umm-maybe--AI-image-detector` | **Downloaded in cache, NOT staged in project directory.** |
| Sentence-BERT (Policy RAG) | `sentence-transformers/all-MiniLM-L6-v2` | Host cache: `C:\Users\ammur\.cache\huggingface\hub\models--sentence-transformers--all-MiniLM-L6-v2` | **Downloaded in cache, NOT staged in project directory.** |

---

## 3. Reproducible Failures & Audit Findings

### Issue A: Video Fusion False Positive on Insufficient Branches (1 test failure)
- **Failing Test:** `tests/test_video_fusion_conflicts.py::test_fusion_insufficient_branches`
- **Root Cause:** In `app/services/video_fusion.py` (lines 80-87), `b1_rgb` with `score=None` and without `max_frame_synthetic_p` defaulted `p_spatial` to `0.5`, causing `has_spatial` to evaluate to `True`. Because `norm_spatial` and `ensemble_prob` became `0.50`, it tripped Case 6 (`elif has_spatial and norm_spatial >= 0.50 and ensemble_prob >= 0.50`), outputting `AI_GENERATED_VIDEO` when insufficient data should have returned `INCONCLUSIVE`.
- **Fix:** Guard `has_spatial` so that it is only `True` if `b1_rgb.score is not None` or `raw_m.get("max_frame_synthetic_p") is not None`.

### Issue B: Missing Local Weight Staging & Zero-Network Configuration
- **Symptom:** Unauthenticated HF hub warnings during startup; potential inference hangs when running offline.
- **Fix:** Create `backend/scripts/stage_local_weights.py` to copy all model snapshot weights from `C:\Users\ammur\.cache\huggingface\hub\` into `D:\SecuraAI2\backend\models\weights\` under explicit subdirectories. Generate `weights_manifest.json` with relative paths, sizes, and SHA256 hashes. Set `HF_HUB_OFFLINE=1` and `local_files_only=True`.

### Issue C: Instagram Simulation Missing Pre-Publication Scanner
- **Symptom:** User cannot test if an image is AI-generated before publishing; only gets an error toast if intercepted.
- **Fix:** Build an interactive pre-screening component in the Instagram Create Post modal (`POST /api/v1/social/inspect-media`) displaying live canonical score, branch breakdowns, and policy status.

### Issue D: WhatsApp Simulation Lacked Realistic Onboarding & Dedicated Media Bot
- **Symptom:** Direct transition into chats without simulated SMS OTP login; no obvious chat channel for testing photos with the AI model.
- **Fix:** Implement server-backed simulated fake OTP authentication flow (`/api/v1/social/otp/request` and `/api/v1/social/otp/verify`). Seed and pin `🛡️ Secura AI Forensic Bot` to automatically evaluate and report on attached photos.

---

## 4. Phase Execution Plan
1. **Phase 1:** Stage local weights, build manifest, verify strict offline loading (`local_files_only=True`).
2. **Phase 2:** Canonical media inspection service contract + fix video fusion false positive.
3. **Phase 3:** Honest image forensics, EXIF byte extraction, C2PA/SynthID truth reporting.
4. **Phase 4:** Video pipeline hardening, duration, frame sampling, request isolation.
5. **Phase 5:** Real evaluation and training strategy documentation and harness.
6. **Phase 6:** Shared moderation engine with server-side enforcement.
7. **Phase 7:** Government policy RAG with Indian legal citations.
8. **Phase 8:** Instagram UI overhaul with pre-screening.
9. **Phase 9:** WhatsApp fake OTP onboarding and forensic bot.
10. **Phase 10:** Telegram channels, pre-broadcast moderation, and forensic bot.
11. **Phase 11-13:** Security, database transactions, automated test suite verification.
