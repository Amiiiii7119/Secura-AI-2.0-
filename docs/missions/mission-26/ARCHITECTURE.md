# Mission 26 Architecture: Social Suite & Policy RAG

## 1. System Topology

```
+-------------------------------------------------------------------------------+
|                             SECURA AI 2.0 FRONTEND                            |
|  (React 18 + TypeScript + Vite + Tailwind/Glassmorphism Design System)        |
|                                                                               |
|  +--------------------+  +---------------------+  +------------------------+  |
|  | Instagram Client   |  |  WhatsApp Client    |  | Telegram Channels      |  |
|  | - Feed & Upload    |  |  - Ephemeral OTP    |  | - Public Supergroups   |  |
|  | - Camera Snapshot  |  |  - Direct & Groups  |  | - Broadcast & Pinned   |  |
|  | - Likes / Comments |  |  - Read Receipts    |  | - Emoji Reactions      |  |
|  +--------------------+  +---------------------+  +------------------------+  |
|                                     |                                         |
|  +----------------------------------v--------------------------------------+  |
|  |                  Admin Moderation & Policy Dashboard                     |  |
|  +-------------------------------------------------------------------------+  |
+-------------------------------------------------------------------------------+
                                      | (REST API /api/v1/social)
+-------------------------------------v-----------------------------------------+
|                             FASTAPI BACKEND RUNTIME                           |
|                                                                               |
|  +-------------------------------------------------------------------------+  |
|  | social_routes.py : APIRouter(/api/v1/social)                            |  |
|  | - Instagram, WhatsApp, Telegram, OTP, and Moderation Endpoints          |  |
|  +-------------------------------------------------------------------------+  |
|                         |                                  |                  |
|  +----------------------v--------------+  +----------------v---------------+  |
|  | secura_social_service.py            |  | government_policy_rag.py       |  |
|  | - SQLite DB: data/secura_social.db  |  | - Vector Embeddings Engine     |  |
|  | - OTP & Session Manager             |  | - MiniLM-L6-v2 Embeddings      |  |
|  | - Atomic Engagements & Audit Logs   |  | - 8 Indian Statutory Acts      |  |
|  +-------------------------------------+  +--------------------------------+  |
|                         |                                                     |
|  +----------------------v--------------------------------------------------+  |
|  | detector_service.py (Real Shared AI Detection Inference Engine)          |  |
|  | - UniversalFakeDetect-CLIP-ViT-L/14 (Images)                             |  |
|  | - analyze_video_stream multi-branch fusion (Videos)                      |  |
|  +-------------------------------------------------------------------------+  |
+-------------------------------------------------------------------------------+
```

## 2. Database Schema (`data/secura_social.db`)
- `social_users`: Seeded demo personas (`u_arjun`, `u_priya`, `u_tech`, `u_admin`).
- `demo_otp`: Ephemeral phone OTP records with expires_at and attempt counts.
- `social_sessions`: Active sessions (`sess_...`) mapped to users.
- `social_posts`: Instagram media, caption, tags, verdict, score, block state.
- `social_likes` & `social_comments`: Atomic engagements.
- `social_conversations` & `social_messages`: WhatsApp chats and read receipts.
- `social_channels` & `social_channel_posts`: Telegram channels and pins.
- `social_reactions`: Polymorphic reactions across posts and messages.
- `social_moderation_logs`: Detailed forensic audit trail of all inspected media.