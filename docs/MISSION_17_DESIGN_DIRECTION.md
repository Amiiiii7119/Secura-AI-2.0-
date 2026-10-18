# SECURA AI 2.0 — MISSION 17 DESIGN DIRECTION
## Cinematic Scientific Forensics, Design Tokens & RGB-Heart Specification

**Document Identifier:** `SECURA-DESIGN-M17`  
**Date:** 2026-10-18  
**Status:** Approved Architecture & Specification  

---

### 1. Creative Vision & Product Philosophy

Secura AI 2.0 is designed as a **tier-1 scientific media intelligence workstation**, balancing Apple Human Interface Guidelines with mission-critical forensic instrumentation.

#### Core Tenets:
1. **Cinematic Precision**: Deep obsidian and midnight slate foundation with razor-thin hairline borders (`1px solid rgba(255, 255, 255, 0.08)`), ultra-refined typography, and focused lighting.
2. **Epistemic Honesty**: Zero fabricated certainty. Every metric represents physically measured quantities (CMOS photon noise variance, discrete cosine quantization, JUMBF cryptographic claims, or calibrated vision representations).
3. **Harmonic Visual Identity (The RGB-Heart)**: Chromatic decomposition of light into independent Red, Green, and Blue temporal vectors, mapped across an organic cardioid signal manifold.

---

### 2. Design Tokens & Palette

#### Surface & Canvas Hierarchy
- **Canvas App Background**: `#08090d` (Dark Obsidian) / `#f5f5f7` (Apple Light)
- **Primary Elevated Surface**: `#10121a` with `backdrop-filter: blur(24px)`
- **Secondary Surface (Cards & Panels)**: `#161922`
- **Subtle Hairline Borders**: `rgba(255, 255, 255, 0.08)` (Dark) / `rgba(0, 0, 0, 0.08)` (Light)
- **Active Focus Ring**: `#0071e3` (Apple Royal Blue)

#### Forensic Chromatic Spectrum
- **Red Channel ($R$)**: `#ff453a` (Vascular reflection / long wavelength proxy)
- **Green Channel ($G$)**: `#30d158` (Hemoglobin absorption peak / rPPG pulse signal)
- **Blue Channel ($B$)**: `#0a84ff` (Superficial scattering / structural boundary)
- **Neutral Auxiliary Accent**: `#98989d`
- **Verified Status**: `#34c759`
- **Anomaly Warning**: `#ff9f0a`
- **Tamper Alert**: `#ff453a`

#### Typography Hierarchy
- **System Stack**: `-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Inter", sans-serif`
- **Monospace Stack**: `"SF Mono", "JetBrains Mono", Menlo, Consolas, monospace`
- **Hero Title**: `48px`, font-weight `800`, tracking `-0.035em`, line-height `1.1`
- **Section Headers**: `24px`, font-weight `700`, tracking `-0.02em`
- **Card Titles & Metric Labels**: `13px / 14px`, font-weight `600`, tracking `-0.01em`
- **Technical Captions & Badges**: `11px`, font-weight `600`, uppercase, tracking `0.05em`

---

### 3. The RGB-Heart Signature Visualization Specification

#### Physical & Mathematical Basis
In facial and biological video forensics, micro-circulatory pulse waves (remote photoplethysmography) modulate reflected ambient light. The green channel ($G$) exhibits maximal hemoglobin absorption, creating a characteristic temporal phase relationship against red ($R$) and blue ($B$). In contrast, generative AI video engines (Sora, Kling, Runway, LivePortrait) exhibit high-frequency frame-to-frame chromatic jitter or desynchronized channel distributions.

#### Parametric Manifold
The RGB-Heart renders a parametric cardioid in normalized coordinate space $(u, v) \in [-1, 1]$:
$$x(\theta) = 16 \sin^3(\theta)$$
$$y(\theta) = -(13 \cos(\theta) - 5 \cos(2\theta) - 2 \cos(3\theta) - \cos(4\theta))$$

#### Multi-Channel Orbit Dynamics
1. **Three Independent Channels**:
   - $R(\theta, t)$: Red trace modulated by instantaneous frame red-channel energy $\bar{r}(t)$
   - $G(\theta, t)$: Green trace modulated by instantaneous frame green-channel energy $\bar{g}(t)$ with harmonic pulse
   - $B(\theta, t)$: Blue trace modulated by instantaneous frame blue-channel energy $\bar{b}(t)$
2. **State Machine**:
   - **Idle Mode (Landing Page)**: Autonomous gentle breathing pulse (0.8 Hz sinusoidal phase sweep).
   - **Active Video Inspection**: Real decoded frame statistics ($R, G, B$) drive trace displacement and scale.
   - **Scrubbing & Timeline Seek**: Instantaneous re-centering of the orbital trace to the selected frame index.
   - **Reduced Motion**: Respects `prefers-reduced-motion` by freezing dynamic oscillation into a static, high-resolution vector waveform.

---

### 4. Video Forensics Architecture

1. **Ingestion & Container Validation**: Supports MP4, WebM, MOV. Validates dimensions, frame count, duration, FPS, and codec headers.
2. **Deterministic Frame Sampling**: Uniform temporal sampling of up to $N=60$ frames across the duration to maintain bounded memory and instantaneous responsiveness.
3. **Per-Frame Chromatic Extraction**: Computes channel means $(\mu_R, \mu_G, \mu_B)$, standard deviations, and frame-difference anomalies $\Delta(t) = \|F_t - F_{t-1}\|_1$.
4. **Frame-Level Deep Forensics**: Any sampled frame can be inspected using the full image forensics suite (calibrated AI classifier, ELA, DCT, Laplacian noise).
5. **Timeline Synchronization**: Dual-speed scrubbing with interactive thumbnail preview, temporal anomaly markers, and synced RGB-heart display.
