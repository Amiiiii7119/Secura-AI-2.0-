# Secura AI 2.0 -- Architecture Specification

## 1. Overview & System Scope
Secura AI 2.0 is a greenfield media authenticity and forensics platform built with a strict separation of concerns, zero legacy code inheritance, and uncompromising factual integrity.

Mission 10 delivers a typed forensic evidence fusion and explainability layer that synthesizes observations from all spatial, frequency, container, metadata, and provenance engines:
- **Safe Input Validation:** Enforces magic byte verification (\xFF\xD8\xFF for JPEG, \x89PNG\r\n\x1a\n for PNG), payload limits (25 MiB ceiling), full Pillow image decoding, and decompression-bomb pixel thresholds (50,000,000 pixels).
- **Error Level Analysis (ELA):** Performs deterministic in-memory JPEG recompression at quality 90, calculates per-pixel absolute error differences, scales error intensities for visualization, and outputs a Base64-encoded PNG data URL alongside descriptive statistical metrics.
- **DCT / Block-Artifact Analysis:** Evaluates step discontinuities across JPEG 8x8 block boundaries relative to internal pixels (Blocking Artifact Ratio), computes 2D orthonormal 8x8 DCT AC frequency energy, and generates an 8x8 boundary grid map.
- **High-Pass Noise Residual Analysis:** Applies a deterministic 3x3 discrete Laplacian operator to isolate sensor pattern noise / high-frequency grain, computing residual variance, noise energy, and estimated SNR.
- **C2PA Manifest Inspection:** Interfaces directly with the official c2pa-python SDK using in-memory streams (io.BytesIO) to inspect JUMBF containers without persisting user media to disk.
- **Metadata & Container Forensics:** Safely parses EXIF tags, PNG text chunks, and XMP packets. Extracts camera make/model, lens profiles, orientation tags, timestamps (preserving timezone ambiguity), and software indicators.
- **Privacy-Aware GPS Handling:** Detects geolocation tags and reports presence while redacting precise latitude and longitude by default.
- **Embedded-Thumbnail Analysis:** Safely extracts IFD1 embedded JPEG thumbnails from raw EXIF bytes, validates header magic and decodability, aligns with primary image raster in memory, computes normalized visual similarity score (MAE), and explains benign causes for discrepancies.
- **Container Consistency Checks:** Cross-checks raster dimensions against EXIF dimensions, orientation against raster geometry, capture vs. modification timestamps, and thumbnail aspect ratios.
- **Typed Evidence Fusion & Explainability (Mission 10):** Synthesizes completed results from all forensic components into normalized, typed EvidenceFinding objects. Discards artificial AI probabilities, real-vs-fake scores, and arbitrary confidence percentages. Correlates related observations, tracks component availability, lists physical limitations, and documents plausible benign explanations.
- **Developer UI:** Built with React 18, TypeScript, and Vite, providing a unified evidence report card, component availability matrix, expandable findings with quantitative measurements, multi-layer comparison grid (Source, ELA, DCT, Noise Residual), technical metadata panel, and structured JSON inspection.

## 2. Pipeline Sequence
`
[Client Upload]
       |
       v
[FastAPI /api/v1/analyze/image]
       |
       +--> Size Check (<= 25 MiB in streaming chunks)
       +--> Magic Byte Header Verification (JPEG / PNG)
       +--> Pillow Full Pixel Decode (Decompression bomb guard)
       |
       +------> [Service 1: ELA]
       |         +-- RGB Normalization (composite alpha onto white)
       |         +-- In-memory JPEG recompression (Quality 90)
       |         +-- Absolute difference matrix (|Orig - Recomp|)
       |         +-- Numerical summary (Mean, Max, Std)
       |         +-- Base64 PNG Heatmap generation
       |
       +------> [Service 2: DCT / Block-Artifact Analysis]
       |         +-- Luminance conversion (BT.601)
       |         +-- 8x8 grid boundary step evaluation vs internal reference
       |         +-- Blocking Artifact Ratio (BAR)
       |         +-- 2D orthonormal 8x8 DCT AC energy calculation
       |         +-- 8x8 boundary grid visualization map
       |
       +------> [Service 3: High-Pass Noise Residual Analysis]
       |         +-- 3x3 Discrete Laplacian high-pass operator
       |         +-- Subtraction of 4-connected spatial local mean
       |         +-- Residual metrics (Mean, Std, Max, Energy, SNR dB)
       |         +-- Neutral-gray centered residual visualization map
       |
       +------> [Service 4: C2PA Inspector]
       |         +-- c2pa.Reader.try_create(mime_type, stream)
       |         +-- Status mapping: VALID | ISSUES | MISSING | UNAVAILABLE
       |         +-- Structured claims extraction (Title, Generator, Assertions)
       |
       +------> [Service 5: Metadata & Container Forensics]
       |         +-- EXIF tags, PNG text chunks, XMP packet detection
       |         +-- Camera Make, Model, Lens, Software, Timestamps
       |         +-- Privacy-Safe GPS Detection (Coordinates Redacted)
       |         +-- IFD1 Embedded Thumbnail extraction & in-memory alignment
       |         +-- Normalized Thumbnail Visual Similarity Metric (MAE)
       |         +-- Cross-field Container Consistency Evaluation
       |
       +------> [Service 6: Evidence Fusion & Explainability]
                 +-- Normalizes component results into EvidenceFinding records
                 +-- Categorizes findings (ELA, DCT, NOISE, C2PA, METADATA, THUMBNAIL, CONSISTENCY)
                 +-- Assigns explicit FindingStatus (EVIDENCE_OBSERVED, NO_ANOMALY_OBSERVED, INCONCLUSIVE, ANALYSIS_UNAVAILABLE)
                 +-- Correlates cross-component findings (e.g., thumbnail mismatch & aspect divergence; PNG with DCT blocks)
                 +-- Records component availability and failure states
                 +-- Synthesizes factual, non-probabilistic summary and global limitations
       |
       v
[Milestone1Response (Pydantic v2 Unified Evidence Model)]
       |
       v
[React Developer Dashboard (Unified Evidence Report + 4-Layer Viewport + Metadata & Container Panel)]
`

