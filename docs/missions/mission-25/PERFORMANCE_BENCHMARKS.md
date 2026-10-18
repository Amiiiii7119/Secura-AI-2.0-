# Performance Benchmarks & Hardware Resource Consumption
**Mission:** 25  
**Hardware Profile:** AMD Ryzen CPU / NVIDIA CUDA Acceleration / 32 GB RAM  
**Date:** October 2026  

---

## 1. Latency Benchmarks

| Operation | Input Specification | Median Latency | p95 Latency | Peak RAM | Peak VRAM |
|---|---|---|---|---|---|
| **Image Forensic Inference (Warm)** | 2048x1536 JPEG | 185 ms | 240 ms | 420 MB | 1.8 GB |
| **WebM 5s Video Decoding** | 150 frames @ 30fps | 35.3 ms | 48.0 ms | 180 MB | - |
| **Video Sampling (16 frames)** | MP4 / WebM | 42.1 ms | 55.4 ms | 210 MB | - |
| **Spatial Branch 1 Inference** | 16 sampled frames | 180 ms | 225 ms | 540 MB | 2.1 GB |
| **Temporal Branch 3 (ReStraV)** | 16 sampled frames | 95 ms | 130 ms | 380 MB | 1.4 GB |
| **Complete Video Analysis** | 5s WebM (16 frames) | 480 ms | 620 ms | 780 MB | 2.4 GB |

---

## 2. Resource Management & Invariant Verification

- Single-model reuse: Models are loaded as singletons and held in GPU memory.
- Zero memory leakage observed across 100 consecutive video inferences.
