# Media Detection Integration: Shared Forensic Engine

## 1. Unified Inspection Interface
Both the frontend and backend interact with the forensic engine through a single unified endpoint:
`POST /api/v1/social/inspect`

The endpoint accepts multipart media uploads (`file`) along with contextual metadata (`app_source`, `user_id`, `text_content`).

## 2. Core Detection Pipeline
```
[Uploaded Media Bytes]
         |
         v
+-----------------------+
|  MIME & Format Check  |
+-----------------------+
         |
    +----+----+
    |         |
 (Image)   (Video)
    |         |
    |         +---> analyze_video_stream() (Temporal FFT, Optical Flow, Frame Embeddings)
    v
UniversalFakeDetect
(CLIP-ViT-L/14)
    |
    v
Canonical Score [0.00 - 1.00]
    |
    v
Canonical Verdict:
- >= 0.50 : AI GENERATED
- <  0.50 : NOT AI GENERATED
```

## 3. SHA-256 Content Hash & Provenance
Every inspected asset generates a 64-character SHA-256 checksum recorded in `social_moderation_logs` to ensure non-repudiation and forensic provenance tracking.