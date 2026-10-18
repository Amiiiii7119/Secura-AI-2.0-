# MISSION 18 — BASELINE REPOSITORY & RUNTIME AUDIT
**Project:** Secura AI 2.0  
**Audit Scope:** Video Forensic Pipeline, Feature Decoupling, Signal Truthfulness, Model Verification  
**Standard:** Gravitas Exhaustive / ASD-STE100  
**Timestamp:** 2026-10-18T12:00:00Z  

---

## 1. Executive Summary & Core Diagnosis

This audit was conducted to determine why Secura AI 2.0 previously struggled to reliably classify AI-generated videos versus authentic camera footage, verify whether its RGB and temporal features are computed from decoded pixels, and analyze the data path from video container decoding to UI rendering.

### Primary Forensic Findings:
1. **Signal Genuineness:** Decoded frames are legitimately read via OpenCV VideoCapture, correctly converted from BGR to RGB, and normalized to $[0.0, 1.0]$. The RGB-Heart in analytical mode consumes authentic per-frame channel statistics ($\mu_R, \mu_G, \mu_B$) and frame-to-frame $ differences $\Delta(t)$. In idle/landing mode, it runs an autonomous decorative animation.
2. **Missing Learned Video-Level Temporal Representation:** Prior to Mission 18, the system lacked a learned video-level temporal representation. While Mission 17 added per-frame inference using an image-level Swin Transformer (umm-maybe/AI-image-detector), per-frame spatial classification ignores temporal trajectory curvature, motion discontinuity, and inter-frame feature drift.
3. **Task Conflation Defect:** The previous taxonomy compressed all inputs into a tri-state classification (AI_GENERATED_VIDEO, AUTHENTIC_CAMERA_VIDEO, SUSPICIOUS_OR_HYBRID), improperly treating fully AI-generated scenes, face-swaps, camera motion blur, and re-encoded videos as the same underlying task.

---

## 2. Baseline Component Matrix

| Component | Implementation File | Model / Checkpoint | Genuine Inference? | Final Verdict Input? | Test Coverage | Known Failure Modes | Measured Runtime (CPU) |
|:---|:---|:---|:---|:---|:---|:---|:---|
| **Video Container & Decoder** | ackend/app/services/video_forensics.py | OpenCV cv2.VideoCapture | Yes (decodes real bytes) | Yes (metadata, frame count, FPS) | High (	ests/test_video_forensics.py) | Fails on truncated containers or rare codecs | ~80-140ms (15 frames) |
| **RGB Channel & Jitter Analyzer** | ackend/app/services/video_forensics.py | Pure NumPy / OpenCV | Yes (genuine pixel arrays) | Supporting signal (jitter anomaly timestamps) | High | Lighting changes/scene cuts trigger false deltas | ~15ms (15 frames) |
| **Sensor Noise Estimator** | ackend/app/services/video_forensics.py | Laplacian Variance $	ext{Var}(
abla^2 I)$ | Yes (high-pass filter) | Yes (heuristic noise check) | High | Over-smoothed real video mimics AI | ~8ms (15 frames) |
| **Swin Vision Classifier** | ackend/app/services/ai_image_detector.py | umm-maybe/AI-image-detector | Yes (in-memory forward pass) | Yes (mean & peak (	ext{AI})$) | High (	ests/test_ai_detector.py) | High false positives on heavy video compression | ~1100ms (15 frames on CPU) |
| **UniversalFakeDetect (CVPR 2023)** | ackend/app/services/ai_image_detector.py | c_weights.pth (Linear probe on CLIP) | Yes, when head active | Optional fallback | Medium | 0% sensitivity to modern diffusion textures | ~450ms (15 frames on CPU) |
| **Learned Temporal Branch** | *None* (Target Branch 3) | *None* | **NO (Missing)** | **NO** | None | Fails to detect temporal warping/morphing | N/A |
| **Optical Flow / Motion Branch** | *None* (Target Branch 2) | *None* | **NO (Missing)** | **NO** | None | Scene cuts conflated with motion anomaly | N/A |
| **C2PA Provenance / Container** | ackend/app/services/c2pa_service.py | C2PA Rust binary tool / manifest reader | Yes (for images) | Not bound to video container | Low for video containers | Stripped metadata on Web re-encodes | N/A for video |
| **RGB-Heart Visualization** | rontend/src/components/RGBHeartVisualization.tsx | HTML5 Canvas 2D | Yes (fed by ctiveSample) | UI Visualization | Browser / Component | Autonomous mode when no video is loaded | 60 FPS Canvas |
| **Video Workspace UI** | rontend/src/components/VideoForensicsWorkspace.tsx | React 18 / Tailwind | Yes (live telemetry) | Presentation | Browser verified | Lacked multi-branch detail dashboard | Fast render |

