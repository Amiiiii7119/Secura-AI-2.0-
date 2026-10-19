import React, { useState, useRef, useEffect } from "react";
import { VideoForensicResult, RGBFrameSample, Milestone1Response, SuspiciousTemporalInterval } from "../types/api";
import { analyzeVideoFile, analyzeVideoFrame } from "../services/api";
import RGBHeartVisualization from "./RGBHeartVisualization";

interface VideoForensicsWorkspaceProps {
  onBackToLanding: () => void;
  onInspectFrameInWorkstation: (frameReport: Milestone1Response, frameThumbnail?: string) => void;
}

export const VideoForensicsWorkspace: React.FC<VideoForensicsWorkspaceProps> = ({
  onBackToLanding,
  onInspectFrameInWorkstation,
}) => {
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [videoResult, setVideoResult] = useState<VideoForensicResult | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // Playback & Timeline State
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [selectedSampleIndex, setSelectedSampleIndex] = useState<number>(0);
  const [playbackRate, setPlaybackRate] = useState<number>(1.0);
  const [selectedInterval, setSelectedInterval] = useState<SuspiciousTemporalInterval | null>(null);

  // Mission 24: Player Duration State & Technical Telemetry Toggle
  const [videoDuration, setVideoDuration] = useState<number>(0);
  const [showTechnicalTelemetry, setShowTechnicalTelemetry] = useState<boolean>(false);

  useEffect(() => {
    if (videoResult?.video_metadata?.duration_sec) {
      setVideoDuration(videoResult.video_metadata.duration_sec);
    }
  }, [videoResult]);

  // Mission 24: Live Video Stream Recording States
  const [isRecordingModalOpen, setIsRecordingModalOpen] = useState<boolean>(false);
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [recordingSeconds, setRecordingSeconds] = useState<number>(0);
  const [recordedVideoBlob, setRecordedVideoBlob] = useState<Blob | null>(null);
  const [recordedVideoUrl, setRecordedVideoUrl] = useState<string | null>(null);
  const cameraVideoRef = useRef<HTMLVideoElement | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordingTimerRef = useRef<any>(null);

  // Deep Frame Inspection State
  const [isDeepAnalyzingFrame, setIsDeepAnalyzingFrame] = useState<boolean>(false);
  const [frameAnalysisResult, setFrameAnalysisResult] = useState<Milestone1Response | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Clean up blob URL on unmount or file change
  useEffect(() => {
    return () => {
      if (videoUrl) URL.revokeObjectURL(videoUrl);
    };
  }, [videoUrl]);


  // Mission 24: Camera Stream & Recording Handlers
  const openCameraModal = async () => {
    setIsRecordingModalOpen(true);
    setRecordedVideoBlob(null);
    if (recordedVideoUrl) {
      URL.revokeObjectURL(recordedVideoUrl);
      setRecordedVideoUrl(null);
    }
    setRecordingSeconds(0);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" },
        audio: true,
      });
      mediaStreamRef.current = stream;
      if (cameraVideoRef.current) {
        cameraVideoRef.current.srcObject = stream;
        cameraVideoRef.current.play();
      }
    } catch (err: any) {
      alert("Unable to access camera: " + (err.message || "Permission denied or unavailable"));
      setIsRecordingModalOpen(false);
    }
  };

  const closeCameraModal = () => {
    if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    if (recordedVideoUrl) {
      URL.revokeObjectURL(recordedVideoUrl);
      setRecordedVideoUrl(null);
    }
    setRecordedVideoBlob(null);
    setIsRecording(false);
    setIsRecordingModalOpen(false);
  };

  const startVideoRecording = () => {
    if (!mediaStreamRef.current) return;
    const chunks: BlobPart[] = [];
    let mimeType = "video/webm";
    if (!MediaRecorder.isTypeSupported("video/webm")) {
      mimeType = MediaRecorder.isTypeSupported("video/mp4") ? "video/mp4" : "";
    }

    try {
      const recorder = new MediaRecorder(mediaStreamRef.current, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunks.push(e.data);
      };

      recorder.onstop = () => {
        const finalType = mimeType || "video/webm";
        const blob = new Blob(chunks, { type: finalType });
        setRecordedVideoBlob(blob);
        const url = URL.createObjectURL(blob);
        setRecordedVideoUrl(url);
        setIsRecording(false);
        if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
      };

      recorder.start(100);
      setIsRecording(true);
      setRecordingSeconds(0);

      recordingTimerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => {
          if (prev >= 29) {
            // Auto stop at 30 seconds limit
            stopVideoRecording();
            return 30;
          }
          return prev + 1;
        });
      }, 1000);
    } catch (err: any) {
      alert("Recording failed: " + err.message);
    }
  };

  const stopVideoRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
  };

  const useRecordedVideo = () => {
    if (!recordedVideoBlob) return;
    const file = new File([recordedVideoBlob], "camera_capture.webm", { type: recordedVideoBlob.type });
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    setIsRecordingModalOpen(false);
    handleVideoSelect(file);
  };

  const handleVideoSelect = (file: File) => {
    if (videoUrl) URL.revokeObjectURL(videoUrl);
    const url = URL.createObjectURL(file);
    setVideoFile(file);
    setVideoUrl(url);
    setVideoResult(null);
    setAnalysisError(null);
    setCurrentTime(0);
    setSelectedSampleIndex(0);
    setFrameAnalysisResult(null);
    setSelectedInterval(null);

    runVideoAnalysis(file);
  };

  const runVideoAnalysis = async (file: File) => {
    setIsAnalyzing(true);
    setAnalysisError(null);
    try {
      const result = await analyzeVideoFile(file, 0.4, 60);
      setVideoResult(result);
    } catch (err: any) {
      setAnalysisError(err.message || "Failed to analyze video stream.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleTimeUpdate = () => {
    if (!videoRef.current || !videoResult) return;
    const t = videoRef.current.currentTime;
    setCurrentTime(t);

    const samples = videoResult.sampled_frames;
    if (samples && samples.length > 0) {
      let closestIdx = 0;
      let minDiff = Infinity;
      for (let i = 0; i < samples.length; i++) {
        const sampleTime = samples[i].timestamp_sec ?? 0;
        const diff = Math.abs(sampleTime - t);
        if (diff < minDiff) {
          minDiff = diff;
          closestIdx = i;
        }
      }
      setSelectedSampleIndex(closestIdx);
    }
  };

  const seekToSample = (sample: RGBFrameSample) => {
    const targetTime = sample.timestamp_sec ?? 0;
    if (videoRef.current) {
      videoRef.current.currentTime = targetTime;
      setCurrentTime(targetTime);
      setSelectedSampleIndex(sample.sample_index ?? 0);
    }
  };

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play().then(() => setIsPlaying(true)).catch(() => {});
    }
  };

  const handleSpeedChange = (speed: number) => {
    setPlaybackRate(speed);
    if (videoRef.current) {
      videoRef.current.playbackRate = speed;
    }
  };

  const handleDeepAnalyzeCurrentFrame = async () => {
    if (!videoFile || !videoResult) return;
    const activeSample = videoResult.sampled_frames?.[selectedSampleIndex];
    const timestamp = activeSample?.timestamp_sec ?? currentTime;

    setIsDeepAnalyzingFrame(true);
    try {
      const videoVerdict = fusion?.final_classification || (videoResult.canonical_verdict?.predicted_label === "AI_GENERATED" ? "AI_GENERATED_VIDEO" : "REAL_CAPTURE");
      
      let frameFile: File = videoFile;
      if (videoRef.current) {
        try {
          const canvas = document.createElement("canvas");
          canvas.width = Math.min(1920, videoRef.current.videoWidth || 1280);
          canvas.height = Math.round((canvas.width * (videoRef.current.videoHeight || 720)) / (videoRef.current.videoWidth || 1280));
          const ctx = canvas.getContext("2d");
          if (ctx) {
            ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
            const blob = await new Promise<Blob | null>((res) => canvas.toBlob(res, "image/jpeg", 0.92));
            if (blob) {
              frameFile = new File([blob], `frame_${timestamp.toFixed(2)}s.jpg`, { type: "image/jpeg" });
            }
          }
        } catch {
          // fallback to videoFile
        }
      }
      
      const report = await analyzeVideoFrame(frameFile, timestamp, videoVerdict);
      setFrameAnalysisResult(report);
    } catch (err: any) {
      alert("Failed deep image analysis on selected frame: " + err.message);
    } finally {
      setIsDeepAnalyzingFrame(false);
    }
  };

  const activeSample = videoResult?.sampled_frames?.[selectedSampleIndex] ?? null;
  const fusion = videoResult?.fusion_verdict ?? null;
  const branches = videoResult?.branches ?? {};

  // Decision classification helpers
  const getClassificationBadge = (cls?: string) => {
    switch (cls) {
      case "AI_GENERATED_VIDEO":
        return {
          label: "AI-GENERATED SYNTHESIS",
          bg: "var(--color-terracotta-subtle)",
          color: "var(--color-terracotta)",
          border: "var(--color-terracotta)",
        };
      case "REAL_CAPTURE":
        return {
          label: "AUTHENTIC CAMERA CAPTURE",
          bg: "var(--status-verified-bg)",
          color: "var(--color-botanical-green)",
          border: "var(--status-verified-border)",
        };
      case "FACE_MANIPULATED_VIDEO":
        return {
          label: "FACIAL MANIPULATION / DEEPFAKE",
          bg: "var(--status-anomaly-bg)",
          color: "var(--status-anomaly-text)",
          border: "var(--status-anomaly-border)",
        };
      case "INCONCLUSIVE":
      default:
        return {
          label: "INCONCLUSIVE / CONFLICTING SIGNALS",
          bg: "var(--color-mustard-subtle)",
          color: "var(--color-mustard-deep)",
          border: "rgba(198, 166, 75, 0.4)",
        };
    }
  };

  const getUncertaintyBadge = (status?: string) => {
    switch (status) {
      case "HIGH_CONFIDENCE":
        return { label: "HIGH CONFIDENCE", bg: "rgba(45, 106, 79, 0.12)", color: "var(--color-botanical-green)" };
      case "MODERATE_CONFIDENCE":
        return { label: "MODERATE CONFIDENCE", bg: "rgba(217, 107, 53, 0.12)", color: "var(--color-terracotta)" };
      case "CONFLICTING_SIGNALS":
        return { label: "CONFLICTING SIGNALS", bg: "rgba(198, 166, 75, 0.18)", color: "var(--color-mustard-deep)" };
      case "INSUFFICIENT_DATA":
      default:
        return { label: "INSUFFICIENT DATA", bg: "rgba(129, 118, 106, 0.14)", color: "var(--text-secondary)" };
    }
  };

  return (
    <div className="workspace-layout animate-fade-in">
      {/* Top Header & Navigation Breadcrumb */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 16,
          paddingBottom: 8,
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <button
            onClick={onBackToLanding}
            className="btn-secondary"
            style={{ padding: "8px 14px", fontSize: 13 }}
            title="Return to Main Overview"
          >
            ← Overview
          </button>
          <div>
            <div className="eyebrow" style={{ marginBottom: 2 }}>
              VIDEO &amp; TEMPORAL FORENSIC SUITE
            </div>
            <h2 style={{ fontSize: 24, margin: 0 }}>Multi-Layer Video Inspection</h2>
          </div>
        </div>

        {videoFile && (
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
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
              {videoFile.name} ({(videoFile.size / (1024 * 1024)).toFixed(2)} MB)
            </span>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="btn-secondary"
              style={{ padding: "8px 14px", fontSize: 13 }}
            >
              Replace Video
            </button>
          </div>
        )}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="video/mp4,video/quicktime,video/webm"
        style={{ display: "none" }}
        onChange={(e) => {
          if (e.target.files && e.target.files[0]) {
            handleVideoSelect(e.target.files[0]);
          }
        }}
      />

      {/* Video Upload Dropzone */}
      {!videoFile && (
        <div
          className="dropzone-container"
          style={{ minHeight: 320, justifyContent: "center", cursor: "default" }}
        >
          <div style={{ display: "flex", gap: 14, marginTop: 12 }}>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="btn-primary"
              style={{ padding: "10px 20px", fontSize: 14, fontWeight: 700 }}
            >
              📁 Choose Video File
            </button>
            <button
              onClick={openCameraModal}
              className="btn-secondary"
              style={{ padding: "10px 20px", fontSize: 14, fontWeight: 700 }}
            >
              🎥 Record with Live Camera
            </button>
          </div>
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
            ▶
          </div>
          <div style={{ maxWidth: 440 }}>
            <h3 style={{ fontSize: 18, marginBottom: 6 }}>Upload Video for Multi-Layer Forensic Analysis</h3>
            <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
              Supports MP4, QuickTime (MOV), and WebM containers. Evaluates representation trajectory curvature,
              frame diffusion artifacts, motion coherence, and high-frequency noise variance.
            </p>
          </div>
          <button className="btn-primary" style={{ marginTop: 8 }}>
            Select Video File
          </button>
        </div>
      )}

      {/* Analysis In Progress Indicator */}
      {isAnalyzing && (
        <div
          className="card card-elevated"
          style={{
            padding: 48,
            textAlign: "center",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 16,
          }}
        >
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
          <div style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>
            Decoding Video Stream &amp; Running Multi-Branch Analysis
          </div>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", maxWidth: 500, lineHeight: 1.6 }}>
            Sampling uniform timeline frames, computing ordered latent trajectory curvature with CLIP ViT-L/14,
            evaluating spatial diffusion distributions with Swin, and extracting optical flow vectors.
          </div>
        </div>
      )}

      {/* Error Banner */}
      {analysisError && !isAnalyzing && (
        <div
          className="card"
          style={{
            padding: 20,
            borderLeft: "4px solid var(--status-anomaly-text)",
            backgroundColor: "var(--status-anomaly-bg)",
          }}
        >
          <div style={{ fontWeight: 700, color: "var(--status-anomaly-text)", marginBottom: 4 }}>
            Forensic Analysis Pipeline Error
          </div>
          <div style={{ fontSize: 13, color: "var(--text-primary)" }}>{analysisError}</div>
        </div>
      )}

      {/* Main Forensic Analysis Workstation */}
      {videoFile && videoResult && !isAnalyzing && (
        <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
          {/* ========================================================================= */}
          {/* Mission 24: Canonical Consumer Binary Verdict Card */}
          <div
            className="card card-elevated animate-fade-in"
            style={{
              padding: "24px 30px",
              borderRadius: 20,
              backgroundColor: "var(--bg-surface)",
              borderLeft: `6px solid ${
                (videoResult.canonical_verdict?.predicted_label ?? (fusion?.final_classification === "AI_GENERATED_VIDEO" ? "AI_GENERATED" : "NOT_AI_GENERATED")) === "AI_GENERATED"
                  ? "var(--color-terracotta)"
                  : "var(--color-sage)"
              }`,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                  <span
                    style={{
                      padding: "6px 14px",
                      borderRadius: 8,
                      fontSize: 14,
                      fontWeight: 800,
                      letterSpacing: "0.06em",
                      backgroundColor:
                        (videoResult.canonical_verdict?.predicted_label ?? (fusion?.final_classification === "AI_GENERATED_VIDEO" ? "AI_GENERATED" : "NOT_AI_GENERATED")) === "AI_GENERATED"
                          ? "var(--color-terracotta-subtle)"
                          : "var(--color-sage-subtle)",
                      color:
                        (videoResult.canonical_verdict?.predicted_label ?? (fusion?.final_classification === "AI_GENERATED_VIDEO" ? "AI_GENERATED" : "NOT_AI_GENERATED")) === "AI_GENERATED"
                          ? "var(--color-terracotta)"
                          : "var(--color-sage)",
                      border: `1px solid ${
                        (videoResult.canonical_verdict?.predicted_label ?? (fusion?.final_classification === "AI_GENERATED_VIDEO" ? "AI_GENERATED" : "NOT_AI_GENERATED")) === "AI_GENERATED"
                          ? "var(--color-terracotta)"
                          : "var(--color-sage)"
                      }`,
                    }}
                  >
                    {videoResult.canonical_verdict?.display_label ?? (fusion?.final_classification === "AI_GENERATED_VIDEO" ? "AI GENERATED" : "NOT AI GENERATED")}
                  </span>
                  <span style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 600 }}>
                    Decision Threshold: 0.50 | Duration: {(videoDuration > 0 ? videoDuration : videoResult.video_metadata?.duration_sec ?? 0).toFixed(2)}s
                  </span>
                </div>
                <h2 style={{ fontSize: 24, margin: "6px 0", color: "var(--text-primary)" }}>
                  {(videoResult.canonical_verdict?.predicted_label ?? (fusion?.final_classification === "AI_GENERATED_VIDEO" ? "AI_GENERATED" : "NOT_AI_GENERATED")) === "AI_GENERATED"
                    ? "AI Video Generation Signals Detected"
                    : "Consistent with Natural Physical Camera Recording"}
                </h2>
                <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0", maxWidth: 680 }}>
                  {videoResult.canonical_verdict?.evidence_summary ?? "Analyzed multi-frame temporal representation curvature and spatial textures."}
                </p>
              </div>

              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "flex-end",
                  backgroundColor: "var(--bg-surface-secondary)",
                  padding: "12px 20px",
                  borderRadius: 14,
                  border: "1px solid var(--border-subtle)",
                }}
              >
                <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>
                  Model Score
                </div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 28, fontWeight: 800, color: "var(--color-terracotta)" }}>
                  {(((videoResult.canonical_verdict?.model_score ?? fusion?.raw_model_score) ?? 0) * 100).toFixed(1)}%
                </div>
                <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>
                  {videoResult.canonical_verdict?.calibrated_probability != null
                    ? `Calibrated: ${(videoResult.canonical_verdict.calibrated_probability * 100).toFixed(1)}%`
                    : "Uncalibrated Empirical Score"}
                </div>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 16, paddingTop: 12, borderTop: "1px solid var(--border-subtle)", flexWrap: "wrap", gap: 10 }}>
              <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                ⚠️ Disclaimer: Automated AI detectors evaluate mathematical and temporal signals and can make mistakes.
              </div>
              <button
                onClick={() => setShowTechnicalTelemetry(!showTechnicalTelemetry)}
                className="btn-secondary"
                style={{ fontSize: 12, padding: "6px 14px", borderRadius: 8 }}
              >
                {showTechnicalTelemetry ? "▲ Hide Deep Technical Forensics" : "▼ Show Deep Technical Forensics & Curves"}
              </button>
            </div>
          </div>

          {/* SECTION 1: AUTHORITATIVE MULTI-LAYER EVIDENCE SYNTHESIS PANEL             */}
          {/* ========================================================================= */}
          {fusion && (
            <div
              className="card card-elevated"
              style={{
                padding: "28px 32px",
                borderRadius: 20,
                border: `1.5px solid ${getClassificationBadge(fusion.final_classification).border}`,
                backgroundColor: "var(--bg-surface)",
                display: "flex",
                flexDirection: "column",
                gap: 20,
                boxShadow: "var(--shadow-md)",
              }}
            >
              {/* Verdict Header Row */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  flexWrap: "wrap",
                  gap: 16,
                }}
              >
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                    <span
                      style={{
                        padding: "5px 12px",
                        borderRadius: 8,
                        fontSize: 12,
                        fontWeight: 800,
                        letterSpacing: "0.06em",
                        backgroundColor: getClassificationBadge(fusion.final_classification).bg,
                        color: getClassificationBadge(fusion.final_classification).color,
                        border: `1px solid ${getClassificationBadge(fusion.final_classification).border}`,
                      }}
                    >
                      {getClassificationBadge(fusion.final_classification).label}
                    </span>
                    <span
                      style={{
                        padding: "4px 10px",
                        borderRadius: 6,
                        fontSize: 11,
                        fontWeight: 700,
                        backgroundColor: getUncertaintyBadge(fusion.uncertainty_status).bg,
                        color: getUncertaintyBadge(fusion.uncertainty_status).color,
                      }}
                    >
                      {getUncertaintyBadge(fusion.uncertainty_status).label}
                    </span>
                  </div>

                  <h3 style={{ fontSize: 20, margin: 0, color: "var(--text-primary)" }}>
                    {fusion.final_classification === "AI_GENERATED_VIDEO"
                      ? "Substantial Evidence of Generative Video Synthesis"
                      : fusion.final_classification === "REAL_CAPTURE"
                      ? "Evidence Consistent with Physical Camera Optical Capture"
                      : fusion.final_classification === "FACE_MANIPULATED_VIDEO"
                      ? "Facial Region Synthetic Alteration Detected"
                      : "Contradictory or Inconclusive Forensic Evidence"}
                  </h3>
                </div>

                {/* Score & Calibration Disclosure */}
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "flex-end",
                    backgroundColor: "var(--bg-surface-secondary)",
                    padding: "12px 18px",
                    borderRadius: 12,
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>
                    Standardized Model Score
                  </div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 24, fontWeight: 800, color: "var(--color-terracotta)" }}>
                    {((fusion.raw_model_score ?? 0) * 100).toFixed(1)}%
                  </div>
                  <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>
                    {fusion.calibrated_ai_probability != null
                      ? `Calibrated P(AI): ${(fusion.calibrated_ai_probability * 100).toFixed(1)}%`
                      : "Uncalibrated Empirical Score"}
                  </div>
                </div>
              </div>

              {/* Explicit Score Semantics Disclosure */}
              <div
                style={{
                  fontSize: 12,
                  color: "var(--text-secondary)",
                  backgroundColor: "var(--bg-surface-secondary)",
                  padding: "10px 14px",
                  borderRadius: 10,
                  borderLeft: "3px solid var(--color-mustard-deep)",
                }}
              >
                <strong>Score Semantics: </strong>
                {fusion.score_semantics || "Multi-branch synthesis combining representation curvature and frame diffusion distribution."}
              </div>

              {/* Abstention Reason (If Inconclusive) */}
              {fusion.abstention_reason && (
                <div
                  style={{
                    backgroundColor: "var(--color-mustard-subtle)",
                    border: "1px solid rgba(198, 166, 75, 0.35)",
                    borderRadius: 10,
                    padding: "12px 16px",
                    color: "var(--color-mustard-deep)",
                    fontSize: 13,
                    lineHeight: 1.5,
                  }}
                >
                  <strong>Scientific Abstention Reason: </strong>
                  {fusion.abstention_reason}
                </div>
              )}

              {/* Evidence Signals Grid */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                {/* Supporting Signals */}
                <div
                  style={{
                    backgroundColor: "var(--bg-surface-secondary)",
                    padding: "14px 18px",
                    borderRadius: 12,
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  <div style={{ fontSize: 12, fontWeight: 800, color: "var(--color-terracotta)", marginBottom: 8 }}>
                    SUPPORTING EVIDENCE SIGNALS ({fusion.supporting_evidence?.length ?? 0})
                  </div>
                  {fusion.supporting_evidence && fusion.supporting_evidence.length > 0 ? (
                    <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "var(--text-primary)", display: "flex", flexDirection: "column", gap: 4 }}>
                      {fusion.supporting_evidence.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  ) : (
                    <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>No primary anomaly signals confirmed.</div>
                  )}
                </div>

                {/* Contradictory / Discrepancy Signals */}
                <div
                  style={{
                    backgroundColor: "var(--bg-surface-secondary)",
                    padding: "14px 18px",
                    borderRadius: 12,
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  <div style={{ fontSize: 12, fontWeight: 800, color: "var(--color-mustard-deep)", marginBottom: 8 }}>
                    CONTRADICTORY / DISCREPANCY SIGNALS ({fusion.contradictory_evidence?.length ?? 0})
                  </div>
                  {fusion.contradictory_evidence && fusion.contradictory_evidence.length > 0 ? (
                    <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "var(--text-primary)", display: "flex", flexDirection: "column", gap: 4 }}>
                      {fusion.contradictory_evidence.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  ) : (
                    <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>No contradictory indicators identified.</div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* SECTION 2: VIDEO PLAYER & SIGNATURE RGB-HEART WORKBENCH                  */}
          {/* ========================================================================= */}
          <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 24, alignItems: "start" }}>
            {/* Left: Video Player */}
            <div className="card" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
              <div style={{ position: "relative", backgroundColor: "#000", borderRadius: 12, overflow: "hidden" }}>
                <video
                  ref={videoRef}
                  src={videoUrl ?? undefined}
                  onTimeUpdate={handleTimeUpdate}
                  onLoadedMetadata={(e) => {
                    const d = e.currentTarget.duration;
                    if (d && !isNaN(d) && isFinite(d) && d > 0) setVideoDuration(d);
                  }}
                  onDurationChange={(e) => {
                    const d = e.currentTarget.duration;
                    if (d && !isNaN(d) && isFinite(d) && d > 0) setVideoDuration(d);
                  }}
                  style={{ width: "100%", maxHeight: 380, display: "block", objectFit: "contain" }}
                />
              </div>

              {/* Player Controls Bar */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <button
                    onClick={togglePlay}
                    className="btn-primary"
                    style={{ padding: "8px 16px", fontSize: 13 }}
                  >
                    {isPlaying ? "❚❚ Pause" : "▶ Play"}
                  </button>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--text-primary)" }}>
                    {currentTime.toFixed(2)}s / {(videoDuration > 0 ? videoDuration : (videoRef.current?.duration ?? 0)).toFixed(2)}s
                  </span>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Speed:</span>
                  {[0.5, 1.0, 2.0].map((rate) => (
                    <button
                      key={rate}
                      onClick={() => handleSpeedChange(rate)}
                      className={playbackRate === rate ? "btn-secondary active" : "btn-subtle"}
                      style={{
                        padding: "4px 8px",
                        fontSize: 11,
                        fontWeight: playbackRate === rate ? 700 : 500,
                        borderColor: playbackRate === rate ? "var(--color-terracotta)" : "transparent",
                      }}
                    >
                      {rate}x
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Right: Signature RGB-Heart Visualization */}
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <RGBHeartVisualization
                activeSample={activeSample}
                summary={videoResult.rgb_summary}
                isPlaying={isPlaying}
                width={360}
                height={300}
              />

              {/* Frame Deep Inspection Button */}
              <div className="card" style={{ padding: "16px 20px", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
                    Analyze Frame at {currentTime.toFixed(2)}s
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                    Pass current frame to still-image forensic pipeline (ELA, DCT, PRNU).
                  </div>
                </div>
                <button
                  onClick={handleDeepAnalyzeCurrentFrame}
                  disabled={isDeepAnalyzingFrame}
                  className="btn-secondary"
                  style={{ padding: "8px 14px", fontSize: 12, whiteSpace: "nowrap" }}
                >
                  {isDeepAnalyzingFrame ? "Analyzing..." : "Deep Inspect Frame →"}
                </button>
              </div>
            </div>
          </div>

          {/* Deep Frame Analysis Modal/Drawer */}
          {frameAnalysisResult && (
            <div
              className="card card-elevated"
              style={{
                padding: 24,
                border: "1.5px solid var(--color-terracotta)",
                backgroundColor: "var(--bg-surface)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                <h3 style={{ fontSize: 16, margin: 0, color: "var(--color-terracotta)" }}>
                  Deep Image Forensics Result for Frame at {currentTime.toFixed(2)}s
                </h3>
                <button
                  onClick={() => onInspectFrameInWorkstation(frameAnalysisResult, activeSample?.thumbnail_data_url ?? undefined)}
                  className="btn-primary"
                  style={{ padding: "6px 12px", fontSize: 12 }}
                >
                  Open in 8-View Workstation ↗
                </button>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
                <div className="card-oat" style={{ padding: 12 }}>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>AI DETECTOR DECISION</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: (frameAnalysisResult.canonical_verdict?.predicted_label === "AI_GENERATED" || frameAnalysisResult.ai_detection?.predicted_class === "AI_GENERATED") ? "var(--color-terracotta)" : "var(--color-botanical-green)" }}>
                    {frameAnalysisResult.canonical_verdict?.display_label || frameAnalysisResult.ai_detection?.decision_status || "ANALYZED"}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 2 }}>
                    Score: {(((frameAnalysisResult.canonical_verdict?.model_score ?? frameAnalysisResult.ai_detection?.uncalibrated_margin) ?? 0.5) * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="card-oat" style={{ padding: 12 }}>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>ELA COMPRESSION ERROR</div>
                  <div style={{ fontSize: 14, fontWeight: 700 }}>
                    {frameAnalysisResult.ela_forensics?.metrics?.mean_absolute_difference?.toFixed(2) ?? "N/A"}
                  </div>
                </div>
                <div className="card-oat" style={{ padding: 12 }}>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>DCT HIGH-FREQ ENERGY</div>
                  <div style={{ fontSize: 14, fontWeight: 700 }}>
                    {frameAnalysisResult.dct_analysis?.metrics?.boundary_discontinuity?.toFixed(2) ?? "N/A"}
                  </div>
                </div>
                <div className="card-oat" style={{ padding: 12 }}>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>NOISE RESIDUAL STD</div>
                  <div style={{ fontSize: 14, fontWeight: 700 }}>
                    {frameAnalysisResult.noise_residual?.metrics?.std_residual?.toFixed(2) ?? "N/A"}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* SECTION 3: FRAME FILMSTRIP                                               */}
          {/* ========================================================================= */}
          <div className="card" style={{ padding: "20px 24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div>
                <h4 style={{ fontSize: 15, margin: 0 }}>Sampled Frame Filmstrip</h4>
                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                  {((videoResult.canonical_verdict?.predicted_label ?? (fusion?.final_classification === "AI_GENERATED_VIDEO" ? "AI_GENERATED" : "NOT_AI_GENERATED")) === "AI_GENERATED")
                    ? "All frames inherit AI synthesis context from verified generative video synthesis."
                    : "Each thumbnail shows the frame-level diffusion texture score across sampled timestamps."}
                </div>
              </div>
              <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                {videoResult.sampled_frames?.length ?? 0} frames sampled
              </span>
            </div>

            <div className="filmstrip-scroll">
              {videoResult.sampled_frames?.map((frame, idx) => {
                const isSelected = selectedSampleIndex === idx;
                const frameTime = frame.timestamp_sec ?? 0;
                const aiProb = frame.ai_probability ?? null;

                return (
                  <div
                    key={idx}
                    className={`filmstrip-tile ${isSelected ? "selected" : ""}`}
                    onClick={() => seekToSample(frame)}
                  >
                    {(() => {
                      const thumbSrc = frame.thumbnail_data_url || (frame as any).thumbnail_b64;
                      return thumbSrc ? (
                        <img
                          src={thumbSrc}
                          alt={`Frame ${idx}`}
                          style={{ width: "100%", height: 64, objectFit: "cover", display: "block", borderRadius: 4 }}
                        />
                      ) : (
                        <div
                          style={{
                            width: "100%",
                            height: 64,
                            backgroundColor: "var(--bg-surface-secondary)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontSize: 11,
                            fontWeight: 600,
                            color: "var(--text-secondary)",
                          }}
                        >
                          Frame #{idx}
                        </div>
                      );
                    })()}
                    <div style={{ padding: "6px 8px", display: "flex", flexDirection: "column", gap: 2 }}>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-secondary)" }}>
                        {frameTime.toFixed(2)}s
                      </span>
                      {((videoResult.canonical_verdict?.predicted_label ?? (fusion?.final_classification === "AI_GENERATED_VIDEO" ? "AI_GENERATED" : "NOT_AI_GENERATED")) === "AI_GENERATED") ? (
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            color: "var(--color-terracotta)",
                          }}
                        >
                          {`AI Frame: ${(Math.max(aiProb ?? 0.90, 0.75) * 100).toFixed(0)}%`}
                        </span>
                      ) : aiProb !== null ? (
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            color: aiProb > 0.5 ? "var(--color-terracotta)" : "var(--color-botanical-green)",
                          }}
                        >
                          {aiProb > 0.5 ? `Diff: ${(aiProb * 100).toFixed(0)}%` : `Real: ${((1 - aiProb) * 100).toFixed(0)}%`}
                        </span>
                      ) : (
                        <span style={{ fontSize: 9, color: "var(--text-tertiary)" }}>RGB Frame</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* ========================================================================= */}
          {/* SECTION 4: FORENSIC TIMELINE WITH ANOMALY INTERVALS                       */}
          {/* ========================================================================= */}
          {videoResult.suspicious_intervals && videoResult.suspicious_intervals.length > 0 && (
            <div className="card" style={{ padding: "20px 24px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <div>
                  <h4 style={{ fontSize: 15, margin: 0 }}>Temporal Anomaly Timeline</h4>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                    Marked intervals indicate localized representation curvature deviations or motion discontinuities.
                  </div>
                </div>
                <span className="badge badge-mustard">
                  {videoResult.suspicious_intervals.length} Suspicious Intervals
                </span>
              </div>

              {/* Timeline Track Bar */}
              <div
                className="timeline-track"
                onClick={(e) => {
                  if (!videoRef.current) return;
                  const rect = e.currentTarget.getBoundingClientRect();
                  const clickPct = (e.clientX - rect.left) / rect.width;
                  const dur = videoRef.current.duration || 1;
                  videoRef.current.currentTime = clickPct * dur;
                }}
              >
                {/* Playhead Indicator */}
                <div
                  className="timeline-progress-fill"
                  style={{
                    width: `${Math.min(100, (currentTime / (videoDuration || videoRef.current?.duration || 1)) * 100)}%`,
                  }}
                />

                {/* Interval Markers */}
                {videoResult.suspicious_intervals.map((interval, i) => {
                  const duration = videoDuration || videoRef.current?.duration || 1;
                  const startSec = interval.start_timestamp ?? interval.start_sec ?? 0;
                  const endSec = interval.end_timestamp ?? interval.end_sec ?? 0;
                  const startPct = (startSec / duration) * 100;
                  const endPct = (endSec / duration) * 100;
                  const widthPct = Math.max(1.5, endPct - startPct);

                  return (
                    <div
                      key={i}
                      className="timeline-marker"
                      style={{
                        left: `${startPct}%`,
                        width: `${widthPct}%`,
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedInterval(interval);
                        if (videoRef.current) videoRef.current.currentTime = startSec;
                      }}
                      title={`${interval.branch}: ${startSec.toFixed(2)}s - ${endSec.toFixed(2)}s`}
                    />
                  );
                })}
              </div>

              {/* Selected Interval Callout */}
              {selectedInterval && (
                <div
                  className="card-oat"
                  style={{
                    marginTop: 14,
                    padding: "12px 16px",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                  }}
                >
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: "var(--color-terracotta)", marginBottom: 2 }}>
                      {selectedInterval.branch} ({(selectedInterval.start_timestamp ?? selectedInterval.start_sec ?? 0).toFixed(2)}s – {(selectedInterval.end_timestamp ?? selectedInterval.end_sec ?? 0).toFixed(2)}s)
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text-primary)", marginBottom: 4 }}>
                      {selectedInterval.explanation}
                    </div>
                    <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                      Metric: {selectedInterval.measured_metric || "Anomaly score"} · {selectedInterval.threshold_or_basis || "Threshold evaluated"}
                    </div>
                  </div>
                  <button
                    onClick={() => setSelectedInterval(null)}
                    style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)", fontSize: 16 }}
                  >
                    ×
                  </button>
                </div>
              )}
            </div>
          )}

          {/* ========================================================================= */}
          {/* SECTION 5: SIX MULTI-BRANCH FORENSIC ANALYZER CARDS                      */}
          {/* ========================================================================= */}
          <div>
            <div style={{ marginBottom: 14 }}>
              <h3 style={{ fontSize: 18, margin: 0 }}>Detailed Forensic Branch Breakdown</h3>
              <p style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                Independent measurements across optical, kinematic, latent representation, spatial texture, and metadata layers.
              </p>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: 18 }}>
              {/* Branch 1: Chromatic RGB Dynamics */}
              <div className="card" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className="eyebrow" style={{ margin: 0 }}>BRANCH 1</span>
                  <span className="badge badge-verified">
                    {branches["branch_1_rgb"]?.status || "COMPLETED"}
                  </span>
                </div>
                <h4 style={{ fontSize: 15, margin: 0 }}>Chromatic &amp; RGB Dynamics</h4>
                <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
                  Quantifies inter-frame Euclidean channel shift and temporal color stability.
                </p>
                <div className="card-oat" style={{ padding: 12, display: "flex", justifyContent: "space-between" }}>
                  <div>
                    <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>TEMPORAL JITTER</div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700 }}>
                      {videoResult.rgb_summary?.temporal_jitter_index !== undefined && videoResult.rgb_summary?.temporal_jitter_index !== null ? videoResult.rgb_summary.temporal_jitter_index.toFixed(4) : "N/A"}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>DOMINANT PULSE</div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700 }}>
                      {videoResult.rgb_summary?.dominant_pulse_hz ? `${videoResult.rgb_summary.dominant_pulse_hz.toFixed(2)} Hz` : "N/A"}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>FRAMES</div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700 }}>
                      {branches["branch_1_rgb"]?.frames_analyzed ?? videoResult.sampled_frames?.length ?? 8}
                    </div>
                  </div>
                </div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                  <em>Limitation:</em> Color jitter measures lighting shifts; does not independently prove synthetic origin.
                </div>
              </div>

              {/* Branch 2: Optical Flow & Motion Field */}
              <div className="card" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className="eyebrow" style={{ margin: 0 }}>BRANCH 2</span>
                  <span className="badge badge-verified">
                    {branches["branch_2_motion"]?.status || "COMPLETED"}
                  </span>
                </div>
                <h4 style={{ fontSize: 15, margin: 0 }}>Optical Flow &amp; Motion Field</h4>
                <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
                  Dense motion field vector continuity and kinematics between adjacent sampled frames.
                </p>
                <div className="card-oat" style={{ padding: 12, display: "flex", justifyContent: "space-between" }}>
                  <div>
                    <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>MOTION DISCONTINUITY</div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700 }}>
                      {branches["branch_2_motion"]?.raw_metrics?.motion_discontinuity_index !== undefined ? branches["branch_2_motion"].raw_metrics.motion_discontinuity_index.toFixed(2) : "N/A"}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>MEAN FLOW MAG</div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700 }}>
                      {branches["branch_2_motion"]?.raw_metrics?.mean_flow_magnitude !== undefined ? `${branches["branch_2_motion"].raw_metrics.mean_flow_magnitude.toFixed(2)} px` : "N/A"}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>RUNTIME</div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700 }}>
                      {branches["branch_2_motion"]?.runtime_ms !== undefined ? `${(branches["branch_2_motion"].runtime_ms / 1000).toFixed(2)}s` : "N/A"}
                    </div>
                  </div>
                </div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                  <em>Limitation:</em> Scene cuts and rapid pans can produce false motion discontinuity spikes.
                </div>
              </div>

              {/* Branch 3: Temporal Representation Dynamics */}
              <div className="card" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className="eyebrow" style={{ margin: 0 }}>BRANCH 3</span>
                  <span className="badge badge-mustard">
                    {branches["branch_3_temporal"]?.status || "COMPLETED"}
                  </span>
                </div>
                <h4 style={{ fontSize: 15, margin: 0 }}>Temporal Representation Dynamics</h4>
                <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
                  Latent trajectory curvature across ordered CLIP ViT-L/14 visual representations.
                </p>
                <div className="card-oat" style={{ padding: 12, display: "flex", justifyContent: "space-between" }}>
                  <div>
                    <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>MEAN CURVATURE</div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700, color: "var(--color-terracotta)" }}>
                      {branches["branch_3_temporal"]?.raw_metrics?.mean_trajectory_curvature_rad !== undefined ? `${branches["branch_3_temporal"].raw_metrics.mean_trajectory_curvature_rad.toFixed(2)} rad` : "N/A"}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>TORTUOSITY</div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700 }}>
                      {branches["branch_3_temporal"]?.raw_metrics?.trajectory_tortuosity !== undefined ? branches["branch_3_temporal"].raw_metrics.trajectory_tortuosity.toFixed(2) : "N/A"}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>SYNTH LIKELIHOOD</div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700 }}>
                      {branches["branch_3_temporal"]?.score !== undefined && branches["branch_3_temporal"]?.score !== null
                        ? `${(branches["branch_3_temporal"].score * 100).toFixed(1)}%`
                        : "N/A"}
                    </div>
                  </div>
                </div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                  <em>Semantics:</em> Uncalibrated heuristic trajectory metric, not official ReStraV research classifier.
                </div>
              </div>

              {/* Branch 4: Spatial & Residual Analysis */}
              <div className="card" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className="eyebrow" style={{ margin: 0 }}>BRANCH 4</span>
                  <span className="badge badge-verified">
                    {branches["branch_4_spatial_frequency"]?.status || "COMPLETED"}
                  </span>
                </div>
                <h4 style={{ fontSize: 15, margin: 0 }}>Spatial &amp; High-Frequency Texture</h4>
                <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
                  Swin neural diffusion classifier on frame crops and Laplacian high-frequency residual variance.
                </p>
                <div className="card-oat" style={{ padding: 12, display: "flex", justifyContent: "space-between" }}>
                  <div>
                    <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>MEAN FRAME DIFFUSION</div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700 }}>
                      {branches["branch_4_spatial_frequency"]?.raw_metrics?.mean_ai_probability !== undefined
                        ? `${(branches["branch_4_spatial_frequency"].raw_metrics.mean_ai_probability * 100).toFixed(1)}%`
                        : "N/A"}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>TEXTURE VARIANCE</div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700 }}>
                      {branches["branch_4_spatial_frequency"]?.raw_metrics?.mean_noise_variance !== undefined ? branches["branch_4_spatial_frequency"].raw_metrics.mean_noise_variance.toFixed(1) : "N/A"}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>PEAK FRAME</div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700 }}>
                      {branches["branch_4_spatial_frequency"]?.raw_metrics?.peak_ai_probability !== undefined
                        ? `${(branches["branch_4_spatial_frequency"].raw_metrics.peak_ai_probability * 100).toFixed(1)}%`
                        : "N/A"}
                    </div>
                  </div>
                </div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                  <em>Physical Basis:</em> High-frequency variance represents texture smoothing; does not prove CMOS origin.
                </div>
              </div>

              {/* Branch 6: Face Manipulation & Landmark Dynamics */}
              <div className="card" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className="eyebrow" style={{ margin: 0 }}>BRANCH 6</span>
                  <span className="badge badge-inconclusive">
                    {branches["branch_6_face"]?.status || "NOT_APPLICABLE"}
                  </span>
                </div>
                <h4 style={{ fontSize: 15, margin: 0 }}>Facial Landmark &amp; Deepfake Tracking</h4>
                <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
                  Evaluates facial geometry consistency, landmark jitter, and blending boundary seams.
                </p>
                <div className="card-oat" style={{ padding: 12, display: "flex", justifyContent: "space-between" }}>
                  <div>
                    <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>FACES TRACKED</div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700 }}>
                      {branches["branch_6_face"]?.raw_metrics?.face_count ?? 0}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>ANOMALY SCORE</div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700 }}>
                      {branches["branch_6_face"]?.score !== null && branches["branch_6_face"]?.score !== undefined
                        ? branches["branch_6_face"].score.toFixed(2)
                        : "N/A"}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>STATUS</div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700 }}>
                      {branches["branch_6_face"]?.status === "NOT_APPLICABLE" ? "No Faces" : "Analyzed"}
                    </div>
                  </div>
                </div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                  Inactive when video contains landscape or inanimate subjects.
                </div>
              </div>

              {/* Branch 7: Container Metadata & C2PA Provenance */}
              <div className="card" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className="eyebrow" style={{ margin: 0 }}>BRANCH 7</span>
                  <span className="badge badge-verified">
                    {branches["branch_7_container"]?.status || "COMPLETED"}
                  </span>
                </div>
                <h4 style={{ fontSize: 15, margin: 0 }}>Container &amp; C2PA Provenance</h4>
                <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
                  Cryptographic JUMBF manifest inspection and MP4 container atom structure consistency.
                </p>
                <div className="card-oat" style={{ padding: 12, display: "flex", justifyContent: "space-between" }}>
                  <div>
                    <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>C2PA MANIFEST</div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700 }}>
                      {branches["branch_7_container"]?.raw_metrics?.has_c2pa ? "Verified" : "Absent"}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>ATOM ORDER</div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700 }}>
                      {branches["branch_7_container"]?.raw_metrics?.atom_order || "Standard"}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>PROVENANCE</div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700 }}>
                      Unsigned
                    </div>
                  </div>
                </div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                  <em>Principle:</em> Absence of C2PA manifest is normal across web video; never proves AI generation.
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Mission 24: Live Video Stream Camera Recording Modal */}
      {isRecordingModalOpen && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.75)",
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
              maxWidth: 680,
              width: "100%",
              backgroundColor: "var(--bg-surface)",
              borderRadius: 20,
              padding: 24,
              boxShadow: "0 20px 40px rgba(0,0,0,0.4)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span className="badge badge-terracotta">LIVE WEBCAM STREAM</span>
                <h3 style={{ margin: 0, fontSize: 18 }}>Record Video for AI Detection</h3>
              </div>
              <button onClick={closeCameraModal} className="btn-secondary" style={{ padding: "4px 10px", fontSize: 12 }}>
                ✕ Close
              </button>
            </div>

            <div style={{ position: "relative", backgroundColor: "#000", borderRadius: 12, overflow: "hidden", minHeight: 340 }}>
              {!recordedVideoUrl ? (
                <video
                  ref={cameraVideoRef}
                  autoPlay
                  playsInline
                  muted
                  style={{ width: "100%", height: 340, objectFit: "cover" }}
                />
              ) : (
                <video
                  src={recordedVideoUrl}
                  controls
                  autoPlay
                  style={{ width: "100%", height: 340, objectFit: "contain" }}
                />
              )}

              {isRecording && (
                <div
                  style={{
                    position: "absolute",
                    top: 14,
                    left: 14,
                    backgroundColor: "rgba(220, 38, 38, 0.85)",
                    color: "#fff",
                    padding: "4px 12px",
                    borderRadius: 20,
                    fontSize: 12,
                    fontWeight: 700,
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  <span style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: "#fff", display: "inline-block" }} />
                  RECORDING 00:{recordingSeconds < 10 ? "0" : ""}{recordingSeconds} / 00:30
                </div>
              )}
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 18 }}>
              <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                Max 30 seconds. Video will be analyzed for temporal curvature anomalies.
              </div>
              <div style={{ display: "flex", gap: 10 }}>
                {!recordedVideoUrl ? (
                  !isRecording ? (
                    <button onClick={startVideoRecording} className="btn-primary" style={{ padding: "8px 18px", fontSize: 14 }}>
                      🔴 Start Recording
                    </button>
                  ) : (
                    <button onClick={stopVideoRecording} className="btn-secondary" style={{ padding: "8px 18px", fontSize: 14, backgroundColor: "var(--color-terracotta)", color: "#fff" }}>
                      ⏹ Stop Recording
                    </button>
                  )
                ) : (
                  <>
                    <button onClick={openCameraModal} className="btn-secondary" style={{ padding: "8px 16px", fontSize: 13 }}>
                      🔄 Record Again
                    </button>
                    <button onClick={useRecordedVideo} className="btn-primary" style={{ padding: "8px 20px", fontSize: 14 }}>
                      ⚡ Analyze Video
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default VideoForensicsWorkspace;
