import React, { useEffect, useRef, useState } from "react";
import { RGBFrameSample, RGBSummary } from "../types/api";

interface RGBHeartProps {
  activeSample?: RGBFrameSample | null;
  summary?: RGBSummary | null;
  isPlaying?: boolean;
  width?: number;
  height?: number;
  showLabels?: boolean;
  interactive?: boolean;
  className?: string;
}

export const RGBHeartVisualization: React.FC<RGBHeartProps> = ({
  activeSample,
  summary,
  isPlaying = false,
  width = 340,
  height = 320,
  showLabels = true,
  interactive = true,
  className = "",
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const timeRef = useRef<number>(0);

  // Channel toggles for analytical soloing
  const [showR, setShowR] = useState(true);
  const [showG, setShowG] = useState(true);
  const [showB, setShowB] = useState(true);

  // Check reduced motion preference
  const prefersReducedMotion = useRef(
    typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches
  ).current;

  // Real data normalization or fallback to idle oscillations
  const isDataBound = Boolean(activeSample);
  const rVal = activeSample ? activeSample.r_mean : 0.58;
  const gVal = activeSample ? activeSample.g_mean : 0.44;
  const bVal = activeSample ? activeSample.b_mean : 0.38;
  const jitter = summary?.temporal_jitter_index
    ? Math.min(1.0, summary.temporal_jitter_index * 10)
    : 0.08;
  const timestampSec = activeSample?.timestamp_sec ?? 0;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Handle high DPI crispness
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    let isMounted = true;

    const render = () => {
      if (!isMounted) return;

      if (!prefersReducedMotion) {
        timeRef.current += isPlaying ? 0.045 : 0.02;
      }
      const t = timeRef.current;

      // Clear Canvas to transparent
      ctx.clearRect(0, 0, width, height);

      const centerX = width / 2;
      const centerY = height / 2 - 10;
      const baseScale = Math.min(width, height) / 38;

      // Draw faint technical coordinate circles (Warm Gray)
      ctx.strokeStyle = "rgba(129, 118, 106, 0.16)";
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 4]);
      ctx.beginPath();
      ctx.arc(centerX, centerY, baseScale * 13.5, 0, Math.PI * 2);
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(centerX, centerY, baseScale * 8, 0, Math.PI * 2);
      ctx.stroke();
      ctx.setLineDash([]);

      // Subtle Crosshair Reticle
      ctx.strokeStyle = "rgba(129, 118, 106, 0.22)";
      ctx.beginPath();
      ctx.moveTo(centerX - 16, centerY);
      ctx.lineTo(centerX + 16, centerY);
      ctx.moveTo(centerX, centerY - 16);
      ctx.lineTo(centerX, centerY + 16);
      ctx.stroke();

      // Parametric Cardioid Generator in Warm Editorial Palette
      const drawCardioidChannel = (
        color: string,
        channelIntensity: number,
        phaseOffset: number,
        pulseScale: number,
        glowColor: string,
        lineWidth: number
      ) => {
        ctx.save();
        ctx.strokeStyle = color;
        ctx.lineWidth = lineWidth;
        ctx.shadowColor = glowColor;
        ctx.shadowBlur = 10;

        ctx.beginPath();
        const steps = 180;
        const dynamicScale = baseScale * (0.94 + channelIntensity * 0.14 + Math.sin(t * 1.4 + phaseOffset) * pulseScale);

        for (let i = 0; i <= steps; i++) {
          const theta = (i / steps) * Math.PI * 2;
          const harmonicMod = 1.0 + Math.sin(theta * 6 + t * 1.8 + phaseOffset) * (jitter * 0.6);

          const rawX = 16 * Math.pow(Math.sin(theta), 3);
          const rawY = -(
            13 * Math.cos(theta) -
            5 * Math.cos(2 * theta) -
            2 * Math.cos(3 * theta) -
            Math.cos(4 * theta)
          );

          const px = centerX + rawX * dynamicScale * harmonicMod;
          const py = centerY + rawY * dynamicScale * harmonicMod;

          if (i === 0) {
            ctx.moveTo(px, py);
          } else {
            ctx.lineTo(px, py);
          }
        }

        ctx.closePath();
        ctx.stroke();
        ctx.restore();
      };

      // 1. Primary Trace: Burnt Terracotta
      if (showR) {
        drawCardioidChannel(
          "#D96B35",
          rVal,
          0.0,
          0.035 + rVal * 0.03,
          "rgba(217, 107, 53, 0.4)",
          2.6
        );
      }

      // 2. Secondary Trace: Light Mustard
      if (showG) {
        drawCardioidChannel(
          "#E8C86A",
          gVal,
          Math.PI * 0.35,
          0.045 + gVal * 0.03,
          "rgba(232, 200, 106, 0.45)",
          1.9
        );
      }

      // 3. Deep Accent Trace: Warm Amber
      if (showB) {
        drawCardioidChannel(
          "#C6A64B",
          bVal,
          Math.PI * 0.7,
          0.025 + bVal * 0.025,
          "rgba(198, 166, 75, 0.35)",
          1.4
        );
      }

      // Center Orbiting Probe Dot
      ctx.save();
      const dotTheta = t * 1.2;
      const dotRadius = baseScale * 10;
      const dotX = centerX + Math.cos(dotTheta) * dotRadius;
      const dotY = centerY + Math.sin(dotTheta) * dotRadius * 0.85;
      ctx.fillStyle = "#F28A43";
      ctx.shadowColor = "rgba(242, 138, 67, 0.6)";
      ctx.shadowBlur = 8;
      ctx.beginPath();
      ctx.arc(dotX, dotY, 3.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      animFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      isMounted = false;
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, [width, height, isPlaying, prefersReducedMotion, rVal, gVal, bVal, jitter, showR, showG, showB]);

  return (
    <div
      className={`card ${className}`}
      style={{
        display: "inline-flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "20px 24px",
        backgroundColor: "var(--bg-surface)",
        border: "1px solid var(--border-subtle)",
        borderRadius: 20,
        boxShadow: "var(--shadow-md)",
      }}
    >
      {/* Top Header & Data-Binding Status */}
      <div
        style={{
          width: "100%",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              backgroundColor: isDataBound ? "var(--color-botanical-green)" : "var(--color-mustard-deep)",
              boxShadow: isDataBound ? "0 0 8px rgba(45, 106, 79, 0.5)" : "none",
            }}
          />
          <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.04em", color: "var(--text-primary)" }}>
            {isDataBound ? "SYNCHRONIZED VIDEO DATA" : "AUTONOMOUS DEMONSTRATION"}
          </span>
        </div>
        {activeSample && (
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              color: "var(--text-secondary)",
              backgroundColor: "var(--bg-surface-secondary)",
              padding: "2px 8px",
              borderRadius: 6,
            }}
          >
            F#{activeSample.frame_index} · {timestampSec.toFixed(2)}s
          </span>
        )}
      </div>

      {/* Canvas Cardioid Drawing */}
      <div style={{ position: "relative", width, height }}>
        <canvas
          ref={canvasRef}
          style={{
            width,
            height,
            display: "block",
            borderRadius: 14,
          }}
        />
      </div>

      {/* Channel Solo Toggles & Metrics */}
      {showLabels && (
        <div
          style={{
            width: "100%",
            display: "flex",
            flexDirection: "column",
            gap: 10,
            marginTop: 14,
            paddingTop: 12,
            borderTop: "1px solid var(--border-subtle)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
            {/* Red / Terracotta Channel */}
            <button
              onClick={() => interactive && setShowR(!showR)}
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                padding: "6px 8px",
                borderRadius: 8,
                border: "1px solid",
                borderColor: showR ? "var(--color-terracotta)" : "var(--border-subtle)",
                backgroundColor: showR ? "var(--color-terracotta-subtle)" : "transparent",
                cursor: interactive ? "pointer" : "default",
                transition: "all var(--trans-quick)",
              }}
            >
              <span style={{ fontSize: 11, fontWeight: 700, color: "var(--color-terracotta)" }}>
                R-CHANNEL
              </span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>
                {(rVal * 255).toFixed(0)}
              </span>
            </button>

            {/* Green / Mustard Channel */}
            <button
              onClick={() => interactive && setShowG(!showG)}
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                padding: "6px 8px",
                borderRadius: 8,
                border: "1px solid",
                borderColor: showG ? "var(--color-mustard-deep)" : "var(--border-subtle)",
                backgroundColor: showG ? "var(--color-mustard-subtle)" : "transparent",
                cursor: interactive ? "pointer" : "default",
                transition: "all var(--trans-quick)",
              }}
            >
              <span style={{ fontSize: 11, fontWeight: 700, color: "var(--color-mustard-deep)" }}>
                G-CHANNEL
              </span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>
                {(gVal * 255).toFixed(0)}
              </span>
            </button>

            {/* Blue / Deep Amber Channel */}
            <button
              onClick={() => interactive && setShowB(!showB)}
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                padding: "6px 8px",
                borderRadius: 8,
                border: "1px solid",
                borderColor: showB ? "var(--color-espresso)" : "var(--border-subtle)",
                backgroundColor: showB ? "rgba(48, 39, 31, 0.08)" : "transparent",
                cursor: interactive ? "pointer" : "default",
                transition: "all var(--trans-quick)",
              }}
            >
              <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-primary)" }}>
                B-CHANNEL
              </span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>
                {(bVal * 255).toFixed(0)}
              </span>
            </button>
          </div>

          <div
            style={{
              fontSize: 11,
              color: "var(--text-secondary)",
              textAlign: "center",
              lineHeight: 1.4,
            }}
          >
            {isDataBound
              ? "Cardioid modulation reflects instantaneous RGB channel energy of current video frame."
              : "Demonstration mode: Illustrates periodic signal coherence across temporal intervals."}
          </div>
        </div>
      )}
    </div>
  );
};

export default RGBHeartVisualization;
