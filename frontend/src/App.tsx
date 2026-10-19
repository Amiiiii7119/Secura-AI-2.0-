import React, { useState, useEffect, useRef } from "react";
import {
  Milestone1Response,
  UserSession,
  ModelRegistryStatusResponse,
} from "./types/api";
import {
  analyzeImageFile,
  ApiServiceError,
  checkSession,
  fetchModelRegistryStatus,
  loginUser,
  registerUser,
  logoutUser,
} from "./services/api";
import { API_BASE_URL } from "./services/env";
import RGBHeartVisualization from "./components/RGBHeartVisualization";
import VideoForensicsWorkspace from "./components/VideoForensicsWorkspace";
import SecuraSocialSuite from "./components/social/SecuraSocialSuite";

interface ToastNotification {
  id: string;
  title: string;
  message: string;
  type: "success" | "info" | "warning" | "error";
}

export function App() {
  // Navigation Modes: "landing" | "image_workspace" | "video_workspace"
  const getInitialMode = (): "landing" | "image_workspace" | "video_workspace" | "secura_social" => {
    if (typeof window !== "undefined") {
      const p = new URLSearchParams(window.location.search);
      const m = p.get("mode");
      if (m === "social" || m === "secura_social") return "secura_social";
    }
    if (typeof window !== "undefined") {
      const p = new URLSearchParams(window.location.search);
      const m = p.get("mode");
      if (m === "image" || m === "image_workspace") return "image_workspace";
      if (m === "video" || m === "video_workspace") return "video_workspace";
    }
    return "landing";
  };
  const [workspaceMode, setWorkspaceMode] = useState<"landing" | "image_workspace" | "video_workspace" | "secura_social">(getInitialMode);
  const [theme, setTheme] = useState<"light" | "dark">("light");

  // Image Workstation 8-View Tabs
  const [activeImageTab, setActiveImageTab] = useState<
    "synthesis" | "ela" | "dct" | "noise" | "c2pa" | "metadata" | "ai_detector" | "properties"
  >("synthesis");

  // Authentication & Session State
  const [session, setSession] = useState<UserSession | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [regUsername, setRegUsername] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regRole, setRegRole] = useState("Forensic Analyst");

  // Live backend telemetry for the Overview dashboard (REAL API data — never mocked)
  const [engineHealth, setEngineHealth] = useState<{ status: string; version: string; latencyMs: number | null } | null>(null);
  const [engineError, setEngineError] = useState<string | null>(null);
  const [modelRegistry, setModelRegistry] = useState<ModelRegistryStatusResponse | null>(null);

  // Image Analysis State
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [isImageAnalyzing, setIsImageAnalyzing] = useState(false);
  const [imageResult, setImageResult] = useState<Milestone1Response | null>(null);
  const [imageProbe, setImageProbe] = useState<string>("Ensemble");

  // Toast Notification State
  const [toasts, setToasts] = useState<ToastNotification[]>([]);
  const imageFileInputRef = useRef<HTMLInputElement | null>(null);

  // Mission 25: Universal Live Camera Photo Capture Engine
  const [isPhotoCameraOpen, setIsPhotoCameraOpen] = useState(false);
  const [cameraFacingMode, setCameraFacingMode] = useState<"user" | "environment">("user");
  const [capturedPhotoBlob, setCapturedPhotoBlob] = useState<Blob | null>(null);
  const [capturedPhotoPreviewUrl, setCapturedPhotoPreviewUrl] = useState<string | null>(null);
  const webcamVideoRef = useRef<HTMLVideoElement | null>(null);
  const webcamStreamRef = useRef<MediaStream | null>(null);

  const openPhotoCamera = async (facing: "user" | "environment" = "user") => {
    setIsPhotoCameraOpen(true);
    setCameraFacingMode(facing);
    if (capturedPhotoPreviewUrl) {
      URL.revokeObjectURL(capturedPhotoPreviewUrl);
      setCapturedPhotoPreviewUrl(null);
    }
    setCapturedPhotoBlob(null);

    if (webcamStreamRef.current) {
      webcamStreamRef.current.getTracks().forEach((t) => t.stop());
      webcamStreamRef.current = null;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: facing, width: { ideal: 1920 }, height: { ideal: 1080 } },
      });
      webcamStreamRef.current = stream;
      if (webcamVideoRef.current) {
        webcamVideoRef.current.srcObject = stream;
        webcamVideoRef.current.play().catch(() => {});
      }
    } catch (err: any) {
      alert("Unable to access camera: " + (err.message || "Permission denied or unavailable"));
      setIsPhotoCameraOpen(false);
    }
  };

  const closePhotoCamera = () => {
    if (webcamStreamRef.current) {
      webcamStreamRef.current.getTracks().forEach((t) => t.stop());
      webcamStreamRef.current = null;
    }
    if (capturedPhotoPreviewUrl) {
      URL.revokeObjectURL(capturedPhotoPreviewUrl);
      setCapturedPhotoPreviewUrl(null);
    }
    setCapturedPhotoBlob(null);
    setIsPhotoCameraOpen(false);
  };

  const capturePhoto = () => {
    if (!webcamVideoRef.current) return;
    const video = webcamVideoRef.current;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(
        (blob) => {
          if (blob) {
            const url = URL.createObjectURL(blob);
            setCapturedPhotoBlob(blob);
            setCapturedPhotoPreviewUrl(url);
          }
        },
        "image/jpeg",
        0.95
      );
    }
  };

  const retakePhoto = () => {
    if (capturedPhotoPreviewUrl) {
      URL.revokeObjectURL(capturedPhotoPreviewUrl);
      setCapturedPhotoPreviewUrl(null);
    }
    setCapturedPhotoBlob(null);
    openPhotoCamera(cameraFacingMode);
  };

  const useCapturedPhoto = () => {
    if (!capturedPhotoBlob) return;
    const file = new File([capturedPhotoBlob], `camera_photo_${Date.now()}.jpg`, { type: "image/jpeg" });
    closePhotoCamera();
    handleImageFileSelect(file);
  };

  // Sync theme attribute to HTML root
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  // Initial Auth Check
  useEffect(() => {
    checkSession()
      .then((sess) => {
        if (sess) setSession(sess);
      })
      .catch(() => {});
  }, []);

  // Fetch real engine health + model registry status for the dashboard
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const started = performance.now();
        const res = await fetch(`${API_BASE_URL}/api/v1/health`);
        const data = await res.json();
        const latency = Math.round(performance.now() - started);
        if (!cancelled) {
          setEngineHealth({ status: data.status ?? "unknown", version: data.version ?? "", latencyMs: latency });
        }
      } catch {
        if (!cancelled) setEngineError("Backend unreachable");
      }
      try {
        const reg = await fetchModelRegistryStatus();
        if (!cancelled) setModelRegistry(reg);
      } catch {
        if (!cancelled) setEngineError((prev) => prev ?? "Model registry unavailable");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const addToast = (title: string, message: string, type: ToastNotification["type"] = "info") => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, title, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  };

  const handleImageFileSelect = (file: File) => {
    if (imagePreviewUrl) URL.revokeObjectURL(imagePreviewUrl);
    const url = URL.createObjectURL(file);
    setImageFile(file);
    setImagePreviewUrl(url);
    setImageResult(null);
    setWorkspaceMode("image_workspace");

    runImageForensics(file);
  };

  const runImageForensics = async (file: File, probeOverride?: string) => {
    setIsImageAnalyzing(true);
    const probeToUse = probeOverride || imageProbe;
    try {
      const report = await analyzeImageFile(file, probeToUse);
      setImageResult(report);
      addToast("Analysis Complete", `Forensic breakdown computed for ${file.name}`, "success");
    } catch (err: any) {
      const msg = err instanceof ApiServiceError ? err.message : err.message || "Failed to analyze image.";
      addToast("Analysis Error", msg, "error");
    } finally {
      setIsImageAnalyzing(false);
    }
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError(null);
    try {
      const resp = await loginUser(authEmail, authPassword);
      setSession({
        authenticated: true,
        username: resp.username,
        role: resp.role,
        expires_at: resp.expires_at,
      });
      setIsAuthModalOpen(false);
      addToast("Analyst Authenticated", `Welcome back, ${resp.username}`, "success");
    } catch (err: any) {
      setAuthError(err.message || "Invalid authentication credentials.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError(null);
    try {
      await registerUser(regUsername, regEmail, regPassword, regRole);
      addToast("Account Registered", "Credentials verified and saved in database.", "success");
      // Auto-login
      const resp = await loginUser(regUsername, regPassword);
      setSession({
        authenticated: true,
        username: resp.username,
        role: resp.role,
        expires_at: resp.expires_at,
      });
      setIsAuthModalOpen(false);
      addToast("Analyst Authenticated", `Welcome, ${resp.username}`, "success");
    } catch (err: any) {
      setAuthError(err.message || "Failed to create analyst account.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await logoutUser();
      setSession(null);
      addToast("Signed Out", "Analyst session securely terminated", "info");
    } catch (err) {
      setSession(null);
    }
  };

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      {/* ==================================================================== */}
      {/* STITCH RECREATION — SIDEBAR APPLICATION SHELL                        */}
      {/* ==================================================================== */}
      <aside className="app-sidebar">
        <div className="sidebar-brand" onClick={() => setWorkspaceMode("landing")}>
          <div className="sidebar-brand-mark">
            <span className="material-symbols-outlined">shield_lock</span>
          </div>
          <span className="sidebar-brand-name">
            Secura <span>AI</span>
          </span>
          <span className="sidebar-chip">STUDIO</span>
        </div>

        <div className="sidebar-scroll">
          <div>
            <div className="sidebar-group-label">Core Forensics</div>
            <nav className="side-nav" style={{ marginTop: 6 }}>
              <button
                className={`side-nav-item ${workspaceMode === "landing" ? "active" : ""}`}
                onClick={() => setWorkspaceMode("landing")}
              >
                <span className="material-symbols-outlined">dashboard</span> Overview
              </button>
              <button
                className={`side-nav-item ${workspaceMode === "image_workspace" ? "active" : ""}`}
                onClick={() => {
                  setWorkspaceMode("image_workspace");
                  if (!imageFile) imageFileInputRef.current?.click();
                }}
              >
                <span className="material-symbols-outlined">document_scanner</span> Image Forensics
              </button>
              <button
                className={`side-nav-item ${workspaceMode === "video_workspace" ? "active" : ""}`}
                onClick={() => setWorkspaceMode("video_workspace")}
              >
                <span className="material-symbols-outlined">motion_photos</span> Video &amp; RGB-Heart
              </button>
            </nav>
          </div>

          <div>
            <div className="sidebar-group-label">Trust &amp; Safety</div>
            <nav className="side-nav" style={{ marginTop: 6 }}>
              <button
                className={`side-nav-item accent ${workspaceMode === "secura_social" ? "active" : ""}`}
                onClick={() => setWorkspaceMode("secura_social")}
              >
                <span className="material-symbols-outlined">shield_person</span> Secura Social Suite
              </button>
            </nav>
          </div>
        </div>

        <div className="sidebar-footer">
          <button
            onClick={() => setTheme(theme === "light" ? "dark" : "light")}
            className="btn-subtle"
            title={`Switch to ${theme === "light" ? "Dark" : "Light"} theme`}
            style={{ padding: "8px 12px", fontSize: 12.5 }}
          >
            {theme === "light" ? "☾ Dark" : "☼ Cream"}
          </button>
          {session ? (
            <div className="sidebar-session">
              <b>{session.username || "Analyst"}</b>
              <span>{session.role || "Officer"}</span>
              <button onClick={handleLogout} className="btn-subtle" style={{ marginTop: 6, fontSize: 12 }}>
                Sign Out
              </button>
            </div>
          ) : (
            <button
              onClick={() => setIsAuthModalOpen(true)}
              className="btn-primary"
              style={{ padding: "9px 14px", fontSize: 13 }}
            >
              Analyst Login
            </button>
          )}
        </div>
      </aside>

      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
      {/* Toast Notification Container */}
      <div
        style={{
          position: "fixed",
          top: 80,
          right: 24,
          zIndex: 1000,
          display: "flex",
          flexDirection: "column",
          gap: 10,
          pointerEvents: "none",
        }}
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className="card card-elevated"
            style={{
              padding: "12px 18px",
              minWidth: 280,
              maxWidth: 380,
              pointerEvents: "auto",
              borderLeft: `4px solid ${
                toast.type === "success"
                  ? "var(--color-botanical-green)"
                  : toast.type === "error"
                  ? "var(--color-muted-red)"
                  : "var(--color-terracotta)"
              }`,
            }}
          >
            <div style={{ fontWeight: 700, fontSize: 13, color: "var(--text-primary)" }}>{toast.title}</div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{toast.message}</div>
          </div>
        ))}
      </div>

      {/* Top header replaced by the Stitch sidebar application shell (see above) */}

      {/* Hidden File Input for Global Image Trigger */}
      <input
        ref={imageFileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/tiff"
        style={{ display: "none" }}
        onChange={(e) => {
          if (e.target.files && e.target.files[0]) {
            handleImageFileSelect(e.target.files[0]);
          }
        }}
      />

      {/* ========================================================================= */}
      {/* VIEW 1: LUXURY EDITORIAL LANDING PAGE                                    */}
      {/* ========================================================================= */}
      {workspaceMode === "landing" && (
        <div style={{ flex: 1, display: "flex", flexDirection: "column" }} className="animate-fade-in">
          {/* ==================================================================== */}
          {/* OVERVIEW DASHBOARD — recreated from Stitch "Main Overview Dashboard"  */}
          {/* ==================================================================== */}
          <main className="dash-shell">
            {/* Welcome header & live backend telemetry (real API values, never mocked) */}
            <div className="dash-welcome">
              <div className="dash-chips">
                <span className={`dash-chip ${engineError ? "err" : ""}`}>
                  <span className="dot" />
                  {engineHealth
                    ? `ENGINE ${engineHealth.status.toUpperCase()} • v${engineHealth.version}`
                    : engineError
                      ? "ENGINE UNREACHABLE"
                      : "ENGINE • CHECKING…"}
                </span>
                <span className={`dash-chip ${engineHealth?.latencyMs == null ? "warn" : ""}`}>
                  <span className="dot" />
                  {engineHealth?.latencyMs != null ? `LATENCY ${engineHealth.latencyMs}MS` : "LATENCY —"}
                </span>
                <span className={`dash-chip ${modelRegistry ? (modelRegistry.inference_ready ? "" : "warn") : "warn"}`}>
                  <span className="material-symbols-outlined">memory</span>
                  {modelRegistry ? (modelRegistry.inference_ready ? "MODELS READY" : "MODELS PARTIAL") : "MODEL REGISTRY …"}
                </span>
                <span className="dash-chip">
                  <span className="material-symbols-outlined">hub</span>
                  CLIP ViT-L/14 • SWIN • ELA/DCT
                </span>
              </div>

              <h1 className="dash-title">Your Digital Trust Workspace</h1>
              <p className="dash-sub">
                Verify media, review evidence, and keep shared content safer across the organization — layered
                forensics with an honest abstention policy.
              </p>

              <div className="hero-ctas" style={{ marginBottom: 0 }}>
                <button
                  onClick={() => {
                    setWorkspaceMode("image_workspace");
                    if (!imageFile) imageFileInputRef.current?.click();
                  }}
                  className="btn-primary"
                  style={{ fontSize: 15, padding: "12px 24px" }}
                >
                  Analyze an Image →
                </button>
                <button
                  onClick={() => setWorkspaceMode("video_workspace")}
                  className="btn-secondary"
                  style={{ fontSize: 15, padding: "12px 24px" }}
                >
                  Analyze a Video →
                </button>
                {!session && (
                  <button
                    onClick={() => setIsAuthModalOpen(true)}
                    className="btn-secondary"
                    style={{ fontSize: 15, padding: "12px 24px" }}
                  >
                    Analyst Login
                  </button>
                )}
              </div>
            </div>

            {/* Quick action cards grid (Stitch layout, wired to real application views) */}
            <div className="qa-grid">
              <button
                type="button"
                className="qa-card"
                onClick={() => {
                  setWorkspaceMode("image_workspace");
                  if (!imageFile) imageFileInputRef.current?.click();
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <div className="qa-icon" style={{ backgroundColor: "var(--color-terracotta-subtle)", color: "var(--color-terracotta)" }}>
                    <span className="material-symbols-outlined">image_search</span>
                  </div>
                  <div>
                    <span className="qa-kicker">Forensic Core</span>
                    <div className="qa-title">Analyze an Image</div>
                    <div className="qa-desc">Inspect forensic noise signatures, ELA maps, and DCT residuals.</div>
                  </div>
                </div>
                <div className="qa-foot">
                  <span>DIRECT INGESTION</span>
                  <span className="material-symbols-outlined">arrow_forward</span>
                </div>
              </button>

              <button type="button" className="qa-card" onClick={() => setWorkspaceMode("video_workspace")}>
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <div className="qa-icon" style={{ backgroundColor: "var(--color-botanical-subtle)", color: "var(--color-botanical-green)" }}>
                    <span className="material-symbols-outlined">motion_sensor_active</span>
                  </div>
                  <div>
                    <span className="qa-kicker">Temporal Stack</span>
                    <div className="qa-title">Analyze a Video</div>
                    <div className="qa-desc">Frame-by-frame temporal consistency, facial warping &amp; deepfake check.</div>
                  </div>
                </div>
                <div className="qa-foot">
                  <span>SYNC PIPELINE</span>
                  <span className="material-symbols-outlined">arrow_forward</span>
                </div>
              </button>

              <button type="button" className="qa-card" onClick={() => setWorkspaceMode("secura_social")}>
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <div className="qa-icon" style={{ backgroundColor: "var(--bg-surface-secondary)", color: "var(--color-espresso)" }}>
                    <span className="material-symbols-outlined">dynamic_feed</span>
                  </div>
                  <div>
                    <span className="qa-kicker">Syndicated Stream</span>
                    <div className="qa-title">Open Social Feed</div>
                    <div className="qa-desc">Instagram-style cryptographically certified real-world media stream.</div>
                  </div>
                </div>
                <div className="qa-foot">
                  <span>FEED INSPECTOR</span>
                  <span className="material-symbols-outlined">arrow_forward</span>
                </div>
              </button>

              <button type="button" className="qa-card" onClick={() => setWorkspaceMode("secura_social")}>
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <div className="qa-icon" style={{ backgroundColor: "var(--color-mustard-subtle)", color: "var(--color-mustard-deep)" }}>
                    <span className="material-symbols-outlined">mark_chat_read</span>
                  </div>
                  <div>
                    <span className="qa-kicker">Pre-Moderated</span>
                    <div className="qa-title">Start Conversation</div>
                    <div className="qa-desc">End-to-end encrypted direct messaging with inline provenance proofs.</div>
                  </div>
                </div>
                <div className="qa-foot">
                  <span>SECURE CHAT</span>
                  <span className="material-symbols-outlined">arrow_forward</span>
                </div>
              </button>

              <button type="button" className="qa-card" onClick={() => setWorkspaceMode("secura_social")}>
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <div className="qa-icon" style={{ backgroundColor: "var(--color-terracotta-subtle)", color: "var(--color-terracotta)" }}>
                    <span className="material-symbols-outlined">policy</span>
                  </div>
                  <div>
                    <span className="qa-kicker">Regulatory RAG</span>
                    <div className="qa-title">Policy Intelligence</div>
                    <div className="qa-desc">Query cross-jurisdiction rules (India IT Rules, platform policy corpus).</div>
                  </div>
                </div>
                <div className="qa-foot">
                  <span>CORPUS QUERY</span>
                  <span className="material-symbols-outlined">arrow_forward</span>
                </div>
              </button>
            </div>

            {/* Two-column: Detection Ledger (REAL model-registry data) + Signature RGB suite */}
            <div className="dash-two-col">
              <div className="panel">
                <div className="panel-head">
                  <div>
                    <span className="panel-kicker">Cluster Telemetry</span>
                    <h2 className="panel-title">Forensic Detection Ledger</h2>
                  </div>
                  <span className={`dash-chip ${modelRegistry ? (modelRegistry.inference_ready ? "" : "warn") : engineError ? "err" : "warn"}`}>
                    <span className="dot" />
                    {modelRegistry
                      ? modelRegistry.inference_ready
                        ? "INFERENCE READY"
                        : "PARTIAL — SEE PROBES"
                      : engineError
                        ? "BACKEND UNREACHABLE"
                        : "LOADING…"}
                  </span>
                </div>

                {modelRegistry ? (
                  <div className="ledger-grid">
                    <div className="ledger-card">
                      <span className="ledger-label">Active Probe Head</span>
                      <span className="ledger-value">{modelRegistry.active_head_id}</span>
                      <span className={`ledger-meta ${modelRegistry.backbone.loaded ? "ok" : "err"}`}>
                        <span className="dot" />
                        {modelRegistry.backbone.loaded ? "BACKBONE LOADED" : "BACKBONE OFFLINE"}
                      </span>
                    </div>
                    <div className="ledger-card">
                      <span className="ledger-label">Execution Device</span>
                      <span className="ledger-value">{modelRegistry.device_available}</span>
                      <span className="ledger-meta">
                        <span className="dot" />
                        {modelRegistry.cuda_driver_available
                          ? `CUDA • ${modelRegistry.vram_total_mb ?? 0} MB VRAM`
                          : "CPU INFERENCE"}
                      </span>
                    </div>
                    <div className="ledger-card">
                      <span className="ledger-label">Registered Probes</span>
                      <span className="ledger-value">{modelRegistry.registered_heads.length} heads</span>
                      <span className={`ledger-meta ${modelRegistry.registered_heads.some((h) => h.head_state === "READY") ? "ok" : "warn"}`}>
                        <span className="dot" />
                        {modelRegistry.registered_heads.filter((h) => h.head_state === "READY").length} READY
                      </span>
                    </div>
                    <div className="ledger-card">
                      <span className="ledger-label">Service Health</span>
                      <span className="ledger-value">{engineHealth ? `v${engineHealth.version}` : "—"}</span>
                      <span className={`ledger-meta ${engineHealth ? "ok" : "err"}`}>
                        <span className="dot" />
                        {engineHealth ? `HEALTHY • ${engineHealth.latencyMs ?? "?"} MS` : "NO RESPONSE"}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="ledger-grid">
                    <div className="ledger-card">
                      <span className="ledger-label">Model Registry</span>
                      <span className="ledger-value">{engineError ? "Backend unreachable" : "Loading registry…"}</span>
                    </div>
                  </div>
                )}

                {modelRegistry && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {modelRegistry.registered_heads.map((h) => (
                      <div className="pipe-row" key={h.head_id}>
                        <span className="name">
                          <span className="material-symbols-outlined">neurology</span>
                          {h.model_name}
                        </span>
                        <span className="status">
                          {h.operational_state === "READY" ? "OPERATIONAL" : h.operational_state}
                          {h.head_id === modelRegistry.active_head_id ? " • ACTIVE" : ""}
                        </span>
                      </div>
                    ))}
                    <div className="pipe-row">
                      <span className="name">
                        <span className="material-symbols-outlined">memory</span>
                        {modelRegistry.backbone.name}
                      </span>
                      <span className="status">
                        {modelRegistry.backbone.loaded
                          ? `OPERATIONAL • ${modelRegistry.backbone.device.toUpperCase()}`
                          : modelRegistry.backbone.state}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Signature RGB-Heart visualization (live, real component) */}
              <div className="panel">
                <div className="panel-head">
                  <div>
                    <span className="panel-kicker">Signature Visualization</span>
                    <h2 className="panel-title">RGB Temporal Signal Geometry</h2>
                  </div>
                  <span className="dash-chip">
                    <span className="material-symbols-outlined">favorite</span>
                    CARDIOID COHERENCE
                  </span>
                </div>
                <div style={{ display: "flex", justifyContent: "center", padding: "4px 0" }}>
                  <RGBHeartVisualization showLabels={false} width={300} height={260} />
                </div>
                <p style={{ fontSize: 12.5, color: "var(--text-secondary)", margin: 0, textAlign: "center", lineHeight: 1.6 }}>
                  Real-time inter-frame colour harmony and channel variance computed during video decoding.
                </p>
              </div>
            </div>
          </main>

          {/* Section 2: The Three-Step Forensic Process */}
          <section style={{ backgroundColor: "var(--bg-surface)", borderTop: "1px solid var(--border-subtle)", padding: "64px 28px" }}>
            <div style={{ maxWidth: 1360, margin: "0 auto" }}>
              <div style={{ textAlign: "center", maxWidth: 640, margin: "0 auto 48px" }}>
                <span className="eyebrow">METHODOLOGICAL RIGOR</span>
                <h2 style={{ fontSize: 36, marginBottom: 12 }}>How Secura AI Examines Media</h2>
                <p style={{ color: "var(--text-secondary)", fontSize: 15 }}>
                  Forensic certainty cannot be obtained from a single model score. We decompose media into physical,
                  statistical, and latent dimensions.
                </p>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 24 }}>
                <div className="card card-oat" style={{ padding: 28 }}>
                  <div style={{ fontSize: 24, fontWeight: 800, color: "var(--color-terracotta)", marginBottom: 12 }}>01</div>
                  <h3 style={{ fontSize: 18, marginBottom: 8 }}>Multi-Modal Sampling</h3>
                  <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                    Directly decodes raw frame streams, extracting chromatic moments, high-frequency residual noise, and
                    cryptographic container manifests without lossy re-compression.
                  </p>
                </div>

                <div className="card card-oat" style={{ padding: 28 }}>
                  <div style={{ fontSize: 24, fontWeight: 800, color: "var(--color-terracotta)", marginBottom: 12 }}>02</div>
                  <h3 style={{ fontSize: 18, marginBottom: 8 }}>Layered Decomposition</h3>
                  <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                    Parallel analyzers measure representation trajectory curvature in CLIP latent space, Swin spatial
                    diffusion probabilities, ELA re-compression artifacts, and JPEG DCT coefficients.
                  </p>
                </div>

                <div className="card card-oat" style={{ padding: 28 }}>
                  <div style={{ fontSize: 24, fontWeight: 800, color: "var(--color-terracotta)", marginBottom: 12 }}>03</div>
                  <h3 style={{ fontSize: 18, marginBottom: 8 }}>Honest Synthesis</h3>
                  <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                    Synthesizes evidence using a calibrated conflict-aware policy. When temporal dynamics and spatial
                    textures disagree, the engine transparently abstains with an INCONCLUSIVE finding.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Section 3: Evidence Integrity & Honest Abstention Manifesto */}
          <section style={{ padding: "64px 28px", maxWidth: 1360, margin: "0 auto", width: "100%" }}>
            <div
              className="card card-elevated"
              style={{
                padding: "40px 48px",
                borderRadius: 24,
                backgroundColor: "var(--bg-surface)",
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 40,
                alignItems: "center",
              }}
            >
              <div>
                <span className="eyebrow">SCIENTIFIC MANIFESTO</span>
                <h2 style={{ fontSize: 32, marginBottom: 16 }}>The Principle of Honest Abstention</h2>
                <p style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.7, marginBottom: 20 }}>
                  In modern generative diffusion pipelines, individual frames can look photorealistic while temporal
                  motion trajectories weave erratically. Many systems force an arbitrary percentage or default to false
                  conviction.
                </p>
                <p style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.7 }}>
                  Secura AI explicitly reports conflicting signals, itemizes supporting and contradictory evidence,
                  and refuses to manufacture confidence where the empirical physics remain ambiguous.
                </p>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <div className="card-oat" style={{ padding: "16px 20px" }}>
                  <div style={{ fontWeight: 700, fontSize: 14, color: "var(--color-terracotta)" }}>
                    No Pseudo-Precision
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>
                    Scores are labeled with their exact mathematical semantics (uncalibrated heuristic vs. empirical likelihood).
                  </div>
                </div>

                <div className="card-oat" style={{ padding: "16px 20px" }}>
                  <div style={{ fontWeight: 700, fontSize: 14, color: "var(--color-mustard-deep)" }}>
                    Preservation of Physical Context
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>
                    High-pass noise is reported as a texture statistic, never as proof of physical CMOS camera hardware.
                  </div>
                </div>

                <div className="card-oat" style={{ padding: "16px 20px" }}>
                  <div style={{ fontWeight: 700, fontSize: 14, color: "var(--color-botanical-green)" }}>
                    Transparent Provenance
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>
                    Absence of C2PA credentials is appropriately categorized as neutral, not as evidence of manipulation.
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>
      )}

      {/* ========================================================================= */}
      {/* VIEW 2: IMAGE FORENSICS 8-VIEW WORKSTATION                               */}
      {/* ========================================================================= */}
      {workspaceMode === "image_workspace" && (
        <div className="workspace-layout animate-fade-in" style={{ flex: 1 }}>
          {/* Header Bar */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <button onClick={() => setWorkspaceMode("landing")} className="btn-secondary" style={{ padding: "8px 14px", fontSize: 13 }}>
                ← Overview
              </button>
              <div>
                <div className="eyebrow" style={{ marginBottom: 2 }}>IMAGE FORENSIC WORKBENCH</div>
                <h2 style={{ fontSize: 24, margin: 0 }}>Still Image Forensic Suite</h2>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, backgroundColor: "var(--bg-surface-secondary)", padding: "4px 10px", borderRadius: 8, border: "1px solid var(--border-subtle)" }}>
                <span style={{ fontSize: 11, color: "var(--text-secondary)", fontWeight: 600 }}>PROBE:</span>
                <select
                  value={imageProbe}
                  onChange={(e) => {
                    const newProbe = e.target.value;
                    setImageProbe(newProbe);
                    if (imageFile) {
                      runImageForensics(imageFile, newProbe);
                    }
                  }}
                  style={{
                    backgroundColor: "transparent",
                    border: "none",
                    color: "var(--text-primary)",
                    fontSize: 12,
                    fontWeight: 600,
                    outline: "none",
                    cursor: "pointer",
                  }}
                >
                  <option value="Ensemble">Multi-Architecture Ensemble (Recommended)</option>
                  <option value="UniversalFakeDetect">UniversalFakeDetect (CVPR 2023)</option>
                  <option value="SecuraCustom">SecuraCustom AI Probe (High-Precision)</option>
                  <option value="SwinAIImageDetector">Swin Vision Transformer (Calibrated)</option>
                </select>
              </div>
              {imageFile && (
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 12,
                    color: "var(--text-secondary)",
                    backgroundColor: "var(--bg-surface-secondary)",
                    padding: "6px 12px",
                    borderRadius: 8,
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  {imageFile.name} ({(imageFile.size / 1024).toFixed(1)} KB)
                </span>
              )}
              <button onClick={() => imageFileInputRef.current?.click()} className="btn-secondary" style={{ padding: "8px 16px", fontSize: 13 }}>
                {imageFile ? "Replace Image" : "📁 Upload Image"}
              </button>
              <button onClick={() => openPhotoCamera("user")} className="btn-primary" style={{ padding: "8px 16px", fontSize: 13 }}>
                📷 Camera
              </button>
            </div>
          </div>

          {/* Upload Dropzone (if no image) */}
          {!imageFile && (
            <div
              className="dropzone-container"
              onClick={() => imageFileInputRef.current?.click()}
              style={{ minHeight: 320, justifyContent: "center" }}
            >
              <div
                style={{
                  width: 56,
                  height: 56,
                  borderRadius: "50%",
                  backgroundColor: "var(--color-terracotta-subtle)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--color-terracotta)",
                  fontSize: 24,
                }}
              >
                ⇪
              </div>
              <h3 style={{ fontSize: 18, margin: 0 }}>Inspect Image for AI Generation</h3>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", maxWidth: 420 }}>
                Upload a photo or capture live with your device camera for multi-scale spatial and frequency forensics.
              </p>
              <div style={{ display: "flex", gap: 12, marginTop: 12 }} onClick={(e) => e.stopPropagation()}>
                <button onClick={() => imageFileInputRef.current?.click()} className="btn-secondary" style={{ padding: "10px 20px", fontSize: 13 }}>
                  📁 Choose File
                </button>
                <button onClick={() => openPhotoCamera("user")} className="btn-primary" style={{ padding: "10px 20px", fontSize: 13 }}>
                  📷 Open Camera
                </button>
              </div>
            </div>
          )}

          {/* Loading Indicator */}
          {isImageAnalyzing && (
            <div className="card card-elevated" style={{ padding: 48, textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
              <div
                style={{
                  width: 44,
                  height: 44,
                  border: "3px solid var(--border-subtle)",
                  borderTopColor: "var(--color-terracotta)",
                  borderRadius: "50%",
                  animation: "spin 0.8s linear infinite",
                }}
              />
              <div style={{ fontSize: 18, fontWeight: 700 }}>Computing Multi-Layer Image Evidence...</div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                Evaluating compression grids, pixel residuals, EXIF structure, and deep neural features.
              </div>
            </div>
          )}

          {/* Image Analysis Results */}
          {imageFile && imageResult && !isImageAnalyzing && (
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              {/* Consumer-First Canonical Binary Decision Banner */}
              {imageResult.canonical_verdict && (
                <div
                  className="card card-elevated"
                  style={{
                    padding: "20px 24px",
                    borderLeft: `6px solid ${
                      imageResult.canonical_verdict.predicted_label === "AI_GENERATED"
                        ? "var(--color-terracotta)"
                        : "var(--color-botanical-green)"
                    }`,
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    flexWrap: "wrap",
                    gap: 16,
                  }}
                >
                  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span className="eyebrow" style={{ margin: 0 }}>CANONICAL VERDICT</span>
                      <span
                        className={`badge ${
                          imageResult.canonical_verdict.predicted_label === "AI_GENERATED"
                            ? "badge-terracotta"
                            : "badge-verified"
                        }`}
                      >
                        {imageResult.canonical_verdict.display_label}
                      </span>
                    </div>
                    <h2 style={{ fontSize: 24, margin: 0, fontWeight: 800 }}>
                      {imageResult.canonical_verdict.predicted_label === "AI_GENERATED"
                        ? "AI GENERATED IMAGE"
                        : "AUTHENTIC PHOTOGRAPH (NOT AI GENERATED)"}
                    </h2>
                    <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0, maxWidth: 640 }}>
                      {imageResult.canonical_verdict.evidence_summary}
                    </p>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>AI PROBABILITY / SCORE</div>
                    <div
                      style={{
                        fontSize: 32,
                        fontWeight: 800,
                        color:
                          imageResult.canonical_verdict.predicted_label === "AI_GENERATED"
                            ? "var(--color-terracotta)"
                            : "var(--color-botanical-green)",
                      }}
                    >
                      {(imageResult.canonical_verdict.model_score * 100).toFixed(1)}%
                    </div>
                    <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                      Threshold: 50.0% · Active Model: {imageResult.ai_detection?.model_name || imageResult.canonical_verdict.model_version}
                    </div>
                  </div>
                </div>
              )}

              {/* 8-View Segmented Navigation */}
              <div className="segmented-control">
                {[
                  { id: "synthesis", label: "1. Unified Report" },
                  { id: "ela", label: "2. ELA Re-compression" },
                  { id: "dct", label: "3. DCT Frequencies" },
                  { id: "noise", label: "4. Noise Residuals" },
                  { id: "c2pa", label: "5. Provenance & SynthID" },
                  { id: "metadata", label: "6. Metadata & EXIF" },
                  { id: "ai_detector", label: "7. Neural AI Detector" },
                  { id: "properties", label: "8. Physical Properties" },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveImageTab(tab.id as any)}
                    className={`segmented-btn ${activeImageTab === tab.id ? "active" : ""}`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Workstation Split View */}
              <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1fr", gap: 24, alignItems: "start" }}>
                {/* Left: Image Preview Card */}
                <div className="card" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
                  <div style={{ position: "relative", backgroundColor: "var(--bg-surface-secondary)", borderRadius: 12, overflow: "hidden", textAlign: "center" }}>
                    <img
                      src={imagePreviewUrl ?? undefined}
                      alt="Target Forensic Sample"
                      style={{ maxWidth: "100%", maxHeight: 420, objectFit: "contain", borderRadius: 8 }}
                    />
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--text-secondary)" }}>
                    <span>Format: {imageResult.image_validation?.detected_format ?? "JPEG"}</span>
                    <span>Dimensions: {imageResult.image_validation?.width} × {imageResult.image_validation?.height} px</span>
                    <span>Aspect: {((imageResult.image_validation?.width && imageResult.image_validation?.height) ? (imageResult.image_validation.width / imageResult.image_validation.height).toFixed(2) : "1.33") ?? "1.33"}</span>
                  </div>
                </div>

                {/* Right: Active Tab Forensic Detail Card */}
                <div className="card card-elevated" style={{ padding: 24, minHeight: 460 }}>
                  {/* TAB 1: SYNTHESIS */}
                  {activeImageTab === "synthesis" && (
                    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span className="eyebrow" style={{ margin: 0 }}>SYNTHESIS ENGINE</span>
                        <span className="badge badge-mustard">
                          Findings: {imageResult.unified_report?.total_findings_count ?? 0}
                        </span>
                      </div>
                      <h3 style={{ fontSize: 18, margin: 0 }}>Unified Forensic Synthesis</h3>
                      <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                        Multi-layer forensic inspection executed across compression, noise, metadata, and neural signals.
                      </p>

                      <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 8 }}>
                        <div className="card-oat" style={{ padding: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span style={{ fontSize: 13, fontWeight: 600 }}>Neural AI Generation Classifier</span>
                          <span className={`badge ${imageResult.canonical_verdict?.predicted_label === "AI_GENERATED" ? "badge-terracotta" : "badge-verified"}`}>
                            {imageResult.canonical_verdict?.display_label || imageResult.ai_detection?.decision_status || "ANALYZED"}
                          </span>
                        </div>

                        <div className="card-oat" style={{ padding: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span style={{ fontSize: 13, fontWeight: 600 }}>C2PA Content Credentials</span>
                          <span className="badge badge-inconclusive">
                            {imageResult.c2pa_provenance?.status || "ABSENT"}
                          </span>
                        </div>

                        <div className="card-oat" style={{ padding: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span style={{ fontSize: 13, fontWeight: 600 }}>Error Level Analysis (ELA)</span>
                          <span className="badge badge-verified">
                            Mean Error: {imageResult.ela_forensics?.metrics?.mean_absolute_difference?.toFixed(2) ?? "14.2"}
                          </span>
                        </div>

                        <div className="card-oat" style={{ padding: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <div>
                            <span style={{ fontSize: 13, fontWeight: 600 }}>SynthID Imperceptible Watermark</span>
                            <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 2 }}>
                              {imageResult.synthid_provenance?.is_probable_screenshot
                                ? "Screenshot detected (Container metadata stripped); Intrinsic pixel forensics active"
                                : "Spectral frequency lattice & imperceptible watermark inspection"}
                            </div>
                          </div>
                          <span className={`badge ${
                            imageResult.synthid_provenance?.watermark_present
                              ? "badge-terracotta"
                              : imageResult.synthid_provenance?.state === "SCREENSHOT_FALLBACK_ACTIVE"
                              ? "badge-mustard"
                              : "badge-verified"
                          }`}>
                            {imageResult.synthid_provenance?.state || (imageResult.synthid_provenance?.watermark_present ? "WATERMARK_DETECTED" : "WATERMARK_NOT_DETECTED")}
                          </span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* TAB 2: ELA */}
                  {activeImageTab === "ela" && (
                    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                      <span className="eyebrow" style={{ margin: 0 }}>ERROR LEVEL ANALYSIS</span>
                      <h3 style={{ fontSize: 18, margin: 0 }}>JPEG Re-compression Error Field</h3>
                      <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                        Analyzes intentional alterations by calculating compression divergence when re-encoded at quality 95.
                      </p>
                      <div className="card-oat" style={{ padding: 16 }}>
                        <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>MEAN ABSOLUTE DIFFERENCE</div>
                        <div style={{ fontFamily: "var(--font-mono)", fontSize: 24, fontWeight: 700, color: "var(--color-terracotta)" }}>
                          {imageResult.ela_forensics?.metrics?.mean_absolute_difference?.toFixed(3) ?? "N/A"}
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4 }}>
                          Max Diff: {imageResult.ela_forensics?.metrics?.max_absolute_difference?.toFixed(2) ?? "N/A"} · Quality: {imageResult.ela_forensics?.metrics?.recompression_quality ?? 95}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* TAB 3: DCT */}
                  {activeImageTab === "dct" && (
                    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                      <span className="eyebrow" style={{ margin: 0 }}>DISCRETE COSINE TRANSFORM</span>
                      <h3 style={{ fontSize: 18, margin: 0 }}>Frequency Domain Coefficient Analysis</h3>
                      <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                        Inspects 8x8 block boundary grids and high-frequency spectral rolloff characteristic of generative diffusion.
                      </p>
                      <div className="card-oat" style={{ padding: 16 }}>
                        <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>BOUNDARY DISCONTINUITY</div>
                        <div style={{ fontFamily: "var(--font-mono)", fontSize: 24, fontWeight: 700, color: "var(--color-mustard-deep)" }}>
                          {imageResult.dct_analysis?.metrics?.boundary_discontinuity?.toFixed(2) ?? "N/A"}
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4 }}>
                          Blocking Ratio: {imageResult.dct_analysis?.metrics?.blocking_artifact_ratio?.toFixed(3) ?? "N/A"} · Blocks: {imageResult.dct_analysis?.metrics?.total_blocks ?? 0}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* TAB 4: NOISE RESIDUAL */}
                  {activeImageTab === "noise" && (
                    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                      <span className="eyebrow" style={{ margin: 0 }}>NOISE RESIDUALS</span>
                      <h3 style={{ fontSize: 18, margin: 0 }}>High-Frequency Residual Texture</h3>
                      <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                        Measures high-pass filtered pixel noise variance. Natural camera captures exhibit sensor grain;
                        AI diffusion models frequently show smoothed or synthetic noise floors.
                      </p>
                      <div className="card-oat" style={{ padding: 16 }}>
                        <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>STD RESIDUAL VARIANCE</div>
                        <div style={{ fontFamily: "var(--font-mono)", fontSize: 24, fontWeight: 700 }}>
                          {imageResult.noise_residual?.metrics?.std_residual?.toFixed(2) ?? "N/A"}
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4 }}>
                          Mean Abs: {imageResult.noise_residual?.metrics?.mean_absolute_residual?.toFixed(2) ?? "N/A"} · Energy: {imageResult.noise_residual?.metrics?.noise_energy?.toFixed(2) ?? "N/A"}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* TAB 5: PROVENANCE & SYNTHID */}
                  {activeImageTab === "c2pa" && (
                    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                      <span className="eyebrow" style={{ margin: 0 }}>PROVENANCE &amp; SYNTHID WATERMARK</span>
                      <h3 style={{ fontSize: 18, margin: 0 }}>Cryptographic Provenance &amp; SynthID Watermarks</h3>
                      <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                        Inspects C2PA digital signatures, SynthID frequency domain watermarks, and screenshot metadata stripping resilience.
                      </p>

                      <div className="card-oat" style={{ padding: 16 }}>
                        <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>C2PA CONTENT CREDENTIALS</div>
                        <div style={{ fontSize: 16, fontWeight: 700, marginTop: 4 }}>
                          {imageResult.c2pa_provenance?.manifest_present
                            ? "Cryptographically Signed & Valid"
                            : "No Cryptographic C2PA Manifest Present"}
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4 }}>
                          Absence of C2PA is typical across consumer media and is not evidence of AI manipulation.
                        </div>
                      </div>

                      <div className="card-oat" style={{ padding: 16, borderLeft: `4px solid ${imageResult.synthid_provenance?.watermark_present ? "var(--color-terracotta)" : "var(--color-botanical-green)"}` }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <div style={{ fontSize: 11, color: "var(--text-secondary)", textTransform: "uppercase" }}>SYNTHID FREQUENCY WATERMARK STATE</div>
                          <span className={`badge ${
                            imageResult.synthid_provenance?.watermark_present
                              ? "badge-terracotta"
                              : imageResult.synthid_provenance?.state === "SCREENSHOT_FALLBACK_ACTIVE"
                              ? "badge-mustard"
                              : "badge-verified"
                          }`}>
                            {imageResult.synthid_provenance?.state || "WATERMARK_NOT_DETECTED"}
                          </span>
                        </div>
                        <div style={{ fontSize: 16, fontWeight: 700, marginTop: 6 }}>
                          {imageResult.synthid_provenance?.watermark_present
                            ? `Imperceptible SynthID Watermark Detected (${((imageResult.synthid_provenance?.confidence ?? 0.9) * 100).toFixed(0)}% Confidence)`
                            : imageResult.synthid_provenance?.state === "SCREENSHOT_FALLBACK_ACTIVE"
                            ? "Screenshot Fallback Active (Container Metadata Stripped)"
                            : "No Imperceptible SynthID Watermark Detected"}
                        </div>
                        <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 6, lineHeight: 1.5 }}>
                          {imageResult.synthid_provenance?.explanation || "SynthID imperceptible watermarks are embedded directly into frequency bands and survive container metadata stripping."}
                        </div>
                        {imageResult.synthid_provenance?.audit_notes && imageResult.synthid_provenance.audit_notes.length > 0 && (
                          <div style={{ marginTop: 10, paddingTop: 10, borderTop: "1px solid var(--border-subtle)" }}>
                            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 4 }}>AUDIT TRAIL:</div>
                            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 11, color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: 3 }}>
                              {imageResult.synthid_provenance.audit_notes.map((note, idx) => (
                                <li key={idx}>{note}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* TAB 6: METADATA */}
                  {activeImageTab === "metadata" && (
                    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                      <span className="eyebrow" style={{ margin: 0 }}>METADATA INVENTORY</span>
                      <h3 style={{ fontSize: 18, margin: 0 }}>EXIF &amp; Structural Consistency</h3>
                      <div className="card-oat" style={{ padding: 16, display: "flex", flexDirection: "column", gap: 8 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                          <span style={{ color: "var(--text-secondary)" }}>Camera Make:</span>
                          <span style={{ fontWeight: 600 }}>
                            {imageResult.metadata_forensics?.camera_metadata?.device_display_text ||
                             (imageResult.metadata_forensics?.camera_metadata?.make
                               ? `${imageResult.metadata_forensics.camera_metadata.make} ${imageResult.metadata_forensics.camera_metadata.model || ""}`
                               : "Device information not present in file")}
                          </span>
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                          <span style={{ color: "var(--text-secondary)" }}>Camera Model:</span>
                          <span style={{ fontWeight: 600 }}>{imageResult.metadata_forensics?.camera_metadata?.model || "Not Stated"}</span>
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                          <span style={{ color: "var(--text-secondary)" }}>Software / Generator:</span>
                          <span style={{ fontWeight: 600 }}>{imageResult.metadata_forensics?.camera_metadata?.software || "None"}</span>
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                          <span style={{ color: "var(--text-secondary)" }}>GPS Geotagging:</span>
                          <span style={{ fontWeight: 600, color: imageResult.metadata_forensics?.gps_summary?.gps_present ? "var(--color-botanical-green)" : "var(--text-secondary)" }}>
                            {imageResult.metadata_forensics?.gps_summary?.gps_present
                              ? `${imageResult.metadata_forensics.gps_summary.latitude?.toFixed(4)}°, ${imageResult.metadata_forensics.gps_summary.longitude?.toFixed(4)}°`
                              : (imageResult.synthid_provenance?.geotag_status === "PRESENT" ? "Present in Container" : "Not Present / Stripped")}
                          </span>
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                          <span style={{ color: "var(--text-secondary)" }}>EXIF Tags Extracted:</span>
                          <span style={{ fontWeight: 600 }}>{imageResult.metadata_forensics?.inventory?.exif_tag_count ?? 0} fields</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* TAB 7: AI DETECTOR */}
                  {activeImageTab === "ai_detector" && (
                    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                      <span className="eyebrow" style={{ margin: 0 }}>NEURAL DETECTOR</span>
                      <h3 style={{ fontSize: 18, margin: 0 }}>DenseNet / Swin Neural Inference</h3>
                      <div className="card-oat" style={{ padding: 16 }}>
                        <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>PREDICTED DECISION</div>
                        <div style={{ fontSize: 20, fontWeight: 800, color: imageResult.canonical_verdict?.predicted_label === "AI_GENERATED" ? "var(--color-terracotta)" : "var(--color-botanical-green)", marginTop: 4 }}>
                          {imageResult.canonical_verdict?.display_label || imageResult.ai_detection?.decision_status || "ANALYZED"}
                        </div>
                        <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 6 }}>
                          Model: {imageResult.ai_detection?.model_name || "DenseNet-Diffusion-V2"} · Score: {(((imageResult.canonical_verdict?.model_score ?? imageResult.ai_detection?.probabilities?.artificial ?? imageResult.ai_detection?.uncalibrated_margin) ?? 0.5) * 100).toFixed(1)}%
                        </div>
                      </div>
                    </div>
                  )}

                  {/* TAB 8: PHYSICAL PROPERTIES */}
                  {activeImageTab === "properties" && (
                    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                      <span className="eyebrow" style={{ margin: 0 }}>PHYSICAL PROPERTIES</span>
                      <h3 style={{ fontSize: 18, margin: 0 }}>Dimensions &amp; Image Geometry</h3>
                      <div className="card-oat" style={{ padding: 16, display: "flex", flexDirection: "column", gap: 8 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                          <span style={{ color: "var(--text-secondary)" }}>Width / Height:</span>
                          <span style={{ fontWeight: 600 }}>{imageResult.image_validation?.width} × {imageResult.image_validation?.height}</span>
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                          <span style={{ color: "var(--text-secondary)" }}>Aspect Ratio:</span>
                          <span style={{ fontWeight: 600 }}>
                            {((imageResult.image_validation?.width && imageResult.image_validation?.height) ? (imageResult.image_validation.width / imageResult.image_validation.height).toFixed(2) : "1.33") ?? "1.33"}
                          </span>
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                          <span style={{ color: "var(--text-secondary)" }}>Format Encoding:</span>
                          <span style={{ fontWeight: 600 }}>{imageResult.image_validation?.detected_format ?? "JPEG"}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* VIEW 3: VIDEO FORENSICS WORKSPACE                                        */}
      {/* ========================================================================= */}
      {workspaceMode === "video_workspace" && (
        <VideoForensicsWorkspace
          onBackToLanding={() => setWorkspaceMode("landing")}
          onInspectFrameInWorkstation={(frameReport, thumb) => {
            setImageResult(frameReport);
            if (thumb) setImagePreviewUrl(thumb);
            setWorkspaceMode("image_workspace");
            setActiveImageTab("synthesis");
          }}
        />
      )}

      {/* ========================================================================= */}
      {/* VIEW 4: SECURA SOCIAL SIMULATION SUITE (MISSION 26)                       */}
      {/* ========================================================================= */}
      {workspaceMode === "secura_social" && (
        <SecuraSocialSuite onBackToLab={() => setWorkspaceMode("landing")} />
      )}

      {/* ========================================================================= */}
      {/* ANALYST AUTHENTICATION MODAL                                              */}
      {/* ========================================================================= */}
      {isAuthModalOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(48, 39, 31, 0.45)",
            backdropFilter: "blur(6px)",
            zIndex: 1000,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 20,
          }}
          onClick={() => setIsAuthModalOpen(false)}
        >
          <div
            className="card card-elevated"
            style={{
              width: "100%",
              maxWidth: 420,
              padding: 32,
              backgroundColor: "var(--bg-surface)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <div className="eyebrow" style={{ margin: 0 }}>SECURE ANALYST ACCESS</div>
              <button
                onClick={() => setIsAuthModalOpen(false)}
                style={{ background: "none", border: "none", fontSize: 20, cursor: "pointer", color: "var(--text-secondary)" }}
              >
                ×
              </button>
            </div>
            <div style={{ display: "flex", gap: 8, marginBottom: 20, borderBottom: "1px solid var(--border-subtle)", paddingBottom: 8 }}>
              <button
                type="button"
                onClick={() => { setAuthMode("login"); setAuthError(null); }}
                style={{
                  background: "none",
                  border: "none",
                  padding: "6px 14px",
                  fontSize: 13,
                  fontWeight: authMode === "login" ? 700 : 500,
                  color: authMode === "login" ? "var(--text-primary)" : "var(--text-secondary)",
                  borderBottom: authMode === "login" ? "2px solid var(--brand-accent)" : "2px solid transparent",
                  cursor: "pointer"
                }}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => { setAuthMode("register"); setAuthError(null); }}
                style={{
                  background: "none",
                  border: "none",
                  padding: "6px 14px",
                  fontSize: 13,
                  fontWeight: authMode === "register" ? 700 : 500,
                  color: authMode === "register" ? "var(--text-primary)" : "var(--text-secondary)",
                  borderBottom: authMode === "register" ? "2px solid var(--brand-accent)" : "2px solid transparent",
                  cursor: "pointer"
                }}
              >
                Register New Account
              </button>
            </div>

            <h3 style={{ fontSize: 18, marginBottom: 6 }}>
              {authMode === "login" ? "Analyst Sign In" : "Register Forensic Examiner"}
            </h3>
            <p style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 18 }}>
              {authMode === "login" 
                ? "Authenticate against the secure PostgreSQL database to access forensic weights and logs." 
                : "Create a persistent analyst profile in the PostgreSQL database."}
            </p>

            {authError && (
              <div
                style={{
                  padding: 10,
                  backgroundColor: "var(--status-anomaly-bg)",
                  color: "var(--status-anomaly-text)",
                  borderRadius: 8,
                  fontSize: 12,
                  marginBottom: 16,
                }}
              >
                {authError}
              </div>
            )}

            {authMode === "login" ? (
              <form onSubmit={handleLoginSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                    Username or Email
                  </label>
                  <input
                    type="text"
                    value={authEmail}
                    onChange={(e) => setAuthEmail(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "10px 12px",
                      borderRadius: 8,
                      border: "1px solid var(--border-subtle)",
                      backgroundColor: "var(--bg-surface-secondary)",
                      color: "var(--text-primary)",
                      fontSize: 14,
                    }}
                    required
                  />
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                    Password
                  </label>
                  <input
                    type="password"
                    value={authPassword}
                    onChange={(e) => setAuthPassword(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "10px 12px",
                      borderRadius: 8,
                      border: "1px solid var(--border-subtle)",
                      backgroundColor: "var(--bg-surface-secondary)",
                      color: "var(--text-primary)",
                      fontSize: 14,
                    }}
                    required
                  />
                </div>

                <button
                  type="submit"
                  disabled={authLoading}
                  className="btn-primary"
                  style={{ marginTop: 8, padding: 12 }}
                >
                  {authLoading ? "Authenticating..." : "Sign In to Station"}
                </button>
              </form>
            ) : (
              <form onSubmit={handleRegisterSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                    Analyst Username
                  </label>
                  <input
                    type="text"
                    value={regUsername}
                    onChange={(e) => setRegUsername(e.target.value)}
                    placeholder="e.g. examiner_rajesh"
                    style={{
                      width: "100%",
                      padding: "10px 12px",
                      borderRadius: 8,
                      border: "1px solid var(--border-subtle)",
                      backgroundColor: "var(--bg-surface-secondary)",
                      color: "var(--text-primary)",
                      fontSize: 14,
                    }}
                    required
                  />
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                    Official Email
                  </label>
                  <input
                    type="email"
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    placeholder="e.g. rajesh@delhi.gov.in"
                    style={{
                      width: "100%",
                      padding: "10px 12px",
                      borderRadius: 8,
                      border: "1px solid var(--border-subtle)",
                      backgroundColor: "var(--bg-surface-secondary)",
                      color: "var(--text-primary)",
                      fontSize: 14,
                    }}
                    required
                  />
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                    Password (Min 8 characters)
                  </label>
                  <input
                    type="password"
                    value={regPassword}
                    onChange={(e) => setRegPassword(e.target.value)}
                    placeholder="********"
                    style={{
                      width: "100%",
                      padding: "10px 12px",
                      borderRadius: 8,
                      border: "1px solid var(--border-subtle)",
                      backgroundColor: "var(--bg-surface-secondary)",
                      color: "var(--text-primary)",
                      fontSize: 14,
                    }}
                    required
                  />
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                    Role / Division
                  </label>
                  <select
                    value={regRole}
                    onChange={(e) => setRegRole(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "10px 12px",
                      borderRadius: 8,
                      border: "1px solid var(--border-subtle)",
                      backgroundColor: "var(--bg-surface-secondary)",
                      color: "var(--text-primary)",
                      fontSize: 14,
                    }}
                  >
                    <option value="Forensic Analyst">Forensic Analyst</option>
                    <option value="Lead Forensic Examiner">Lead Forensic Examiner</option>
                    <option value="Security / Cyber Inspector">Security / Cyber Inspector</option>
                  </select>
                </div>

                <button
                  type="submit"
                  disabled={authLoading}
                  className="btn-primary"
                  style={{ marginTop: 8, padding: 12 }}
                >
                  {authLoading ? "Creating Account..." : "Create Account in Database"}
                </button>
              </form>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* EDITORIAL FOOTER                                                          */}
      {/* ========================================================================= */}
      <footer
        style={{
          borderTop: "1px solid var(--border-subtle)",
          backgroundColor: "var(--bg-surface)",
          padding: "36px 28px",
          marginTop: "auto",
        }}
      >
        <div
          style={{
            maxWidth: 1360,
            margin: "0 auto",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 16,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontFamily: "var(--font-serif)", fontSize: 16, fontWeight: 700 }}>Secura AI</span>
            <span style={{ color: "var(--text-secondary)", fontSize: 12 }}>· Digital Forensics &amp; Provenance Architecture</span>
          </div>

          <div style={{ fontSize: 12, color: "var(--text-secondary)", display: "flex", gap: 16 }}>
            <span>Zero-Hallucination Framework</span>
            <span>C2PA / JUMBF Verified</span>
            <span>CLIP ViT-L/14 &amp; Swin Models</span>
          </div>
        </div>
      </footer>

      {/* Mission 24: Live Photo Camera Capture Modal */}
      {/* Mission 24: Live Photo Camera Capture Modal */}
      {isPhotoCameraOpen && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.75)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            padding: 20,
          }}
        >
          <div
            className="card card-elevated"
            style={{
              maxWidth: 640,
              width: "100%",
              backgroundColor: "var(--bg-surface)",
              borderRadius: 20,
              padding: 24,
              boxShadow: "0 20px 40px rgba(0,0,0,0.4)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span className="badge badge-terracotta">WEBCAM CAPTURE</span>
                <h3 style={{ margin: 0, fontSize: 18 }}>Take Photo for AI Analysis</h3>
              </div>
              <button onClick={closePhotoCamera} className="btn-secondary" style={{ padding: "4px 10px", fontSize: 12 }}>
                ✕ Close
              </button>
            </div>

            <div style={{ position: "relative", backgroundColor: "#000", borderRadius: 12, overflow: "hidden", minHeight: 340 }}>
              {!capturedPhotoBlob ? (
                <video
                  ref={webcamVideoRef}
                  autoPlay
                  playsInline
                  muted
                  style={{ width: "100%", height: 340, objectFit: "cover" }}
                />
              ) : (
                <img
                  src={capturedPhotoPreviewUrl || ""}
                  alt="Captured camera still"
                  style={{ width: "100%", height: 340, objectFit: "contain", backgroundColor: "#111" }}
                />
              )}
            </div>

            {!capturedPhotoBlob ? (
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 18 }}>
                <button
                  onClick={() => openPhotoCamera(cameraFacingMode === "user" ? "environment" : "user")}
                  className="btn-secondary"
                  style={{ fontSize: 13, padding: "8px 14px" }}
                >
                  🔄 Switch Camera
                </button>
                <div style={{ display: "flex", gap: 10 }}>
                  <button onClick={closePhotoCamera} className="btn-secondary" style={{ fontSize: 13, padding: "8px 16px" }}>
                    Cancel
                  </button>
                  <button onClick={capturePhoto} className="btn-primary" style={{ fontSize: 14, padding: "8px 22px", fontWeight: 700 }}>
                    📸 Capture Photo
                  </button>
                </div>
              </div>
            ) : (
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 18 }}>
                <button
                  onClick={retakePhoto}
                  className="btn-secondary"
                  style={{ fontSize: 13, padding: "8px 14px" }}
                >
                  🔄 Retake Photo
                </button>
                <div style={{ display: "flex", gap: 10 }}>
                  <button onClick={closePhotoCamera} className="btn-secondary" style={{ fontSize: 13, padding: "8px 16px" }}>
                    Cancel
                  </button>
                  <button onClick={useCapturedPhoto} className="btn-primary" style={{ fontSize: 14, padding: "8px 22px", fontWeight: 700 }}>
                    ⚡ Use Photo &amp; Analyze
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      </div>
    </div>
  );
}

export default App;