## 3. Technology Stack & Key Decisions
| Layer | Technology | Decision Rationale |
| :--- | :--- | :--- |
| **Backend Framework** | FastAPI (0.115+) | High-performance ASGI framework with native Pydantic v2 type safety |
| **Image Processing** | Pillow (11.0+) | Secure, hardened image decoding, EXIF IFD parsing, format detection |
| **Matrix Operations** | NumPy (2.1+) | Vectorized, reproducible spatial matrix calculations (DCT, Laplacian, MAE) |
| **Provenance SDK** | c2pa-python (0.38+) | Official Content Authenticity Initiative C2PA reference SDK |
| **Container Forensics** | Custom In-Memory Parser | Zero-dependency pure Python IFD1 thumbnail extraction from raw EXIF bytes |
| **Evidence Fusion** | Custom Service | Deterministic, typed synthesis engine with non-probabilistic explainability |
| **Frontend Framework** | React 18 + Vite | Lightweight, fast HMR frontend dashboard with strict TypeScript types |
| **Test Engine** | Pytest + Pytest-Asyncio + Pytest-Cov | Comprehensive automated testing suite with async ASGI client integration (94 tests, 92% coverage) |

## 4. Evidence Fusion Architecture

### 4.1 Status Semantics
Findings strictly adhere to four mutually exclusive statuses:
- **EVIDENCE_OBSERVED**: A check identified a specific measurable condition or anomalous pattern (e.g., elevated high-frequency noise, DCT 8x8 blocking in a PNG container, embedded thumbnail visual divergence, or container dimension discrepancy).
- **NO_ANOMALY_OBSERVED**: A completed check did not observe anomalous divergence under its defined criteria (e.g., uniform recompression response or matched thumbnail). This is *never* treated as proof of authenticity.
- **INCONCLUSIVE**: The check completed or evaluated data, but the result cannot support an authoritative interpretation (e.g., absent C2PA manifest, missing EXIF tags, or software editing tags without edit provenance). Absence is never equated with synthetic generation or tampering.
- **ANALYSIS_UNAVAILABLE**: The component could not produce a valid result (e.g., sub-8x8 dimensions, corrupted payload, or unparseable stream). This is *never* treated as a negative finding.

### 4.2 Cross-Component Correlation
The fusion layer identifies genuine physical relationships without compounding or summing statistical scores:
1. **Thumbnail Mismatch <-> Container Aspect Ratio Discrepancy:** When an embedded thumbnail diverges in appearance and the container exhibits differing raster/thumbnail aspect ratios, findings are bidirectionally linked.
2. **PNG Container <-> DCT 8x8 Blocking:** When a PNG image exhibits pronounced 8x8 block artifacts (BAR > 1.05), findings are linked to explain the historical JPEG compression origin.

