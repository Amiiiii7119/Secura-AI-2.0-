# FRONTEND REDESIGN SPECIFICATION: APPLE HUMAN INTERFACE GUIDELINES
**Secura AI 2.0 Digital Media Forensics Workstation**  
**Design System:** Apple HIG (Clarity, Deference, Depth)  
**Deliverable:** `docs/FRONTEND_REDESIGN.md`

---

## 1. Design Philosophy & Architectural Principles

The Secura AI 2.0 user interface was completely overhauled to replace dark sci-fi/cyberpunk tropes with the calm, precise, and authoritative visual language associated with professional Apple macOS and iOS applications.

Forensic analysis requires high cognitive focus. The redesigned interface follows three core Apple Human Interface Guidelines (HIG) pillars:
1. **Clarity:** Content is the focal point. System typography (`-apple-system`, SF Pro) provides sharp readability at all scales. Status badges use distinct semantic tints rather than garish glowing borders.
2. **Deference:** The user interface recedes into the background to highlight the evidence under review—the original image, error level heatmaps, DCT block boundary grids, and sensor noise residuals.
3. **Depth:** Smooth transitions, refined multi-tier elevation shadows, and translucent surfaces create clear visual hierarchy without distracting ornamentation.

---

## 2. Design Token System & Color Palette

### 2.1 Cohesive Neutral Palette (Light & Dark Mode)

| Token | Light Theme Value | Dark Theme Value | Purpose |
| :--- | :--- | :--- | :--- |
| `--bg-app` | `#f5f5f7` (Apple Gray 6) | `#000000` (Pure Black) | Canvas background |
| `--bg-surface` | `#ffffff` (Pure White) | `#1c1c1e` (Apple Dark Surface) | Primary cards and panels |
| `--bg-surface-secondary` | `#fbfbfd` | `#2c2c2e` | Viewport frames and callout boxes |
| `--bg-surface-tertiary` | `#f0f0f2` | `#3a3a3c` | Inner cards and chips |
| `--border-subtle` | `rgba(0, 0, 0, 0.08)` | `rgba(255, 255, 255, 0.12)` | Hairline container borders |
| `--border-strong` | `rgba(0, 0, 0, 0.16)` | `rgba(255, 255, 255, 0.22)` | Active borders and drag zones |
| `--text-primary` | `#1d1d1f` | `#f5f5f7` | Headings, labels, and primary data |
| `--text-secondary` | `#6e6e73` | `#a1a1a6` | Subtitles and table descriptors |
| `--text-tertiary` | `#86868b` | `#86868b` | Metadata timestamps and footnotes |
| `--accent-system` | `#0071e3` (System Blue) | `#2997ff` (System Blue Dark) | Interactive buttons and active states |

### 2.2 Semantic Status System

Status badges avoid solid neon colors in favor of Apple-standard subtle tint backgrounds ($12\%\text{--}18\%$ opacity) with high-contrast text:
- **Valid / Authentic / Normal:** `--status-success` (`#34c759` light / `#30d158` dark)
- **Warning / Anomaly / Inconsistency:** `--status-warning` (`#ff9500` light / `#ff9f0a` dark)
- **Error / Danger / Tampered:** `--status-danger` (`#ff3b30` light / `#ff453a` dark)
- **Inconclusive / Missing / Neutral:** `--status-neutral` (`#8e8e93` light / `#98989d` dark)
- **Observed Evidence:** `--status-observed` (`#5856d6` light / `#5e5ce6` dark)

---

## 3. Redesigned Section Architecture

### 3.1 Top Navigation Bar
- **Monogram & Identity:** Monochromatic rounded squircle badge displaying `"S2"` alongside the title `"Secura AI 2.0 Workstation"` and uppercase eyebrow `"DIGITAL MEDIA FORENSICS"`.
- **System Health Indicator:** Pill badge displaying `"Local Node Active"` with a pulsating emerald status dot.
- **Theme Toggle:** Single-click toggle between light mode (`☀️ Light`) and dark mode (`🌙 Dark`), persisting dynamically to `document.documentElement` via `data-theme`.

### 3.2 Hero Drag & Drop Upload Zone
- Minimalist dashed boundary with generous $44\text{px}$ vertical padding.
- Centered Apple-style cloud upload icon.
- Concise action instructions: *"Drop image to verify authenticity"*.
- Active drag state highlights with subtle blue tint (`--accent-subtle`) and a $0.5\%$ scale elevation.

### 3.3 Active File Bar
When an image is loaded, a compact status banner replaces the dropzone, showing the filename, native resolution, filesize, and instant actions (`"Analyze Another Image"`, `"Clear"`).

### 3.4 Multi-Layer Forensic Viewport
- **Apple Segmented Pill Control:** Segmented switch allowing analysts to toggle between:
  `[ All (2×2) | Source | ELA | DCT | Residual ]`
- **Synchronized 2×2 Grid:** Displays Source raster, ELA heatmap (with recompression quality Q), DCT 8×8 boundary grid (with Blocking Artifact Ratio BAR), and High-Pass Noise Residual (with estimated SNR in dB).
- **Focused Viewport:** Seamless container rendering high-resolution overlays up to $520\text{px}$ height.

### 3.5 Unified Evidence Synthesis Card (Mission 10)
- Prominent callout box synthesizing findings across all 7 diagnostic categories.
- Component availability matrix rendering 7 diagnostic pills with completion badges.
- Expandable finding accordions displaying category, status, summary, interpretation, limitations, and benign explanations.
- Quantitative measurements rendered in formatted tabular numerals.

### 3.6 AI-Generated Image Detection Card (Mission 11 & 12)
- Architecture title and active classification head.
- Dual badges: Classification Decision (`REAL_IMAGE_CLASS`, `AI_GENERATED_CLASS`, `INCONCLUSIVE`, `UNAVAILABLE`) and Model Status (`LOADED` / `UNAVAILABLE`).
- Tabular figures for raw logit $z$ and uncalibrated sigmoid margin $\sigma(z)$.
- Transparent display of compute device, preprocessing pipeline, and mandatory scientific calibration caveats.

### 3.7 Asset Specification & Provenance Cards
- **Asset Specs:** Format, dimensions, megapixel count, color mode, and filesize.
- **C2PA Provenance:** Cryptographic manifest presence, claim generator, and assertions.
- **Metadata & Container Forensics:** Camera make/model, lens profile, software tag, orientation, timestamps, GPS privacy redactions, embedded thumbnail comparison, and container consistency observations.

### 3.8 Structured JSON Inspector & Legal Footer
- Collapsible Apple-style drawer with monospace JSON payload viewer.
- `"Copy Payload"` button with 2-second checkmark feedback.
- Centered legal disclaimer reminding analysts that spatial, frequency, and ML signals represent investigative evidence requiring multi-signal human verification.

---

## 4. Accessibility & Responsive Breakpoints

- **Responsive Stacking:** Desktop layouts ($> 1024\text{px}$) utilize a balanced $1.15\text{fr} : 0.85\text{fr}$ two-column grid. Mobile and tablet viewports stack gracefully into a single scrollable column.
- **Contrast Ratios:** All text elements exceed WCAG AA standards ($> 4.5:1$ for body text, $> 3:1$ for large headings).
- **Reduced Motion:** Interactive state transitions use brief durations ($100\text{--}200\text{ms}$) that respect system preferences.