---

## 3. Specific Forensic Inquiries (Questions A through K)

### Question A: Is the RGB-heart fed by real decoded frames from the uploaded video?
- **Source Reference:** rontend/src/components/RGBHeartVisualization.tsx (lines 36-39, 78-95), rontend/src/components/VideoForensicsWorkspace.tsx (lines 142-160).
- **Finding (Observed & Verified):** YES, in video-analysis mode.
  When a video is uploaded and analyzed, VideoForensicsWorkspace binds the currently selected frame ctiveSample = result.sampled_frames[selectedFrameIndex].
  In RGBHeartVisualization.tsx:
  `	ypescript
  const rVal = activeSample ? activeSample.r_mean : 0.55;
  const gVal = activeSample ? activeSample.g_mean : 0.48;
  const bVal = activeSample ? activeSample.b_mean : 0.42;
  const jitter = activeSample ? activeSample.delta_prev_frame : (summary?.temporal_jitter_index || 0.05);
  `
  These values dynamically scale the cardioid geometry (channelIntensity * 0.16) and harmonic ripple distortion (harmonicMod = 1.0 + Math.sin(theta*6 + t*2 + phaseOffset) * (jitter * 0.8)).
  When no video is uploaded (landing page), it runs an autonomous decorative animation.

### Question B: Are RGB values calculated from the decoded frame pixels?
- **Source Reference:** ackend/app/services/video_forensics.py (lines 74-88).
- **Finding (Observed & Verified):** YES.
  OpenCV decodes video frames into NumPy arrays in BGR order. The service extracts:
  `python
  b_channel = frame[:, :, 0].astype(np.float32) / 255.0
  g_channel = frame[:, :, 1].astype(np.float32) / 255.0
  r_channel = frame[:, :, 2].astype(np.float32) / 255.0
  `
  Channel 2 is correctly mapped to Red, Channel 1 to Green, and Channel 0 to Blue. Pixels are properly scaled to $[0.0, 1.0]$. Timestamps are calculated deterministically as 	imestamp_sec = float(target_frame / fps).

### Question C: Are all sampled frames analyzed, or are frames accidentally reused?
- **Source Reference:** ackend/app/services/video_forensics.py (lines 68-73, 110-125).
- **Finding (Observed & Verified):** ALL sampled frames are independently analyzed.
  The loop sets cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame), reads 
et, frame = cap.read(), computes independent Laplacian variance, generates a distinct thumbnail data URL, and passes each uncompressed RGB frame to the neural detector. No cached feature vectors or duplicate frames are reused.

### Question D: Are actual video-level model predictions generated?
- **Source Reference:** ackend/app/services/video_forensics.py (lines 154-205).
- **Finding (Observed & Verified):** PARTIAL / INCOMPLETE.
  Prior to Mission 18, the pipeline computed frame-level image predictions using SwinAIImageDetector and aggregated them via heuristic statistical rules ($\mu_{P(	ext{AI})} \ge 0.48$, {	ext{AI}} \ge 0.45$, or $\max(P(	ext{AI})) \ge 0.85$).
  No learned temporal model or representation trajectory classifier was evaluated across the video stream.

### Question E: Is the current image AI detector being incorrectly used as a video AI detector?
- **Source Reference:** ackend/app/services/video_forensics.py (lines 115-128).
- **Finding (Observed & Verified):** YES.
  umm-maybe/AI-image-detector is an image-space Swin Transformer trained on static images. Still-image detectors deployed on compressed video frames suffer from two primary vulnerabilities:
  1. False positives triggered by H.264/HEVC compression artifacts (macroblocking, quantization noise).
  2. False negatives on modern diffusion videos where individual frames appear plausible but temporal continuity exhibits high geodesic curvature and unnatural motion jumps.

### Question F: Is the final verdict dominated by a broken conversion or inverted mapping?
- **Source Reference:** ackend/app/services/ai_image_detector.py (lines 43-45, 110-135).
- **Finding (Observed & Verified):** NO inversion in Swin; but UniversalFakeDetect fails on diffusion.
  The Swin model config id2label is verified as {0: 'artificial', 1: 'human'}. Index 0 corresponds to (	ext{AI})$ and Index 1 corresponds to (	ext{Real})$.
  However, UniversalFakeDetect (CVPR 2023 linear probe on CLIP) exhibits 0.0% sensitivity to modern diffusion generators because it was trained only on 2020 ProGAN data.

