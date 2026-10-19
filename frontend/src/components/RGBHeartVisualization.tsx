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
  width = 360,
  height = 320,
  showLabels = true,
  interactive = true,
  className = "",
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const ecgCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const timeRef = useRef<number>(0);
  const ecgHistoryRef = useRef<number[]>([]);

  // Channel toggles for analytical soloing
  const [showR, setShowR] = useState(true);
  const [showG, setShowG] = useState(true);
  const [showB, setShowB] = useState(true);

  // Check reduced motion preference
  const prefersReducedMotion = useRef(
    typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches
  ).current;

  // Normalized RGB values in [0, 1] range to avoid off-canvas projection
  const rVal = activeSample ? (activeSample.r_mean > 1.0 ? activeSample.r_mean / 255.0 : activeSample.r_mean) : 0.58;
  const gVal = activeSample ? (activeSample.g_mean > 1.0 ? activeSample.g_mean / 255.0 : activeSample.g_mean) : 0.44;
  const bVal = activeSample ? (activeSample.b_mean > 1.0 ? activeSample.b_mean / 255.0 : activeSample.b_mean) : 0.38;

  // Raw channel display values (0 to 255 scale)
  const rDisplay = Math.round(rVal * 255);
  const gDisplay = Math.round(gVal * 255);
  const bDisplay = Math.round(bVal * 255);

  const rawBpm = activeSample?.heart_rate_bpm ?? summary?.estimated_heart_rate_bpm ?? 0.0;
  const hasCardiacPulse = rawBpm >= 45.0 && rawBpm <= 160.0;
  const displayBpm = hasCardiacPulse ? rawBpm.toFixed(1) : "0.0";
  const jitter = summary?.spectral_entropy ?? 0.15;
  const timestampSec = activeSample?.timestamp_sec ?? 0;

  // 1. Cardioid Photoplethysmography Heart Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    let isMounted = true;

    const render = () => {
      if (!isMounted) return;

      if (!prefersReducedMotion) {
        // Pulse speed accelerates when playing and scales with BPM
        const bpmSpeed = hasCardiacPulse ? (rawBpm / 72.0) * 0.04 : 0.025;
        timeRef.current += isPlaying ? bpmSpeed * 1.4 : bpmSpeed;
      }
      const t = timeRef.current;

      ctx.clearRect(0, 0, width, height);

      const centerX = width / 2;
      const centerY = height / 2 - 12;
      // Controlled baseScale to keep cardioid strictly inside width/height
      const baseScale = Math.min(width, height) / 44;

      // Concentric Calibration Circles
      ctx.strokeStyle = "rgba(129, 118, 106, 0.14)";
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 4]);
      ctx.beginPath();
      ctx.arc(centerX, centerY, baseScale * 14, 0, Math.PI * 2);
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(centerX, centerY, baseScale * 8, 0, Math.PI * 2);
      ctx.stroke();
      ctx.setLineDash([]);

      // Subtle Axis Reticle
      ctx.strokeStyle = "rgba(129, 118, 106, 0.20)";
      ctx.beginPath();
      ctx.moveTo(centerX - 18, centerY);
      ctx.lineTo(centerX + 18, centerY);
      ctx.moveTo(centerX, centerY - 18);
      ctx.lineTo(centerX, centerY + 18);
      ctx.stroke();

      // Parametric Heart Cardioid Channel Function
      const drawCardioidChannel = (
        color: string,
        channelNorm: number,
        phaseOffset: number,
        pulseAmp: number,
        glowColor: string,
        lineWidth: number,
        fillGradient?: boolean
      ) => {
        ctx.save();
        ctx.strokeStyle = color;
        ctx.lineWidth = lineWidth;
        ctx.shadowColor = glowColor;
        ctx.shadowBlur = hasCardiacPulse ? 12 : 4;

        ctx.beginPath();
        const steps = 180;
        // Keep dynamicScale bounded between 0.88 and 1.15
        const pulse = hasCardiacPulse
          ? Math.sin(t * 2.8 + phaseOffset) * pulseAmp
          : Math.sin(t * 0.6) * 0.015;
        const dynamicScale = baseScale * (0.92 + channelNorm * 0.12 + pulse);

        for (let i = 0; i <= steps; i++) {
          const theta = (i / steps) * Math.PI * 2;
          const harmonicMod = 1.0 + Math.sin(theta * 6 + t * 2.0 + phaseOffset) * (Math.min(jitter, 0.08));

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

        if (fillGradient) {
          const grad = ctx.createRadialGradient(centerX, centerY, 5, centerX, centerY, baseScale * 14);
          grad.addColorStop(0, "rgba(217, 107, 53, 0.16)");
          grad.addColorStop(1, "rgba(217, 107, 53, 0.0)");
          ctx.fillStyle = grad;
          ctx.fill();
        }

        ctx.restore();
      };

      // 1. Red Channel (Primary Terracotta Arterial Wave)
      if (showR) {
        drawCardioidChannel(
          "#D96B35",
          rVal,
          0.0,
          0.065,
          "rgba(217, 107, 53, 0.55)",
          2.6,
          true
        );
      }

      // 2. Green Channel (rPPG Hemoglobin Absorption Wave)
      if (showG) {
        drawCardioidChannel(
          "#2D6A4F",
          gVal,
          Math.PI * 0.25,
          0.055,
          "rgba(45, 106, 79, 0.55)",
          2.0
        );
      }

      // 3. Blue Channel (Venous Accent)
      if (showB) {
        drawCardioidChannel(
          "#C6A64B",
          bVal,
          Math.PI * 0.50,
          0.040,
          "rgba(198, 166, 75, 0.45)",
          1.5
        );
      }

      // Orbiting Hemodynamic Photoplethysmography Dot
      ctx.save();
      const dotTheta = t * 1.6;
      const dotRadius = baseScale * 9.5;
      const dotX = centerX + Math.cos(dotTheta) * dotRadius;
      const dotY = centerY + Math.sin(dotTheta) * dotRadius * 0.88;
      ctx.fillStyle = hasCardiacPulse ? "#D96B35" : "#81766A";
      ctx.shadowColor = hasCardiacPulse ? "rgba(217, 107, 53, 0.8)" : "transparent";
      ctx.shadowBlur = 10;
      ctx.beginPath();
      ctx.arc(dotX, dotY, 4.0, 0, Math.PI * 2);
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
  }, [width, height, isPlaying, prefersReducedMotion, rVal, gVal, bVal, jitter, hasCardiacPulse, rawBpm, showR, showG, showB]);

  // 2. Live Arterial Blood Volume Pulse (rPPG Waveform) Canvas
  useEffect(() => {
    const ecgCanvas = ecgCanvasRef.current;
    if (!ecgCanvas) return;
    const ctx = ecgCanvas.getContext("2d");
    if (!ctx) return;

    const w = width;
    const h = 50;
    ecgCanvas.width = w;
    ecgCanvas.height = h;

    // Update history buffer
    const history = ecgHistoryRef.current;
    if (history.length === 0) {
      for (let i = 0; i < 100; i++) history.push(0);
    }

    // Add new pulse sample
    const t = timeRef.current;
    let newSample = 0;
    if (hasCardiacPulse) {
      // Realistic systolic/diastolic photoplethysmogram wave
      const phase = (t * 2.8) % (Math.PI * 2);
      newSample = Math.sin(phase) * 0.65 + Math.sin(phase * 2) * 0.25;
    } else {
      // Flatline with micro noise for synthetic media
      newSample = (Math.random() - 0.5) * 0.08;
    }
    history.push(newSample);
    if (history.length > 120) history.shift();

    // Draw ECG Curve
    ctx.clearRect(0, 0, w, h);
    ctx.strokeStyle = hasCardiacPulse ? "#2D6A4F" : "rgba(217, 107, 53, 0.8)";
    ctx.lineWidth = 1.8;
    ctx.beginPath();

    const dx = w / (history.length - 1);
    for (let i = 0; i < history.length; i++) {
      const x = i * dx;
      const y = h / 2 - history[i] * (h * 0.38);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Draw active scanning head
    ctx.fillStyle = hasCardiacPulse ? "#2D6A4F" : "#D96B35";
    ctx.beginPath();
    ctx.arc(w - 4, h / 2 - newSample * (h * 0.38), 3, 0, Math.PI * 2);
    ctx.fill();
  }, [width, hasCardiacPulse, rVal, gVal]);

  return (
    <div
      className={`card ${className}`}
      style={{
        display: "inline-flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "18px 22px",
        backgroundColor: "var(--bg-surface)",
        border: "1px solid var(--border-subtle)",
        borderRadius: 20,
        boxShadow: "var(--shadow-md)",
        width: width + 48,
        maxWidth: "100%",
        boxSizing: "border-box"
      }}
    >
      {/* Top Header & Cardiac Telemetry */}
      <div
        style={{
          width: "100%",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 10,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {/* Animated Beating Heart Icon */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: 32,
              height: 32,
              borderRadius: "50%",
              backgroundColor: hasCardiacPulse ? "rgba(45, 106, 79, 0.12)" : "rgba(217, 107, 53, 0.12)",
              color: hasCardiacPulse ? "#2D6A4F" : "#D96B35",
              transform: hasCardiacPulse ? "scale(1.08)" : "none",
              transition: "transform 0.15s ease-in-out"
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
            </svg>
          </div>

          <div>
            <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: "0.02em", color: "var(--text-primary)" }}>
              {hasCardiacPulse ? `${displayBpm} BPM` : "NO PULSE (SYNTHETIC)"}
            </div>
            <div style={{ fontSize: 10, color: hasCardiacPulse ? "var(--color-botanical-green)" : "var(--color-terracotta)", fontWeight: 600 }}>
              {hasCardiacPulse ? "rPPG Cardiac Hemodynamics Verified" : "Synthetic Face / Flatline Profile"}
            </div>
          </div>
        </div>

        {activeSample && (
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              color: "var(--text-secondary)",
              backgroundColor: "var(--bg-surface-secondary)",
              padding: "3px 8px",
              borderRadius: 6,
            }}
          >
            F#{activeSample.frame_index} · {timestampSec.toFixed(2)}s
          </span>
        )}
      </div>

      {/* Main Cardioid Canvas */}
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

      {/* Rhythmic rPPG Pulse Waveform Canvas */}
      <div style={{ width: "100%", marginTop: 4, marginBottom: 8 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 3 }}>
          <span style={{ fontSize: 10, fontWeight: 700, color: "var(--text-secondary)", letterSpacing: "0.04em" }}>
            HEMODYNAMIC WAVEFORM (GREEN SPECTRUM)
          </span>
          <span style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: hasCardiacPulse ? "var(--color-botanical-green)" : "var(--color-terracotta)" }}>
            {hasCardiacPulse ? "PERIODIC" : "APERIODIC"}
          </span>
        </div>
        <canvas
          ref={ecgCanvasRef}
          style={{
            width: "100%",
            height: 44,
            display: "block",
            borderRadius: 8,
            backgroundColor: "var(--bg-surface-secondary)",
            border: "1px solid var(--border-subtle)"
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
            marginTop: 4,
            paddingTop: 10,
            borderTop: "1px solid var(--border-subtle)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
            {/* Red Channel Button */}
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
                backgroundColor: showR ? "rgba(217, 107, 53, 0.12)" : "transparent",
                cursor: interactive ? "pointer" : "default",
                transition: "all var(--trans-quick)",
              }}
            >
              <span style={{ fontSize: 10, fontWeight: 700, color: "var(--color-terracotta)" }}>
                R-CHANNEL
              </span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>
                {rDisplay}
              </span>
            </button>

            {/* Green Channel Button (rPPG Heart Rate Sensor) */}
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
                borderColor: showG ? "var(--color-botanical-green)" : "var(--border-subtle)",
                backgroundColor: showG ? "rgba(45, 106, 79, 0.12)" : "transparent",
                cursor: interactive ? "pointer" : "default",
                transition: "all var(--trans-quick)",
              }}
            >
              <span style={{ fontSize: 10, fontWeight: 700, color: "var(--color-botanical-green)" }}>
                G-rPPG
              </span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>
                {gDisplay}
              </span>
            </button>

            {/* Blue Channel Button */}
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
              <span style={{ fontSize: 10, fontWeight: 700, color: "var(--text-primary)" }}>
                B-CHANNEL
              </span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>
                {bDisplay}
              </span>
            </button>
          </div>

          <div
            style={{
              fontSize: 10,
              color: "var(--text-secondary)",
              textAlign: "center",
              lineHeight: 1.4,
            }}
          >
            {hasCardiacPulse
              ? "Synchronized cardiac rhythm: Green-channel micro-absorption matches mammalian capillary pulse."
              : "Aperiodic neural signal: Absence of cardiac pulse indicates generative AI face synthesis."}
          </div>
        </div>
      )}
    </div>
  );
};

export default RGBHeartVisualization;