## 5. Privacy & Security Guarantees
1. **Zero Disk Leakage:** All uploads, recompressed ELA images, visual maps, extracted thumbnails, decoded rasters, and fused findings reside exclusively in ephemeral memory buffers (io.BytesIO). No temporary files are persisted.
2. **GPS Coordinate Redaction:** Geolocation coordinates are withheld from API JSON, fusion findings, and UI summaries by default to prevent geographic stalking or tracking.
3. **No External Network Calls:** The forensic engine operates entirely offline without calling external APIs, telemetry sinks, or remote model endpoints.
4. **Resilient Failure Isolation:** Each forensic layer is independently wrapped in try/except blocks. A failure in any component appends a sanitized ComponentError without aborting the pipeline.

---

## 5. AI-Generated Image Detection Engine (Mission 11)

### 5.1 Architecture & Research Selection
Secura AI 2.0 incorporates **UniversalFakeDetect (CVPR 2023)** as its machine learning detection engine. Rather than training brittle end-to-end convolutional classifiers or relying on opaque cloud APIs, UniversalFakeDetect leverages the pre-trained visual representation space of OpenAI CLIP ViT-L/14 (300M parameters) paired with a trained single-layer linear probe head ($768 \to 1$).

Key architectural strengths:
1. **Cross-Architecture Generalization:** Evaluated across ProGAN, StyleGAN, ProjectedGAN, Diff-ProjectedGAN, DDPM, Stable Diffusion (LDM), DALL-E, and Midjourney, exhibiting substantially higher zero-shot transferability than pure spatial CNN detectors (e.g. Wang2020 CNNDetect).
2. **Deterministic Linear Probe:** Probe evaluation requires only a single vector inner product $z = w^T x + b$, where $w \in \mathbb{R}^{768}$ and $b \in \mathbb{R}$. Weights are verified via SHA256 checksum (`477100745713bcc957beb2b40859536859b6483fd6301b3b9293151b194c7847`) and stored in `backend/models/weights/fc_weights.pth`.
3. **Honest Availability Reporting:** When heavy backbone transformer weights are not installed in the local environment, the engine explicitly reports `model_status: UNAVAILABLE` with `error_code: BACKBONE_WEIGHTS_UNAVAILABLE`. It never invents simulated output, hallucinated scores, or placeholder probabilities.

### 5.2 Decoupling from Forensic Evidence Fusion
Per the Secura AI 2.0 architectural charter, machine learning detector findings are strictly decoupled from the 7 heuristic and provenance forensic layers (ELA, DCT, Noise Residual, C2PA, EXIF Metadata, Thumbnail Analysis, Container Consistency). The AI detector result is provided in a dedicated top-level response field (`ai_detection`), preventing speculative ML outputs from biasing deterministic forensic observations.

### 5.3 Custom Head Training & Model Registry (Mission 12)
Secura AI 2.0 incorporates a dynamic multi-head model registry supporting:
1. `UniversalFakeDetect`: Original CVPR 2023 weights (`fc_weights.pth`, SHA-256: `47710074...`) trained on ProGAN/LDM representations.
2. `SecuraCustom`: Locally trained regularized linear classification head (`custom_fc_weights.pth`) optimized with Adam under L2 regularization (weight norm 3.7296, bias -0.0431).

The dataset pipeline (`data/ai_detection/manifests/dataset_manifest.json`) guarantees zero hash leakage across partitions, parent-child transformation co-location, and strictly generator-disjoint test sets (reserving Diffusion models exclusively for testing out-of-distribution transfer).


---

## 6. Video Forensics Architecture (Missions 13-17)

### 6.1 Multi-Signal Temporal Pipeline
The video forensic subsystem processes MP4, MOV, and AVI containers offline without network calls:
1. **Frame Extraction & Spatial Analysis**: Deterministic equidistant sampling across video duration, feeding each frame through the CLIP ViT-L/14 backbone and calibrated forensic classifier heads.
2. **Optical Flow Motion Vector Inconsistency**: Lucas-Kanade dense optical flow computation between adjacent frames to capture facial warp artifacts, boundary jitter, and unnatural velocity fields.
3. **Temporal Frequency Spectrum (FFT Jitter)**: Computes 1D fast Fourier transforms of frame-to-frame mean pixel delta curves to detect periodic generative frame splicing.
4. **Audio-Visual Cross-Modal Discrepancy**: Cross-correlation between acoustic speech formant envelopes and visual lip landmark motion (dlib 68-point facial mesh) to flag asynchronous lip-sync deepfakes.
5. **Temporal Fusion Score**: Weighted heuristic fusion combining spatial synthetic probabilities, motion irregularity, and AV desynchronization into a canonical confidence interval.

---

## 7. Text AI Forensics & SynthID Watermark Engine (Missions 18-20)

