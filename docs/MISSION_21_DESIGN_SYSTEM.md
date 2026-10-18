# Secura AI 2.0 — Mission 21 Design System Specification

## 1. Design Direction: Warm Editorial Luxury
The Secura AI 2.0 interface adopts an editorial visual language:
**Warm Editorial Luxury x Cinematic Forensic Laboratory x Creative Software Workspace.**

It departs from cold monochromatic dashboards and neon glow palettes in favor of a warm, human-centered ivory, oat, and burnt terracotta aesthetic.

---

## 2. Token Palette & CSS Variables

| Token Name | Hex Code | Semantic Role |
| :--- | :--- | :--- |
| `--bg-base` | `#FAF7F0` | Warm ivory canvas background |
| `--surface-card` | `#FFFDF8` | Cream primary card and panel surface |
| `--surface-elevated` | `#FFFFFF` | Elevated modal, popover, and floating elements |
| `--surface-oat` | `#F2EBDD` | Secondary surface, wells, and nested containers |
| `--border-warm` | `#E5DCCF` | Delicate container borders and hairline dividers |
| `--terracotta` | `#D96B35` | Primary interaction accent, CTA buttons, active indicators |
| `--terracotta-hover` | `#C25B28` | Hover and active focus states for primary controls |
| `--orange-bright` | `#F28A43` | Dynamic channel signals, playback head, markers |
| `--mustard-light` | `#E8C86A` | Secondary accent, telemetry badges, informative highlights |
| `--mustard-deep` | `#C6A64B` | High-contrast borders and active tab underlines |
| `--text-primary` | `#30271F` | Dark espresso high-contrast typography |
| `--text-secondary` | `#81766A` | Warm gray descriptive copy, subtitles, metadata |
| `--text-muted` | `#A89F93` | De-emphasized labels, disabled placeholders |
| `--success-green` | `#3A7D44` | Botanical restrained green for authentic camera provenance |
| `--danger-red` | `#B83A2E` | Deep muted red for synthetic/manipulation alerts |

---

## 3. Typography System

Secura AI 2.0 uses a dual-type hierarchy:
1. **Editorial Display Serif**: `Playfair Display`, `Georgia`, `serif` for hero titles, section headlines, and major forensic verdicts.
2. **Technical Sans-Serif**: `Inter`, `-apple-system`, `BlinkMacSystemFont`, `sans-serif` for controls, metadata, telemetry grids, and filmstrip timestamps.
3. **Monospace Metric Font**: `ui-monospace`, `SFMono-Regular`, `Menlo`, `monospace` for SHA-256 hashes, timestamps, frame indexes, and numeric raw scores.

```css
/* Typography Scale */
.eyebrow {
  font-family: var(--font-sans);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--terracotta);
}

h1, .hero-title {
  font-family: var(--font-serif);
  font-size: 54px;
  line-height: 1.08;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

h2, .section-title {
  font-family: var(--font-serif);
  font-size: 32px;
  line-height: 1.2;
  font-weight: 600;
  color: var(--text-primary);
}
```

---

## 4. Reusable Core Components

### 4.1 Buttons
- `.btn-terracotta`: Primary action button with burnt terracotta fill, white text, 8px border-radius, and smooth micro-hover transition.
- `.btn-secondary`: Cream fill with `--border-warm` hairline border, dark espresso text, and oat hover state.

### 4.2 Cards
- `.card`: Primary cream surface (`#FFFDF8`), warm border (`#E5DCCF`), subtle shadow (`rgba(48, 39, 31, 0.04)`), 12px radius.
- `.card-elevated`: Pure white surface with soft drop-shadow for interactive focal points.
- `.card-oat`: Pale oat background (`#F2EBDD`) for nested technical parameter wells.

### 4.3 Forensic Badges
- `.badge-terracotta`: Tinted terracotta background with solid terracotta typography for AI alerts and high-frequency anomaly tags.
- `.badge-mustard`: Light mustard fill with deep mustard typography for uncalibrated scores and descriptive signals.
- `.badge-success`: Restrained botanical green fill for confirmed provenance and verified metadata.
- `.badge-inconclusive`: Neutral oat fill with dark espresso border for mixed or conflicting signals.

### 4.4 Forensic Workspaces
- Dual workspace modes: **Image Forensics** (8-tab deep inspection) and **Video Forensics & RGB-Heart** (multi-layer synthesis, timeline, filmstrip, 6 analyzer branches, and real-time color telemetry).
