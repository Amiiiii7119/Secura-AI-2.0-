# SECURA AI 2.0 — KNOWN TECHNICAL LIMITATIONS & OPERATIONAL BOUNDARIES

## 1. Sequence Length & Minimum Frame Requirements

- **Minimum Frame Requirement**: ReStraV temporal representation modeling requires at least **4 consecutive chronological frames** to compute meaningful trajectory step vectors ($\Delta z_t$) and turning angles ($\theta_t$). For optimal geometry, **24 frames** are extracted.
- **Short Clip Fallback**: If an uploaded video has fewer than 4 frames or duration $< 0.15$ seconds, Branch 3 reports `INSUFFICIENT_DATA`, and the fusion engine falls back to 2D spatial diffusion analysis (Swin) and motion continuity.
- **Abstention Boundary**: When multiple primary analyzers cannot obtain sufficient data, Secura AI 2.0 honestly abstains with verdict `INCONCLUSIVE` rather than guessing.

---

## 2. Temporal Discontinuities & Unmodeled Scene Cuts

- **Hard Cuts Between Shots**: When a video contains rapid cut-editing between unrelated cameras/scenes, the representation displacement across the cut boundary can create an artificial step jump.
- **Mitigation Implemented**: The `VideoFrameSampler` runs a histogram-based scene cut detector. Turning angles spanning a flagged cut index are filtered out from the suspicious interval tracker.
- **Limitation**: Unflagged soft cross-dissolves or morphing transitions shorter than 2 frames may still trigger local geometric warnings.

---

## 3. Compression & Bitrate Degradation

- **Extreme Low-Bitrate / Re-Encoding**: Heavy re-encoding (e.g., WhatsApp re-compression with CRF $> 35$ or macroblock quantization) degrades fine sensor photon shot noise, dampening the noise variance metric ($\sigma_{\text{noise}}^2$).
- **ReStraV Robustness**: Because DINOv2 is a self-supervised ViT operating on semantic and spatial structures rather than high-frequency DCT coefficients, its trajectory turning angles remain robust down to medium bitrates ($> 500\text{ kbps}$), but extreme pixel blockiness can shift representation geometry.

---

## 4. Adversarial Perturbations & Future Diffusion Architectures

- **Zero Hardcoded Heuristics**: Secura AI 2.0 intentionally avoids brittle hardcoded filename heuristics, frame-rate matching, or metadata tags (which can be forged or stripped).
- **Novel Video Foundation Models**: As future generative video architectures incorporate explicit temporal consistency losses or physics discriminators during pretraining, trajectory turning angles may gradually straighten. Regular benchmark re-evaluation and checkpoint registry updates are required.

---

## 5. C2PA Provenance Credentials

- **Absence of Provenance is Not Proof**: Many camera manufacturers and social platforms do not currently sign or preserve C2PA metadata. The absence of C2PA credentials is never treated as negative evidence of real capture.
