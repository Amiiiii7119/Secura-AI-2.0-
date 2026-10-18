# Live Photo Camera Capture System Architecture
**Mission:** 25  
**Component:** Frontend (`src/App.tsx`), Backend (`api/v1/analyze/image`)  
**Date:** October 2026  

---

## 1. User Workflow & Experience

Beside the standard file Upload option in the Image Forensics interface, Secura AI 2.0 now provides an interactive **Camera** capture engine:
1. **Explicit Permission:** Triggered strictly when the user clicks "Camera". Does not access webcam proactively.
2. **Viewfinder Mode (`!capturedPhotoBlob`):**
   - Shows live `<video>` element with hardware stream.
   - Defaults to front camera on desktop, rear (`environment`) camera on mobile devices where supported.
   - Includes "Switch Camera" toggle button (`user` $\leftrightarrow$ `environment`).
   - "Capture Photo" triggers high-resolution canvas snapshot.
3. **Review Mode (`capturedPhotoBlob`):**
   - Displays captured still image in full viewport.
   - Provides "Retake Photo" to reopen live viewfinder without re-requesting browser permission.
   - "Use Photo & Analyze" wraps captured JPEG blob into a standard `File` object and feeds it into `/api/v1/analyze/image`.
4. **Lifecycle & Resource Cleanup:**
   - All `MediaStreamTrack` instances are cleanly stopped on modal close, retake, or unmount.
   - Object URLs generated via `URL.createObjectURL()` are explicitly revoked (`URL.revokeObjectURL()`).

---

## 2. API Parity

Camera-captured photos pass through the exact same forensic pipeline as uploaded images:
- C2PA provenance and manifest verification.
- CLIP ViT-L/14 & Swin feature extraction.
- DCT frequency lattice analysis.
- Error Level Analysis (ELA) and noise residual variance.
- Output adheres to the canonical binary verdict (`AI GENERATED` vs `NOT AI GENERATED`).
