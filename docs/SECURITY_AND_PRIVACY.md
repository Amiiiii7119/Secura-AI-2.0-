# Secura AI 2.0 — Security, Privacy, and Safe Harbor Architecture

## Threat Model & Design Principles
Secura AI 2.0 is designed for forensic veracity, privacy-preserving moderation, and statutory compliance under Indian and international digital media regulations.

---

## 1. Privacy Safeguards

### 1.1 Ephemeral OTP Authentication
- WhatsApp mobile verification uses safe, short-lived 6-digit OTP codes.
- Codes are cryptographically generated using Python `secrets` module and hashed with SHA-256.
- Strict 5-minute time-to-live (TTL) expiration with single-use invalidation.
- Rate-limited to prevent brute-force verification attacks.

### 1.2 Local Media Storage & Hashing
- Uploaded media is hashed with SHA-256 before analysis.
- When media is quarantined (blocked), it is stored exclusively in an isolated, non-public quarantine directory with zero delivery to feed or subscribers.
- No facial recognition or biometric signatures are retained beyond the active inspection session.

### 1.3 Zero Outbound Telemetry
- The entire model execution pipeline runs strictly on local compute.
- No user media, prompt text, or metadata is transmitted to third-party cloud providers, APIs, or external model hosts.

---

## 2. Intermediary Safe Harbor Compliance (IT Rules 2021)

### 2.1 Pre-Publication Interception
- In high-enforcement mode (`block_ai_generated_media = True`), synthetic media is intercepted prior to database persistence and network distribution.
- Returns HTTP 403 Forbidden with detailed forensic scorecard and statutory citations, satisfying the intermediary due diligence obligation to prevent transmission of deceptive media.

### 2.2 Transparency Labelling (ECI & MeitY Alignment)
- When content is permitted under informational policy, the platform automatically appends the `✨ AI Info: Created with AI` badge.
- Interactive popovers inform viewers of detection models, synthetic confidence score, and regulatory basis.

---

## 3. Cryptographic Provenance (C2PA)
- The platform incorporates standard C2PA JUMBF parsing.
- Verifies cryptographically signed provenance manifests from compliant digital cameras and editing tools.
- Flags manifest tampering, mismatched thumbnails, and broken certificate trust chains.
