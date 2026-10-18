# Secura AI 2.0 — Mission 21 Motion System Specification

## 1. Principles of Forensic Motion Design
1. **Purposeful, Not Distracting**: Motion indicates real telemetry updates, playback seeking, and view switching. It never masks analyzer latency or fabricates false certainty.
2. **Accessible by Default**: Every transition respects `prefers-reduced-motion: reduce`. Animations gracefully downgrade to clean, static transitions without layout shifting.
3. **Hardware Efficient**: Visual calculations run on `<canvas>` or CSS transforms/opacity without triggering expensive DOM reflows.

---

## 2. Motion Timing & Easing Curves

| Interaction Category | Duration | Easing Function | Application |
| :--- | :--- | :--- | :--- |
| **Micro-Interactions** | `140ms` | `cubic-bezier(0.16, 1, 0.3, 1)` | Button press, badge hover, icon color shift |
| **Tab / View Transitions** | `220ms` | `cubic-bezier(0.2, 0, 0, 1)` | Switching between image tabs & workspace modes |
| **Card & Panel Reveals** | `340ms` | `cubic-bezier(0.16, 1, 0.3, 1)` | Slide-up and fade-in of analyzer evidence cards |
| **Hero Stagger Sequence** | `800ms total` | `ease-out` | Eyebrow (0ms) -> Heading (150ms) -> CTAs (300ms) -> Signal heart (450ms) |
| **RGB-Heart Pulse** | Dynamic | Signal-Bound | Driven by active video frame chroma variance |

---

## 3. Reduced Motion Support

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```
When reduced motion is enabled:
- Decorative orbital background grids freeze into subtle static hairline patterns.
- Tab switches execute as instant cross-fades.
- Heart telemetry renders real-time color vector points without pulsing wave animations.
