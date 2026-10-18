# Live Video Camera Capture & Streaming Architecture
**Mission:** 25  
**Component:** `src/components/VideoForensicsWorkspace.tsx`, `api/v1/video/analyze`  
**Date:** October 2026  

---

## 1. Live Video Recording Pipeline

- Implemented via HTML5 `MediaRecorder` with dynamic MIME type sniffing:
  - `video/webm;codecs=vp9,opus` (preferred)
  - `video/webm;codecs=vp8,opus` (fallback)
  - `video/webm`
  - `video/mp4` (Safari / WebKit)
- Provides real-time recording timer and duration counter.
- Automatic track cleanup upon recording stop or component unmount.

---

## 2. Backend Stream Resilience

- Browser-recorded WebM files do not write EBML duration headers into chunked blobs.
- Backend `VideoFrameSampler` detects unindexed WebM streams and routes them through the high-speed two-pass grab scanner.
- Guarantees accurate non-zero duration calculation and multi-frame sampling regardless of whether the video was recorded live or uploaded from disk.
