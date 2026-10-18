# Secura AI 2.0 — API Specification

## Base URL
Default local development URL: `http://localhost:8000`

---

## Authentication & Session Management

Secura AI 2.0 includes local cryptographic authentication using PBKDF2-HMAC-SHA256 password hashing and 256-bit cryptographically secure session tokens.

### 1. Analyst Login
`POST /api/v1/auth/login`

Authenticates analyst credentials, sets an `HttpOnly` session cookie (`secura_session`), and returns an authorization bearer token.

**Request Body (`application/json`):**
```json
{
  "username": "admin",
  "password": "SecuraForensics2026!"
}
```

**Success Response (`200 OK`):**
```json
{
  "success": true,
  "token": "465de8371fd5a80be86477ac4669a69a563cafc82e89c21660c9127dfc148b3e",
  "username": "admin",
  "role": "Lead Forensic Examiner",
  "expires_at": "2026-10-18T09:47:04.372898+00:00"
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid username or password (`detail: "Invalid username or password."`).
- `429 Too Many Requests`: Triggered when > 5 failed attempts occur within 60 seconds (`detail: "Too many failed login attempts. Please wait 60 seconds before trying again."`).

---

### 2. Analyst Logout
`POST /api/v1/auth/logout`

Revokes the active session token in the server's session store and deletes the `secura_session` cookie.

**Headers:**
`Authorization: Bearer <token>` (or cookie `secura_session`)

**Success Response (`200 OK`):**
```json
{
  "success": true,
  "message": "Session successfully terminated"
}
```

---

### 3. Session Verification
`GET /api/v1/auth/session`

Validates session status and returns active analyst metadata.

**Headers:**
`Authorization: Bearer <token>` (or cookie `secura_session`)

**Success Response (`200 OK`):**
```json
{
  "authenticated": true,
  "username": "admin",
  "role": "Lead Forensic Examiner",
  "expires_at": "2026-10-18T09:47:04.372898+00:00"
}
```

---

## Model Registry & Diagnostics

### 4. Model Registry Lifecycle Status
`GET /api/v1/models/status`

Returns lifecycle states (`READY`, `LOADING`, `UNAVAILABLE`, `FAILED`, `INCOMPATIBLE`) for all registered classification probes, feature extractors, and host hardware execution environments.

**Success Response (`200 OK`):**
```json
{
  "status": "operational",
  "timestamp_utc": "2026-10-17T09:46:46.720834+00:00",
  "active_head_id": "UniversalFakeDetect",
  "inference_ready": false,
  "device_available": "NVIDIA RTX 5070 Laptop (Host)",
  "cuda_driver_available": true,
  "vram_total_mb": 12227.0,
  "backbone": {
    "backbone_id": "clip_vit_l14",
    "name": "OpenAI CLIP ViT-L/14",
    "architecture": "Vision Transformer (ViT-L/14, 304M params)",
    "expected_dim": 768,
    "loaded": false,
    "device": "cuda",
    "state": "UNAVAILABLE",
    "reason": "Pretrained 933MB transformer weights (openai/clip-vit-large-patch14) not installed locally. Surrogate cache status: UNVERIFIED_SURROGATE."
  },
  "registered_heads": [
    {
      "head_id": "UniversalFakeDetect",
      "model_name": "UniversalFakeDetect (CVPR 2023)",
      "version": "1.0.0-cvpr2023",
      "filename": "fc_weights.pth",
      "expected_sha256": "477100745713bcc957beb2b40859536859b6483fd6301b3b9293151b194c7847",
      "actual_sha256": "477100745713bcc957beb2b40859536859b6483fd6301b3b9293151b194c7847",
      "weights_loaded": true,
      "weights_shape": [768, 1],
      "head_state": "READY",
      "operational_state": "UNAVAILABLE",
      "description": "Original CVPR 2023 linear probe head trained on ProGAN/LDM representations."
    },
    {
      "head_id": "SecuraCustom",
      "model_name": "Secura AI Custom Regularized Head",
      "version": "1.0.0-secura",
      "filename": "custom_fc_weights.pth",
      "expected_sha256": null,
      "actual_sha256": "d6c5...",
      "weights_loaded": true,
      "weights_shape": [768, 1],
      "head_state": "READY",
      "operational_state": "UNAVAILABLE",
      "description": "Custom L2-regularized linear classification head trained on balanced multi-generator dataset."
    }
  ]
}
```

---

## Health & Forensic Analysis

### 5. Health Check
`GET /api/v1/health`

Returns service health, service name, and version. Designed for orchestrator liveness checks. Excludes all private internal paths.

---

### 6. Image Analysis Pipeline
`POST /api/v1/analyze/image`

Executes the multi-layer forensic analysis pipeline on an uploaded image.

**Form Data:**
- `file`: JPEG or PNG image binary (maximum 25 MB).

**Headers (Optional):**
- `Authorization: Bearer <token>`

**Response Payload (`200 OK`):**
Returns `Milestone1Response` JSON containing:
1. `image_validation`: Dimensions, color mode, pixel count, format, byte size.
2. `ela_forensics`: Resaved quality difference, ELA difference metrics, base64 difference heatmap.
3. `dct_analysis`: 8×8 block boundary discontinuity, internal discontinuity, blocking ratio, grid map.
4. `noise_residual`: 3×3 Laplacian residual variance, kurtosis, noise energy, SNR estimate.
5. `c2pa_provenance`: JUMBF metadata manifest inspection, digital signatures, validation claims.
6. `metadata_forensics`: EXIF tags, camera/lens, GPS redaction notice, IFD1 thumbnail comparison.
7. `ai_detection`: Linear probe output or honest `BACKBONE_WEIGHTS_UNAVAILABLE` notification without fabricated scores.
8. `unified_report`: Consolidated evidence findings, confidence weights, explainable observations, and mandatory disclaimer.
