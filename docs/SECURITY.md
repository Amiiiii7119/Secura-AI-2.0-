# Secura AI 2.0 ? Milestone 1 Security & Privacy Policy

## 1. Security Architecture & Threat Model

### 1.1 Input Validation & Memory Exhaustion Controls
- **Streaming Size Enforcement:** The API consumes uploaded binary chunks in 64 KiB segments with an active size accumulator, terminating immediately with HTTP 413 if the payload exceeds 25 MiB (`26,214,400` bytes). This prevents unbounded memory allocation from unbuffered uploads.
- **Magic Byte Header Inspection:** File headers are validated against exact byte sequences (`\xFF\xD8\xFF` for JPEG, `\x89PNG\r\n\x1a\n` for PNG) prior to decoding.
- **Decompression Bomb Defense:** Pillow is constrained with `Image.MAX_IMAGE_PIXELS = 50_000_000`. Images attempting to expand into gigabytes of raw pixel buffers are aborted with `DECOMPRESSION_BOMB_LIMIT`.

### 1.2 In-Memory Lifecycle & Privacy
- **Zero Disk Retention:** Media bytes, recompressed buffers, and generated ELA heatmaps are processed strictly in-memory using `io.BytesIO`. No files are written to the local filesystem or staging caches during standard operations.
- **Untrusted Filename Handling:** User-provided filenames are treated as untrusted strings. They are never evaluated as filesystem paths, passed to shell commands, or used in file creation.
- **Data Minimization in Logs:** Image binary payloads, Base64 heatmaps, and client internal paths are excluded from application logs.

### 1.3 CORS & API Surface
- **Explicit CORS Origins:** Wildcard (`*`) origins with credentials are prohibited. Origins are strictly locked to authorized local development hosts (`http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`).
- **No SSRF / URL Ingestion:** The endpoint accepts direct multipart uploads only. URL fetching and remote asset downloads are completely disabled in Milestone 1 to eliminate Server-Side Request Forgery (SSRF) vectors.
- **Omission of Stack Traces:** A global exception handler intercepts unhandled exceptions and outputs sanitized error envelopes, preventing server stack trace disclosure.

---

## 2. Explicit Security Limitations & Disclaimers

1. **Magic-Byte Limitation:** Magic-byte validation verifies file header markers only. It does not replace comprehensive virus scanning, deep container sanitization, or execution sandboxing.
2. **SSD Storage Erasure:** In-memory buffers reside in process RAM. Where OS swapping or temporary disk caching occurs at the OS/hardware level, programmatic deletion does not guarantee complete cryptographic erasure from SSD flash wear-leveling blocks.
3. **Forensic Interpretation:** Neither ELA brightness nor C2PA absence constitutes evidence of AI generation, deepfake manipulation, or tampering.

---

## 3. Future Hardening Roadmap (Milestones 2+)
- Dedicated sandboxed worker processes with tight cgroup memory and CPU limits.
- ClamAV or equivalent AV scanning integration for uploaded binaries.
- End-to-end request rate limiting with token buckets (per IP / API key).
- Cryptographic TLS certificate pinning and verification for upstream C2PA trust lists.