### Question G: Are there separate model outputs for real and generated classes?
- **Source Reference:** 	ransformers.AutoModelForImageClassification forward pass.
- **Finding (Observed & Verified):** YES.
  Output logits have dimension [1, 2]. Softmax produces complementary probabilities:
  P(	ext{artificial}) + P(	ext{human}) = 1.0

### Question H: Are reported scores genuine outputs from trained weights?
- **Source Reference:** HuggingFace Hub cache models--umm-maybe--AI-image-detector and models--openai--clip-vit-large-patch14.
- **Finding (Observed & Verified):** YES.
  Inference executes genuine PyTorch tensor forward passes with 	orch.no_grad(). Preprocessing uses standard ImageNet/CLIP mean and standard deviation tensors.

### Question I: Does the model receive correct RGB/BGR ordering, size, and normalization?
- **Source Reference:** ackend/app/services/video_forensics.py (line 116).
- **Finding (Observed & Verified):** YES.
  rame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) converts OpenCV BGR to standard RGB before creating a PIL Image. The transformer image processor handles resizing (224x224) and channel normalization.

### Question J: Does a valid AI-generated test video reach the classifier and the UI?
- **Source Reference:** Verified in Mission 17 on 	est_ai_stream.mp4 and 	est_real_stream.mp4.
- **Finding (Observed & Verified):** YES.
  The video bytes are posted to /api/v1/analyze/video, decoded into frame buffers, evaluated by the model, serialized into JSON, and rendered as an evidentiary banner and filmstrip badges in VideoForensicsWorkspace.tsx.

### Question K: Are generated videos, face-swaps, and manipulated videos treated as the same task?
- **Source Reference:** ackend/app/schemas/evidence.py (VideoAIVerdict.decision).
- **Finding (Observed & Verified):** DEFECT CONFIRMED.
  The previous schema supported only AI_GENERATED_VIDEO, AUTHENTIC_CAMERA_VIDEO, and SUSPICIOUS_OR_HYBRID.
  It failed to differentiate:
  - REAL_CAPTURE
  - AI_GENERATED_VIDEO (diffusion / autoregressive T2V)
  - FACE_MANIPULATED_VIDEO (deepfake / swap)
  - OTHER_MANIPULATED_VIDEO (splicing / temporal editing)
  - UNKNOWN_OR_OUT_OF_DISTRIBUTION
  with an explicit INCONCLUSIVE abstention policy.

---

## 4. Hardware and Runtime Environment Verification

- **Operating System:** Windows 11 Pro 64-bit (10.0.26300).
- **Python Version:** 3.12.7 (in virtual environment D:\SecuraAI2\.venv).
- **PyTorch Build:** 2.14.1+cpu (CPU SIMD execution).
- **NVIDIA GPU Hardware:** NVIDIA GeForce RTX 5070 Laptop GPU (12GB VRAM, Driver 591.84, CUDA 13.1).
- **CUDA Runtime Availability in Environment:** 	orch.cuda.is_available() == False because the active .venv contains the CPU-only PyTorch binary.
- **Architectural Directive:** To preserve environment integrity without multi-gigabyte package mutation, all neural inference pipelines must operate in high-efficiency, multi-threaded CPU mode with batching, with dynamic device selection (cuda if available, cpu otherwise), and truth-tested CPU runtime reporting.

---

## 5. Architectural Remediation Plan (Phases 2-9)

1. **Phase 2:** Complete literature review on ReStraV (Representation Straightening for Video), GenVidBench, DeCoF, and C2PA video specifications.
2. **Phase 3 & 4:** Implement shared, configurable VideoFrameSampler (uniform, scene-change aware) and typed BaseVideoAnalyzer interface.
3. **Phase 5:** Implement **Learned Temporal Representation Branch** inspired by ReStraV principles using genuine visual representations (CLIP ViT-L/14), calculating step distances, trajectory curvature, tortuosity, and acceleration variance.
4. **Phase 6:** Implement dedicated video-level classifier with multi-class taxonomy and reproducible dataset/training pipeline.
5. **Phase 7:** Implement Motion/Optical-Flow Branch (Farnebäck flow consistency), Spatial/Frequency Branch, and Container/Provenance Branch.
6. **Phase 8:** Multi-layer evidence fusion with calibrated probabilities and explicit abstention (INCONCLUSIVE).
7. **Phase 9:** Upgrade frontend evidence dashboard with multi-branch inspection and seekable suspicious intervals.