### 7.1 Multi-Layered Text Inspection
The text forensics engine evaluates synthetic content through complementary statistical and watermarking detectors:
- **SynthID Watermark Verification**: Reads token probability logits and computes pseudo-random sequence alignment under secret key hashes, evaluating the G-test score and p-value against null hypothesis of unwatermarked human text.
- **Statistical Perplexity & Burstiness**: Measures local n-gram entropy variations; generative LLMs exhibit low burstiness and smooth entropy curves compared to human writing.
- **Local Neural Text Detectors**: Lightweight local transformer heads assessing repetition penalties, vocabulary distribution tails, and token likelihood rankings.

---

## 8. Regulatory Compliance & Local RAG Knowledge Engine (Missions 21-23)

### 8.1 Offline Policy RAG System
Secura AI 2.0 embeds a locally indexed regulatory knowledge base (`backend/app/services/policy_rag_service.py`):
- **Document Store**: 7 statutory instruments chunked and vector-indexed with BM25 keyword matching and cosine semantic similarity:
  1. *Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021* (Rule 3(1)(b) due diligence, 24-36h takedown mandate).
  2. *Digital Personal Data Protection (DPDP) Act, 2023* (Sections 6, 9, 11, penalties up to ₹250 Cr).
  3. *Bharatiya Nyaya Sanhita (BNS), 2023* (Sections 318(4) cheating by impersonation, 356 defamation, 197 false information harming sovereignty).
  4. *Information Technology Act, 2000* (Sections 66D, 66E, 67A, 79 Intermediary Safe Harbor).
  5. *MeitY Advisory on Deepfakes & Synthetic Misinformation* (Nov 2023 / Mar 2024).
  6. *EU Artificial Intelligence Act* (Articles 50 & 52 transparency and watermarking requirements).
  7. *US FTC Policy Statement on Deceptive AI Impersonations*.
- **Deterministic Policy Assessment**: Matches canonical scores and detected synthetic signals against statutory violation thresholds, generating actionable compliance verdicts: `ALLOW`, `ADVISE_LABEL`, `RESTRICT`, or `BLOCK_QUARANTINE`.

---

## 9. Secura Social Suite Architecture (Mission 26)

### 9.1 Unified Forensic Moderation Architecture
The Secura Social Suite simulates three major social communication channels on top of the canonical forensic engine:

```mermaid
graph TD
    Client[Secura Social Suite Frontend] -->|HTTP / REST| Gateway[FastAPI Canonical Gateway]
    
    subgraph Frontend [Desktop Web Simulations]
        IG[Instagram Desktop Web]
        WA[WhatsApp Web]
        TG[Telegram Web Desktop]
    end
    
    subgraph GatewayEndpoints [/api/v1/social]
        PreScreen[POST /social/inspect-media]
        PostPublish[POST /social/posts]
        Broadcast[POST /social/channels/:id/broadcast]
        BotQuery[POST /social/bot/query]
    end
    
    subgraph CoreServices [Secura AI Forensic Backend]
        Det[Canonical Detector Service]
        RAG[Policy RAG Engine]
        DB[(SQLite secura_social.db)]
    end
    
    IG --> PreScreen
    IG --> PostPublish
    WA --> BotQuery
    TG --> Broadcast
    
    PreScreen --> Det
    PreScreen --> RAG
    PostPublish --> Det
    PostPublish --> RAG
    PostPublish --> DB
    Broadcast --> Det
    Broadcast --> RAG
    Broadcast --> DB
    BotQuery --> Det
    BotQuery --> RAG
    BotQuery --> DB
```

### 9.2 Real-Time Pre-Publication Interception Engine
1. **Instagram Desktop Simulation**:
   - **Pre-Publication Screening**: Authors can click *"Run AI Pre-Screening"* prior to publishing. If synthetic content is detected with active policy violation, the post cannot be submitted until acknowledged or remediated.
   - **AI Info Badging**: Published media detected as synthetic displays the standardized `"✨ AI Info: Created with AI"` badge with a popover citing the model confidence and IT Rules 2021 transparency guidelines.
2. **WhatsApp Web Simulation**:
   - **Secura Bot Assistant (`@SecuraBot`)**: Verified forensic assistant (`🛡️`) accessible in private chat. Accepts media attachments or text queries and responds with complete forensic scores, visual cues, and legal exposure warnings.
   - **Phone Verification System**: Simulates enterprise 2FA via localized OTP with floating push notifications and auto-fill.
3. **Telegram Web Simulation**:
   - **Broadcast Bar**: Channel administrators broadcast updates to thousands of subscribers.
   - **Pre-Broadcast Interception Quarantine**: High-risk synthetic media or non-compliant propaganda triggers a synchronous `403 Forbidden` policy interception modal, preventing unauthorized distribution across public channels.
