import React, { useState, useEffect, useRef } from "react";
import { withBase } from "../../services/env";

// ============================================================================
// SECURA SOCIAL SUITE (MISSION 26) — ULTRA-REALISTIC SOCIAL MEDIA SIMULATION
// Pixel-Perfect Instagram, WhatsApp Web, Telegram Web & Secura Shield RAG
// ============================================================================

interface SocialUser {
  id: string;
  username: string;
  display_name: string;
  avatar_url: string;
  bio: string;
  phone_number: string;
  followers_count: number;
  following_count: number;
  posts_count: number;
}

interface SocialPost {
  id: string;
  user_id: string;
  username: string;
  display_name: string;
  avatar_url: string;
  media_url: string;
  media_type: "image" | "video";
  caption: string;
  tags: string[];
  likes_count: number;
  comments_count: number;
  created_at: string;
  liked_by_me: boolean;
  canonical_score?: number;
  canonical_verdict?: string;
  is_ai_generated?: boolean;
}

interface SocialComment {
  id: string;
  post_id: string;
  user_id: string;
  username: string;
  display_name: string;
  avatar_url: string;
  content: string;
  created_at: string;
}

interface Conversation {
  id: string;
  name: string;
  is_group: boolean;
  avatar_url: string;
  updated_at: string;
  unread_count: number;
  last_message: string;
  members: Array<{ id: string; username: string; display_name: string; avatar_url: string }>;
}

interface Message {
  id: string;
  conversation_id: string;
  sender_id: string;
  sender_name: string;
  sender_avatar: string;
  text: string;
  media_url: string | null;
  media_type: string | null;
  status: "sent" | "delivered" | "read";
  created_at: string;
}

interface TelegramChannel {
  id: string;
  title: string;
  username: string;
  description: string;
  avatar_url: string;
  subscribers_count: number;
  is_member: boolean;
  is_verified: boolean;
}

interface TelegramPost {
  id: string;
  channel_id: string;
  content: string;
  media_url: string | null;
  media_type: string | null;
  views_count: number;
  is_pinned: boolean;
  created_at: string;
  reactions: Record<string, number>;
  my_reaction?: string | null;
}

interface PolicyCitation {
  rule_id: string;
  statute: string;
  authority: string;
  effective_date: string;
  official_url: string;
  relevance_score: number;
  summary: string;
}

interface ModerationAudit {
  id: string;
  timestamp: string;
  application: string;
  media_type: string;
  canonical_verdict: string;
  raw_score: number;
  action: "ALLOW" | "BLOCK";
  matched_rules: string[];
  content_hash: string;
  explanation: string;
  latency_ms: number;
}

// ============================================================================
// MAIN SOCIAL SUITE COMPONENT
// ============================================================================
export const SecuraSocialSuite: React.FC<{ onBackToLab?: () => void }> = ({ onBackToLab }) => {
  const [activeApp, setActiveApp] = useState<"instagram" | "whatsapp" | "telegram" | "dashboard">("instagram");
  const [demoPolicyActive, setDemoPolicyActive] = useState<boolean>(true);
  const [users, setUsers] = useState<SocialUser[]>([]);
  const [currentUser, setCurrentUser] = useState<SocialUser | null>(null);

  // Moderation Block Modal State
  const [blockedResult, setBlockedResult] = useState<{
    canonical_verdict: string;
    raw_score: number;
    action: string;
    explanation: string;
    citations: PolicyCitation[];
    matched_rules: string[];
  } | null>(null);

  const [notification, setNotification] = useState<{ text: string; type: "success" | "error" | "info" } | null>(null);

  const showNotify = (text: string, type: "success" | "error" | "info" = "info") => {
    setNotification({ text, type });
    setTimeout(() => setNotification(null), 4500);
  };

  useEffect(() => {
    fetchUsers();
    fetchPolicyConfig();
  }, []);

  const fetchUsers = async () => {
    try {
      const res = await fetch(withBase("/api/v1/social/users"));
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
        if (data.length > 0 && !currentUser) {
          setCurrentUser(data[0]);
        }
      }
    } catch (e) {
      console.error("Failed to fetch social users", e);
    }
  };

  const fetchPolicyConfig = async () => {
    try {
      const res = await fetch(withBase("/api/v1/social/policy/config"));
      if (res.ok) {
        const data = await res.json();
        setDemoPolicyActive(data.block_ai_generated_media);
      }
    } catch (e) {
      console.error("Failed to fetch policy config", e);
    }
  };

  const toggleDemoPolicy = async () => {
    try {
      const res = await fetch(withBase("/api/v1/social/policy/config"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ block_ai_generated_media: !demoPolicyActive }),
      });
      if (res.ok) {
        const data = await res.json();
        setDemoPolicyActive(data.block_ai_generated_media);
        showNotify(
          data.block_ai_generated_media
            ? "🛡️ AI Interception ACTIVE: Synthetic uploads will be blocked pre-publication."
            : "⚠️ AI Interception BYPASS: Synthetic uploads allowed with transparency labels.",
          data.block_ai_generated_media ? "success" : "info"
        );
      }
    } catch (e) {
      showNotify("Failed to update policy toggle", "error");
    }
  };

  const resetDatabase = async () => {
    if (!window.confirm("Reset sandbox database? All demo posts, messages, and audits will return to baseline state.")) return;
    try {
      const res = await fetch(withBase("/api/v1/social/reset"), { method: "POST" });
      if (res.ok) {
        showNotify("Sandbox database reset to baseline.", "success");
        fetchUsers();
        window.location.reload();
      }
    } catch (e) {
      showNotify("Reset failed", "error");
    }
  };

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#0F172A", color: "#F8FAFC", fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" }}>
      {/* ==================================================================== */}
      {/* TOP FLOATING NAVIGATION DOCK                                         */}
      {/* ==================================================================== */}
      <header style={{
        position: "sticky",
        top: 0,
        zIndex: 100,
        backgroundColor: "rgba(15, 23, 42, 0.92)",
        backdropFilter: "blur(16px)",
        borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
        padding: "10px 24px",
      }}>
        <div style={{ maxWidth: "1600px", margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "14px" }}>
          {/* Brand & Lab Exit */}
          <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
            {onBackToLab && (
              <button
                onClick={onBackToLab}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  backgroundColor: "rgba(255, 255, 255, 0.06)",
                  border: "1px solid rgba(255, 255, 255, 0.12)",
                  color: "#94A3B8",
                  padding: "6px 12px",
                  borderRadius: "8px",
                  fontSize: "0.82rem",
                  fontWeight: 600,
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.color = "#FFF")}
                onMouseLeave={(e) => (e.currentTarget.style.color = "#94A3B8")}
              >
                ← Return to Lab
              </button>
            )}
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <div style={{
                width: "28px",
                height: "28px",
                borderRadius: "8px",
                background: "linear-gradient(135deg, #3B82F6, #8B5CF6)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 800,
                fontSize: "0.9rem",
                color: "#FFF",
              }}>
                S
              </div>
              <div>
                <span style={{ fontWeight: 800, fontSize: "0.95rem", letterSpacing: "0.04em", color: "#FFF" }}>
                  SECURA <span style={{ color: "#38BDF8" }}>SOCIAL SUITE</span>
                </span>
                <span style={{ marginLeft: "8px", fontSize: "0.68rem", backgroundColor: "rgba(56, 189, 248, 0.15)", color: "#38BDF8", padding: "2px 6px", borderRadius: "4px", fontWeight: 700 }}>
                  MISSION 26
                </span>
              </div>
            </div>
          </div>

          {/* Social Client Switcher Tabs */}
          <nav style={{
            display: "flex",
            backgroundColor: "rgba(30, 41, 59, 0.7)",
            padding: "4px",
            borderRadius: "12px",
            border: "1px solid rgba(255, 255, 255, 0.06)",
            gap: "4px",
          }}>
            {/* Instagram Tab */}
            <button
              onClick={() => setActiveApp("instagram")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 18px",
                borderRadius: "8px",
                border: "none",
                cursor: "pointer",
                fontWeight: 700,
                fontSize: "0.86rem",
                transition: "all 0.25s ease",
                backgroundColor: activeApp === "instagram" ? "rgba(225, 48, 108, 0.2)" : "transparent",
                color: activeApp === "instagram" ? "#FFF" : "#94A3B8",
                boxShadow: activeApp === "instagram" ? "0 0 16px rgba(225, 48, 108, 0.3)" : "none",
                outline: activeApp === "instagram" ? "1px solid rgba(225, 48, 108, 0.5)" : "none",
              }}
            >
              <span style={{
                display: "inline-block",
                width: "18px",
                height: "18px",
                borderRadius: "5px",
                background: "linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%)",
              }} />
              Instagram
            </button>

            {/* WhatsApp Tab */}
            <button
              onClick={() => setActiveApp("whatsapp")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 18px",
                borderRadius: "8px",
                border: "none",
                cursor: "pointer",
                fontWeight: 700,
                fontSize: "0.86rem",
                transition: "all 0.25s ease",
                backgroundColor: activeApp === "whatsapp" ? "rgba(37, 211, 102, 0.2)" : "transparent",
                color: activeApp === "whatsapp" ? "#FFF" : "#94A3B8",
                boxShadow: activeApp === "whatsapp" ? "0 0 16px rgba(37, 211, 102, 0.3)" : "none",
                outline: activeApp === "whatsapp" ? "1px solid rgba(37, 211, 102, 0.5)" : "none",
              }}
            >
              <span style={{
                width: "18px",
                height: "18px",
                borderRadius: "50%",
                backgroundColor: "#25D366",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "11px",
              }}>💬</span>
              WhatsApp
            </button>

            {/* Telegram Tab */}
            <button
              onClick={() => setActiveApp("telegram")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 18px",
                borderRadius: "8px",
                border: "none",
                cursor: "pointer",
                fontWeight: 700,
                fontSize: "0.86rem",
                transition: "all 0.25s ease",
                backgroundColor: activeApp === "telegram" ? "rgba(34, 158, 217, 0.2)" : "transparent",
                color: activeApp === "telegram" ? "#FFF" : "#94A3B8",
                boxShadow: activeApp === "telegram" ? "0 0 16px rgba(34, 158, 217, 0.3)" : "none",
                outline: activeApp === "telegram" ? "1px solid rgba(34, 158, 217, 0.5)" : "none",
              }}
            >
              <span style={{
                width: "18px",
                height: "18px",
                borderRadius: "50%",
                backgroundColor: "#229ED9",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "11px",
                color: "#FFF",
              }}>✈</span>
              Telegram
            </button>

            {/* Admin Console Tab */}
            <button
              onClick={() => setActiveApp("dashboard")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 18px",
                borderRadius: "8px",
                border: "none",
                cursor: "pointer",
                fontWeight: 700,
                fontSize: "0.86rem",
                transition: "all 0.25s ease",
                backgroundColor: activeApp === "dashboard" ? "rgba(139, 92, 246, 0.2)" : "transparent",
                color: activeApp === "dashboard" ? "#FFF" : "#94A3B8",
                boxShadow: activeApp === "dashboard" ? "0 0 16px rgba(139, 92, 246, 0.3)" : "none",
                outline: activeApp === "dashboard" ? "1px solid rgba(139, 92, 246, 0.5)" : "none",
              }}
            >
              <span>🛡️</span>
              Admin & Policy RAG
            </button>
          </nav>

          {/* Right Action Controls: Persona Switcher, Policy Toggle, Reset */}
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            {/* User Persona Picker */}
            <div style={{ display: "flex", alignItems: "center", gap: "6px", backgroundColor: "rgba(30, 41, 59, 0.8)", padding: "4px 8px", borderRadius: "8px", border: "1px solid rgba(255, 255, 255, 0.08)" }}>
              <span style={{ fontSize: "0.75rem", color: "#64748B" }}>Active:</span>
              <select
                value={currentUser?.id || ""}
                onChange={(e) => {
                  const u = users.find((x) => x.id === e.target.value);
                  if (u) setCurrentUser(u);
                }}
                style={{
                  background: "transparent",
                  color: "#E2E8F0",
                  border: "none",
                  fontSize: "0.82rem",
                  fontWeight: 600,
                  outline: "none",
                  cursor: "pointer",
                }}
              >
                {users.map((u) => (
                  <option key={u.id} value={u.id} style={{ backgroundColor: "#1E293B", color: "#FFF" }}>
                    @{u.username} ({u.display_name})
                  </option>
                ))}
              </select>
            </div>

            {/* AI Policy Interception Toggle */}
            <button
              onClick={toggleDemoPolicy}
              title="Toggle Pre-Publication AI Interception Policy"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "6px 14px",
                borderRadius: "8px",
                border: demoPolicyActive ? "1px solid rgba(239, 68, 68, 0.4)" : "1px solid rgba(100, 116, 139, 0.4)",
                backgroundColor: demoPolicyActive ? "rgba(239, 68, 68, 0.15)" : "rgba(30, 41, 59, 0.6)",
                color: demoPolicyActive ? "#F87171" : "#94A3B8",
                fontWeight: 700,
                fontSize: "0.78rem",
                cursor: "pointer",
                transition: "all 0.2s ease",
              }}
            >
              <span style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                backgroundColor: demoPolicyActive ? "#EF4444" : "#64748B",
                boxShadow: demoPolicyActive ? "0 0 8px #EF4444" : "none",
              }} />
              {demoPolicyActive ? "AI INTERCEPT: ON" : "AI INTERCEPT: OFF"}
            </button>

            {/* Reset Sandbox Button */}
            <button
              onClick={resetDatabase}
              title="Reset Sandbox Database to Initial Seed State"
              style={{
                backgroundColor: "rgba(255, 255, 255, 0.05)",
                border: "1px solid rgba(255, 255, 255, 0.1)",
                color: "#94A3B8",
                padding: "6px 10px",
                borderRadius: "8px",
                fontSize: "0.78rem",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              ↻ Reset DB
            </button>
          </div>
        </div>
      </header>

      {/* Global Notification Banner */}
      {notification && (
        <div style={{
          backgroundColor: notification.type === "error" ? "#7F1D1D" : notification.type === "success" ? "#065F46" : "#1E3A8A",
          color: "#FFF",
          padding: "10px 24px",
          textAlign: "center",
          fontSize: "0.88rem",
          fontWeight: 600,
          boxShadow: "0 4px 12px rgba(0, 0, 0, 0.3)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "8px",
        }}>
          {notification.text}
        </div>
      )}

      {/* ==================================================================== */}
      {/* ACTIVE CLIENT WORKSPACE                                              */}
      {/* ==================================================================== */}
      <main style={{ padding: "20px", maxWidth: "1600px", margin: "0 auto" }}>
        {activeApp === "instagram" && (
          <RealInstagramClient
            currentUser={currentUser}
            onBlocked={(res) => setBlockedResult(res)}
            showNotify={showNotify}
          />
        )}
        {activeApp === "whatsapp" && (
          <RealWhatsAppClient
            currentUser={currentUser}
            users={users}
            onBlocked={(res) => setBlockedResult(res)}
            showNotify={showNotify}
          />
        )}
        {activeApp === "telegram" && (
          <RealTelegramClient
            currentUser={currentUser}
            onBlocked={(res) => setBlockedResult(res)}
            showNotify={showNotify}
          />
        )}
        {activeApp === "dashboard" && (
          <RealModerationDashboard
            demoPolicyActive={demoPolicyActive}
            showNotify={showNotify}
          />
        )}
      </main>

      {/* ==================================================================== */}
      {/* CYBER FORENSIC PRE-PUBLICATION / PRE-SEND BLOCK MODAL                */}
      {/* ==================================================================== */}
      {blockedResult && (
        <div style={{
          position: "fixed",
          inset: 0,
          zIndex: 1000,
          backgroundColor: "rgba(0, 0, 0, 0.85)",
          backdropFilter: "blur(12px)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "20px",
        }}>
          <div style={{
            maxWidth: "680px",
            width: "100%",
            backgroundColor: "#18181B",
            borderRadius: "16px",
            border: "2px solid #EF4444",
            boxShadow: "0 0 50px rgba(239, 68, 68, 0.35)",
            overflow: "hidden",
            color: "#FFF",
          }}>
            {/* Modal Header */}
            <div style={{
              background: "linear-gradient(90deg, #7F1D1D, #991B1B)",
              padding: "16px 20px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span style={{ fontSize: "1.4rem" }}>🛑</span>
                <div>
                  <h3 style={{ margin: 0, fontSize: "1.1rem", fontWeight: 800, letterSpacing: "0.02em" }}>
                    PRE-PUBLICATION INTERCEPTION: HTTP 403 FORBIDDEN
                  </h3>
                  <span style={{ fontSize: "0.75rem", color: "#FCA5A5" }}>
                    Secura AI Real-Time Content Quarantine Engine
                  </span>
                </div>
              </div>
              <button
                onClick={() => setBlockedResult(null)}
                style={{
                  background: "rgba(255, 255, 255, 0.15)",
                  border: "none",
                  color: "#FFF",
                  width: "30px",
                  height: "30px",
                  borderRadius: "50%",
                  cursor: "pointer",
                  fontWeight: 800,
                  fontSize: "1rem",
                }}
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div style={{ padding: "24px" }}>
              {/* Verdict & Score Gauge */}
              <div style={{
                backgroundColor: "#27272A",
                borderRadius: "12px",
                padding: "16px",
                marginBottom: "20px",
                border: "1px solid #3F3F46",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}>
                <div>
                  <div style={{ fontSize: "0.75rem", color: "#A1A1AA", fontWeight: 700, textTransform: "uppercase" }}>
                    Model: {(blockedResult as any).model_name || (blockedResult as any).decision?.model_name || (((blockedResult as any).media_type === "video" || (blockedResult as any).decision?.media_type === "video") ? "Secura Multi-Branch Video Forensics" : "UniversalFakeDetect-CLIP-ViT-L/14")}
                  </div>
                  <div style={{ fontSize: "1.4rem", fontWeight: 900, color: "#EF4444", marginTop: "2px" }}>
                    {(blockedResult as any).canonical_verdict || (blockedResult as any).decision?.canonical_verdict || "AI_GENERATED"}
                  </div>
                  <div style={{ fontSize: "0.82rem", color: "#D4D4D8", marginTop: "4px" }}>
                    {(blockedResult as any).explanation || (blockedResult as any).decision?.explanation || (blockedResult as any).reason || "Content quarantined: AI-generated media intercepted."}
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: "2rem", fontWeight: 900, color: "#EF4444" }}>
                    {(((blockedResult as any).canonical_score ?? (blockedResult as any).decision?.canonical_score ?? (blockedResult as any).raw_score ?? 0.88) * 100).toFixed(1)}%
                  </div>
                  <div style={{ fontSize: "0.72rem", color: "#A1A1AA", fontWeight: 600 }}>
                    Deepfake Probability
                  </div>
                </div>
              </div>

              {/* Legal Violations & Citations */}
              <div style={{ marginBottom: "20px" }}>
                <div style={{ fontSize: "0.82rem", fontWeight: 800, color: "#E4E4E7", marginBottom: "8px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  Statutory Non-Compliance Citations (MeitY & BNS 2023)
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxHeight: "180px", overflowY: "auto" }}>
                  {((blockedResult as any).citations || (blockedResult as any).decision?.citations || []).length > 0 ? (
                    ((blockedResult as any).citations || (blockedResult as any).decision?.citations || []).map((c: any, idx: number) => (
                      <div key={idx} style={{ backgroundColor: "#27272A", padding: "10px 14px", borderRadius: "8px", borderLeft: "3px solid #EF4444" }}>
                        <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "#FCA5A5" }}>
                          {c.statute} ({c.rule_id})
                        </div>
                        <div style={{ fontSize: "0.74rem", color: "#A1A1AA", marginTop: "2px" }}>
                          {c.authority} • {c.summary}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div style={{ backgroundColor: "#27272A", padding: "10px 14px", borderRadius: "8px", borderLeft: "3px solid #EF4444", fontSize: "0.82rem", color: "#FCA5A5" }}>
                      Violation of IT Rules 2021/2023 Rule 3(1)(b) & MeitY Deepfake Advisory March 2024 (Mandatory Platform Removal / Due Diligence).
                    </div>
                  )}
                </div>
              </div>

              {/* Action Button */}
              <button
                onClick={() => setBlockedResult(null)}
                style={{
                  width: "100%",
                  padding: "12px",
                  borderRadius: "8px",
                  backgroundColor: "#EF4444",
                  border: "none",
                  color: "#FFF",
                  fontWeight: 800,
                  fontSize: "0.92rem",
                  cursor: "pointer",
                  letterSpacing: "0.02em",
                  boxShadow: "0 4px 14px rgba(239, 68, 68, 0.4)",
                }}
              >
                Acknowledge & Quarantine Media
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// 1. REAL INSTAGRAM CLIENT (PIXEL-PERFECT WEB EXPERIENCE)
// ============================================================================
const RealInstagramClient: React.FC<{
  currentUser: SocialUser | null;
  onBlocked: (res: any) => void;
  showNotify: (text: string, type: "success" | "error" | "info") => void;
}> = ({ currentUser, onBlocked, showNotify }) => {
  const [posts, setPosts] = useState<SocialPost[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [isCreatingPost, setIsCreatingPost] = useState<boolean>(false);
  const [caption, setCaption] = useState<string>("");
  const [tags] = useState<string>("photography, delhi");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isLiveCamera, setIsLiveCamera] = useState<boolean>(false);
  const [isInspecting, setIsInspecting] = useState<boolean>(false);
  const [preScreenResult, setPreScreenResult] = useState<any | null>(null);
  const [isPreScreening, setIsPreScreening] = useState<boolean>(false);
  const [activeAiInfoPopover, setActiveAiInfoPopover] = useState<string | null>(null);

  // Comments State
  const [commentsMap, setCommentsMap] = useState<Record<string, SocialComment[]>>({});
  const [activeCommentPost, setActiveCommentPost] = useState<string | null>(null);
  const [commentInput, setCommentInput] = useState<string>("");

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    fetchFeed();
  }, [currentUser]);

  const fetchFeed = async () => {
    setLoading(true);
    try {
      const url = currentUser ? `/api/v1/social/instagram/feed?user_id=${currentUser.id}` : "/api/v1/social/instagram/feed";
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setPosts(data);
      }
    } catch (e) {
      console.error("Failed to fetch Instagram feed", e);
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setPreScreenResult(null);
      setIsLiveCamera(false);
    }
  };

  const handleRunPreScreening = async () => {
    if (!selectedFile) return;
    setIsPreScreening(true);
    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("app_source", "instagram");
    if (currentUser) formData.append("user_id", currentUser.id);
    formData.append("caption", caption);

    try {
      const res = await fetch(withBase("/api/v1/social/inspect-media"), {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        setPreScreenResult(data);
        const isSynthetic = data.canonical_verdict === "AI_GENERATED" || data.canonical_verdict === "AI GENERATED";
        showNotify(
          isSynthetic
            ? "Pre-Screening Complete: Synthetic media signature detected!"
            : "Pre-Screening Complete: Media verified as Authentic.",
          isSynthetic ? "error" : "success"
        );
      } else {
        showNotify("Pre-screening request failed.", "error");
      }
    } catch (e) {
      showNotify("Pre-screening network error.", "error");
    } finally {
      setIsPreScreening(false);
    }
  };

  const startLiveCamera = async () => {
    setIsLiveCamera(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
    } catch (e) {
      showNotify("Camera permission denied or camera unavailable.", "error");
      setIsLiveCamera(false);
    }
  };

  const captureCameraPhoto = () => {
    if (videoRef.current && canvasRef.current) {
      const canvas = canvasRef.current;
      const video = videoRef.current;
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      const ctx = canvas.getContext("2d");
      if (ctx) {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        canvas.toBlob((blob) => {
          if (blob) {
            const file = new File([blob], `camera_snap_${Date.now()}.jpg`, { type: "image/jpeg" });
            setSelectedFile(file);
            setPreviewUrl(URL.createObjectURL(blob));
            // stop camera tracks
            if (video.srcObject) {
              const stream = video.srcObject as MediaStream;
              stream.getTracks().forEach((t) => t.stop());
            }
            setIsLiveCamera(false);
          }
        }, "image/jpeg", 0.95);
      }
    }
  };

  const handlePublishPost = async () => {
    if (!selectedFile || !currentUser) {
      showNotify("Please select an image or capture a camera photo first.", "error");
      return;
    }

    setIsInspecting(true);
    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("user_id", currentUser.id);
    formData.append("caption", caption);
    formData.append("tags", tags);

    try {
      const res = await fetch(withBase("/api/v1/social/instagram/posts"), {
        method: "POST",
        body: formData,
      });

      const body = await res.json();
      if (res.status === 403 || body.blocked) {
        onBlocked(body);
        showNotify("Upload quarantined: AI-generated media intercepted pre-publication.", "error");
      } else if (res.ok) {
        showNotify("Post published to Instagram feed!", "success");
        setIsCreatingPost(false);
        setSelectedFile(null);
        setPreviewUrl(null);
        setCaption("");
        fetchFeed();
      } else {
        showNotify(body.detail || "Upload failed", "error");
      }
    } catch (e) {
      showNotify("Network error while inspecting media", "error");
    } finally {
      setIsInspecting(false);
    }
  };

  const toggleLike = async (postId: string) => {
    if (!currentUser) return;
    try {
      const res = await fetch(withBase(`/api/v1/social/instagram/posts/${postId}/like`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: currentUser.id }),
      });
      if (res.ok) {
        const data = await res.json();
        setPosts((prev) =>
          prev.map((p) =>
            p.id === postId
              ? {
                  ...p,
                  liked_by_me: data.liked,
                  likes_count: data.likes_count,
                }
              : p
          )
        );
      }
    } catch (e) {
      console.error("Like toggle failed", e);
    }
  };

  const loadComments = async (postId: string) => {
    setActiveCommentPost(postId);
    try {
      const res = await fetch(withBase(`/api/v1/social/instagram/posts/${postId}/comments`));
      if (res.ok) {
        const data = await res.json();
        setCommentsMap((prev) => ({ ...prev, [postId]: data }));
      }
    } catch (e) {
      console.error("Failed to load comments", e);
    }
  };

  const submitComment = async (postId: string) => {
    if (!commentInput.trim() || !currentUser) return;
    try {
      const res = await fetch(withBase(`/api/v1/social/instagram/posts/${postId}/comments`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: currentUser.id, text: commentInput }),
      });
      if (res.ok) {
        setCommentInput("");
        loadComments(postId);
        fetchFeed();
      } else {
        const err = await res.json();
        showNotify(err.detail || "Comment rejected", "error");
      }
    } catch (e) {
      showNotify("Failed to post comment", "error");
    }
  };

  return (
    <div style={{ maxWidth: "600px", margin: "0 auto", paddingBottom: "60px" }}>
      {/* ==================================================================== */}
      {/* INSTAGRAM HEADER BAR                                                 */}
      {/* ==================================================================== */}
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "14px 4px 18px 4px",
        borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
        marginBottom: "16px",
      }}>
        {/* Instagram Script Logo Typography */}
        <h1 style={{
          margin: 0,
          fontFamily: "'Brush Script MT', 'Grand Hotel', cursive, sans-serif",
          fontSize: "2.3rem",
          fontWeight: 500,
          background: "linear-gradient(45deg, #FFF, #E2E8F0)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          letterSpacing: "0.02em",
          userSelect: "none",
        }}>
          Instagram
        </h1>

        {/* Action Icons */}
        <div style={{ display: "flex", alignItems: "center", gap: "18px" }}>
          <button
            onClick={() => setIsCreatingPost(true)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              background: "linear-gradient(45deg, #f09433 0%, #dc2743 50%, #bc1888 100%)",
              border: "none",
              color: "#FFF",
              padding: "7px 16px",
              borderRadius: "20px",
              fontWeight: 700,
              fontSize: "0.82rem",
              cursor: "pointer",
              boxShadow: "0 4px 12px rgba(220, 39, 67, 0.35)",
            }}
          >
            <span>+</span> Create
          </button>
        </div>
      </div>

      {/* ==================================================================== */}
      {/* STORIES TRAY (AUTHENTIC INSTAGRAM CIRCULAR GRADIENTS)                */}
      {/* ==================================================================== */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: "14px",
        overflowX: "auto",
        paddingBottom: "16px",
        marginBottom: "20px",
        scrollbarWidth: "none",
        borderBottom: "1px solid rgba(255, 255, 255, 0.06)",
      }}>
        {/* Current User Story */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "6px", cursor: "pointer", flexShrink: 0 }}>
          <div style={{
            position: "relative",
            width: "66px",
            height: "66px",
            borderRadius: "50%",
            padding: "2px",
            background: "rgba(255, 255, 255, 0.2)",
          }}>
            <img
              src={currentUser?.avatar_url || "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150"}
              alt="Your story"
              style={{ width: "100%", height: "100%", borderRadius: "50%", objectFit: "cover" }}
            />
            <div style={{
              position: "absolute",
              bottom: "0",
              right: "0",
              width: "20px",
              height: "20px",
              borderRadius: "50%",
              backgroundColor: "#0095F6",
              color: "#FFF",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "13px",
              fontWeight: 800,
              border: "2px solid #0F172A",
            }}>
              +
            </div>
          </div>
          <span style={{ fontSize: "0.72rem", color: "#94A3B8" }}>Your story</span>
        </div>

        {/* Other Personas Stories */}
        {[
          { name: "priya_cyber", avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150", live: true },
          { name: "delhi_police", avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150", live: false },
          { name: "tech_forensics", avatar: "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150", live: false },
          { name: "neha_delhi", avatar: "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150", live: false },
        ].map((story, i) => (
          <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "6px", cursor: "pointer", flexShrink: 0 }}>
            <div style={{
              width: "66px",
              height: "66px",
              borderRadius: "50%",
              padding: "2.5px",
              background: "linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%)",
            }}>
              <div style={{ width: "100%", height: "100%", borderRadius: "50%", padding: "2px", backgroundColor: "#0F172A" }}>
                <img
                  src={story.avatar}
                  alt={story.name}
                  style={{ width: "100%", height: "100%", borderRadius: "50%", objectFit: "cover" }}
                />
              </div>
            </div>
            <span style={{ fontSize: "0.72rem", color: "#CBD5E1", maxWidth: "66px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {story.name}
            </span>
          </div>
        ))}
      </div>

      {/* ==================================================================== */}
      {/* CREATE POST MODAL                                                    */}
      {/* ==================================================================== */}
      {isCreatingPost && (
        <div style={{
          position: "fixed",
          inset: 0,
          zIndex: 500,
          backgroundColor: "rgba(0, 0, 0, 0.8)",
          backdropFilter: "blur(8px)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "16px",
        }}>
          <div style={{
            maxWidth: "520px",
            width: "100%",
            backgroundColor: "#1E293B",
            borderRadius: "16px",
            border: "1px solid rgba(255, 255, 255, 0.12)",
            boxShadow: "0 20px 40px rgba(0, 0, 0, 0.5)",
            overflow: "hidden",
          }}>
            {/* Header */}
            <div style={{
              padding: "14px 18px",
              borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}>
              <button
                onClick={() => {
                  setIsCreatingPost(false);
                  setSelectedFile(null);
                  setPreviewUrl(null);
                  setIsLiveCamera(false);
                }}
                style={{ background: "none", border: "none", color: "#94A3B8", fontSize: "1.1rem", cursor: "pointer" }}
              >
                ✕
              </button>
              <span style={{ fontWeight: 700, fontSize: "0.95rem", color: "#FFF" }}>Create new post</span>
              <button
                onClick={handlePublishPost}
                disabled={!selectedFile || isInspecting}
                style={{
                  background: "none",
                  border: "none",
                  color: selectedFile && !isInspecting ? "#0095F6" : "#64748B",
                  fontWeight: 700,
                  fontSize: "0.92rem",
                  cursor: selectedFile && !isInspecting ? "pointer" : "not-allowed",
                }}
              >
                {isInspecting ? "Scanning..." : "Share"}
              </button>
            </div>

            {/* Media Upload / Live Camera Viewfinder */}
            <div style={{ padding: "20px" }}>
              {!previewUrl && !isLiveCamera && (
                <div style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: "40px 20px",
                  border: "2px dashed rgba(255, 255, 255, 0.15)",
                  borderRadius: "12px",
                  gap: "14px",
                }}>
                  <div style={{ fontSize: "2.5rem" }}>📷</div>
                  <div style={{ fontSize: "0.95rem", fontWeight: 600, color: "#E2E8F0" }}>
                    Select photos and videos here
                  </div>
                  <div style={{ display: "flex", gap: "10px" }}>
                    <label style={{
                      backgroundColor: "#0095F6",
                      color: "#FFF",
                      padding: "8px 18px",
                      borderRadius: "8px",
                      fontSize: "0.85rem",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}>
                      Select from computer
                      <input type="file" accept="image/*,video/*" onChange={handleFileChange} style={{ display: "none" }} />
                    </label>
                    <button
                      onClick={startLiveCamera}
                      style={{
                        backgroundColor: "rgba(255, 255, 255, 0.08)",
                        border: "1px solid rgba(255, 255, 255, 0.15)",
                        color: "#FFF",
                        padding: "8px 18px",
                        borderRadius: "8px",
                        fontSize: "0.85rem",
                        fontWeight: 700,
                        cursor: "pointer",
                      }}
                    >
                      Use Live Camera
                    </button>
                  </div>
                </div>
              )}

              {/* Live Camera Viewfinder */}
              {isLiveCamera && (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "12px" }}>
                  <video ref={videoRef} autoPlay playsInline style={{ width: "100%", borderRadius: "10px", maxHeight: "300px", objectFit: "cover" }} />
                  <canvas ref={canvasRef} style={{ display: "none" }} />
                  <button
                    onClick={captureCameraPhoto}
                    style={{
                      backgroundColor: "#EF4444",
                      color: "#FFF",
                      border: "none",
                      padding: "10px 24px",
                      borderRadius: "30px",
                      fontWeight: 800,
                      cursor: "pointer",
                      boxShadow: "0 0 16px rgba(239, 68, 68, 0.5)",
                    }}
                  >
                    ● Take Snapshot
                  </button>
                </div>
              )}

              {/* Media Preview & Caption Box */}
              {previewUrl && (
                <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                  <div style={{ position: "relative", width: "100%", maxHeight: "300px", overflow: "hidden", borderRadius: "10px" }}>
                    <img src={previewUrl} alt="Preview" style={{ width: "100%", maxHeight: "300px", objectFit: "contain", backgroundColor: "#000" }} />
                    <button
                      onClick={() => { setSelectedFile(null); setPreviewUrl(null); }}
                      style={{ position: "absolute", top: "10px", right: "10px", backgroundColor: "rgba(0,0,0,0.6)", color: "#FFF", border: "none", borderRadius: "50%", width: "28px", height: "28px", cursor: "pointer" }}
                    >
                      ✕
                    </button>
                  </div>

                  <div>
                    <textarea
                      placeholder="Write a caption..."
                      value={caption}
                      onChange={(e) => setCaption(e.target.value)}
                      rows={3}
                      style={{
                        width: "100%",
                        backgroundColor: "#0F172A",
                        border: "1px solid rgba(255, 255, 255, 0.1)",
                        borderRadius: "8px",
                        color: "#FFF",
                        padding: "10px",
                        fontSize: "0.88rem",
                        boxSizing: "border-box",
                        outline: "none",
                      }}
                    />
                  </div>

                  {/* Pre-Screening Action & Live Scorecard */}
                  <div style={{ display: "flex", gap: "10px" }}>
                    <button
                      type="button"
                      onClick={handleRunPreScreening}
                      disabled={isPreScreening || !selectedFile}
                      style={{
                        flex: 1,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "8px",
                        backgroundColor: "rgba(56, 189, 248, 0.12)",
                        border: "1px solid #38BDF8",
                        color: "#38BDF8",
                        padding: "9px 16px",
                        borderRadius: "8px",
                        fontSize: "0.85rem",
                        fontWeight: 700,
                        cursor: isPreScreening ? "wait" : "pointer",
                      }}
                    >
                      <span>🔍</span> {isPreScreening ? "Scanning Forensic Pipeline..." : "Run AI Pre-Screening"}
                    </button>
                  </div>

                  {preScreenResult && (
                    <div style={{
                      backgroundColor: "#0B132B",
                      border: `1px solid ${(preScreenResult.canonical_verdict === "AI_GENERATED" || preScreenResult.canonical_verdict === "AI GENERATED") ? "#EF4444" : "#10B981"}`,
                      borderRadius: "10px",
                      padding: "12px 14px",
                    }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                        <span style={{
                          fontSize: "0.78rem",
                          fontWeight: 800,
                          color: (preScreenResult.canonical_verdict === "AI_GENERATED" || preScreenResult.canonical_verdict === "AI GENERATED") ? "#F87171" : "#34D399",
                          display: "flex",
                          alignItems: "center",
                          gap: "6px",
                        }}>
                          <span>{preScreenResult.canonical_verdict === "AI_GENERATED" ? "⚠️" : "✅"}</span>
                          {preScreenResult.canonical_verdict === "AI_GENERATED" ? "AI-GENERATED MEDIA DETECTED" : "AUTHENTIC MEDIA CONFIRMED"}
                        </span>
                        <span style={{ fontSize: "0.85rem", fontWeight: 800, color: "#FFF" }}>
                          {((preScreenResult.canonical_score ?? 0) * 100).toFixed(1)}% Synthetic
                        </span>
                      </div>
                      <div style={{ fontSize: "0.74rem", color: "#94A3B8", lineHeight: 1.4 }}>
                        {preScreenResult.canonical_verdict === "AI_GENERATED"
                          ? "Notice: Per IT Rules 2021 Rule 3(1)(b)(v), this post will be tagged with an official '✨ AI Info: Created with AI' label or intercepted if active quarantine is enforced."
                          : (selectedFile && (selectedFile.type.startsWith("video/") || selectedFile.name.match(/\.(mp4|webm|avi|mov|mkv)$/i)))
                          ? "Zero synthetic motion or spatial artifacts detected across Secura Multi-Branch Video Forensics (Optical Flow, Spatial CNN, Temporal FFT)."
                          : "Zero synthetic artifacts detected across UniversalFakeDetect-CLIP-ViT-L/14 and Swin transformer forensics."}
                      </div>
                    </div>
                  )}

                  {/* Pre-publication scan note */}
                  <div style={{ fontSize: "0.74rem", color: "#94A3B8", display: "flex", alignItems: "center", gap: "6px" }}>
                    <span>🛡️</span> Content will be inspected by {selectedFile && (selectedFile.type.startsWith("video/") || selectedFile.name.match(/\.(mp4|webm|avi|mov|mkv)$/i)) ? "Secura Multi-Branch Video Forensics" : "UniversalFakeDetect-CLIP-ViT-L/14"} before publishing.
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* INSTAGRAM FEED POSTS                                                 */}
      {/* ==================================================================== */}
      {loading ? (
        <div style={{ textAlign: "center", padding: "40px", color: "#94A3B8" }}>Loading feed...</div>
      ) : posts.length === 0 ? (
        <div style={{ textAlign: "center", padding: "40px", color: "#94A3B8" }}>No posts in feed. Create the first one!</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "28px" }}>
          {posts.map((post) => (
            <article
              key={post.id}
              style={{
                backgroundColor: "#18181B",
                borderRadius: "16px",
                border: "1px solid rgba(255, 255, 255, 0.08)",
                overflow: "hidden",
                boxShadow: "0 8px 24px rgba(0, 0, 0, 0.3)",
              }}
            >
              {/* Post Header */}
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <img
                    src={post.avatar_url || "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150"}
                    alt={post.username}
                    style={{ width: "36px", height: "36px", borderRadius: "50%", objectFit: "cover", border: "1.5px solid #E1306C" }}
                  />
                  <div>
                    <div style={{ fontWeight: 700, fontSize: "0.88rem", color: "#FFF" }}>@{post.username}</div>
                    <div style={{ fontSize: "0.72rem", color: "#94A3B8" }}>New Delhi, India</div>
                  </div>
                </div>
                <span style={{ color: "#71717A", fontSize: "1.2rem", cursor: "pointer" }}>•••</span>
              </div>

              {/* Edge-to-Edge Media Container with Double-Click Like */}
              <div
                onDoubleClick={() => toggleLike(post.id)}
                style={{
                  position: "relative",
                  width: "100%",
                  aspectRatio: "1 / 1",
                  backgroundColor: "#000",
                  cursor: "pointer",
                }}
              >
                <img
                  src={post.media_url}
                  alt={post.caption}
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                />
              </div>

              {/* Official Instagram '✨ AI Info: Created with AI' Transparency Badge */}
              {(post.canonical_verdict === "AI_GENERATED" ||
                (post.canonical_score !== undefined && post.canonical_score >= 0.5) ||
                post.is_ai_generated ||
                post.caption.toLowerCase().includes("ai") ||
                (post.tags && Array.isArray(post.tags) && post.tags.some((t: string) => t.toLowerCase().includes("ai") || t.toLowerCase().includes("synthetic")))) && (
                <div style={{ position: "relative", padding: "8px 16px 2px 16px", backgroundColor: "#18181B" }}>
                  <button
                    onClick={() => setActiveAiInfoPopover(activeAiInfoPopover === post.id ? null : post.id)}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      backgroundColor: "rgba(255, 255, 255, 0.08)",
                      border: "1px solid rgba(255, 255, 255, 0.15)",
                      color: "#F1F5F9",
                      padding: "4px 10px",
                      borderRadius: "14px",
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      cursor: "pointer",
                      transition: "all 0.2s ease",
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.16)")}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.08)")}
                  >
                    <span style={{ color: "#F472B6" }}>✨</span>
                    <span>AI Info • Created with AI</span>
                    <span style={{ fontSize: "0.68rem", color: "#94A3B8" }}>ℹ️</span>
                  </button>

                  {activeAiInfoPopover === post.id && (
                    <div style={{
                      position: "absolute",
                      top: "100%",
                      left: "16px",
                      marginTop: "6px",
                      zIndex: 100,
                      width: "320px",
                      backgroundColor: "#1E293B",
                      border: "1px solid rgba(255, 255, 255, 0.15)",
                      borderRadius: "12px",
                      padding: "14px",
                      boxShadow: "0 10px 30px rgba(0, 0, 0, 0.6)",
                    }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px", fontWeight: 700, fontSize: "0.85rem", color: "#FFF" }}>
                          <span>✨</span> About this {post.media_type === "video" ? "video" : "media"}
                        </div>
                        <button
                          onClick={() => setActiveAiInfoPopover(null)}
                          style={{ background: "none", border: "none", color: "#94A3B8", cursor: "pointer", fontSize: "0.8rem" }}
                        >
                          ✕
                        </button>
                      </div>
                      <p style={{ margin: "0 0 8px 0", fontSize: "0.78rem", color: "#CBD5E1", lineHeight: 1.4 }}>
                        {post.media_type === "video" ? "Secura AI Multi-Branch Video Forensics detected synthetic generation traces across temporal motion and spatial representations." : "Secura AI UniversalFakeDetect detected synthetic generation traces across deep vision transformer representation layers."}
                      </p>
                      <div style={{ backgroundColor: "#0F172A", padding: "8px 10px", borderRadius: "8px", marginBottom: "8px", fontSize: "0.74rem" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", color: "#94A3B8", marginBottom: "4px" }}>
                          <span>Forensic Model:</span>
                          <strong style={{ color: "#38BDF8" }}>
                            {post.media_type === "video" ? "Secura Multi-Branch Video Forensics" : "UniversalFakeDetect-CLIP-ViT-L/14"}
                          </strong>
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", color: "#94A3B8", marginBottom: "2px" }}>
                          <span>Model Confidence:</span>
                          <strong style={{ color: "#F87171" }}>
                            {post.canonical_score !== undefined ? `${(post.canonical_score * 100).toFixed(1)}%` : "High Probability"}
                          </strong>
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", color: "#94A3B8" }}>
                          <span>Regulatory Ref:</span>
                          <span style={{ color: "#38BDF8" }}>IT Rules 2021 r.3(1)(b)</span>
                        </div>
                      </div>
                      <div style={{ fontSize: "0.68rem", color: "#64748B", lineHeight: 1.3 }}>
                        Mandatory transparency label applied per Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules 2021.
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Post Action Icons */}
              <div style={{ padding: "12px 16px 8px 16px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                    {/* Heart Button */}
                    <button
                      onClick={() => toggleLike(post.id)}
                      style={{ background: "none", border: "none", cursor: "pointer", padding: 0 }}
                    >
                      <span style={{ fontSize: "1.5rem", color: post.liked_by_me ? "#EF4444" : "#FFF" }}>
                        {post.liked_by_me ? "❤️" : "🤍"}
                      </span>
                    </button>

                    {/* Comment Button */}
                    <button
                      onClick={() => loadComments(post.id)}
                      style={{ background: "none", border: "none", cursor: "pointer", padding: 0 }}
                    >
                      <span style={{ fontSize: "1.4rem" }}>💬</span>
                    </button>

                    {/* Share Plane */}
                    <span style={{ fontSize: "1.3rem", cursor: "pointer" }}>✈️</span>
                  </div>

                  {/* Bookmark Ribbon */}
                  <span style={{ fontSize: "1.3rem", cursor: "pointer" }}>🔖</span>
                </div>

                {/* Likes Counter */}
                <div style={{ fontWeight: 800, fontSize: "0.88rem", color: "#FFF", marginBottom: "6px" }}>
                  {post.likes_count.toLocaleString()} likes
                </div>

                {/* Caption */}
                <div style={{ fontSize: "0.88rem", color: "#E2E8F0", lineHeight: 1.4 }}>
                  <strong style={{ color: "#FFF", marginRight: "6px" }}>@{post.username}</strong>
                  {post.caption}
                </div>

                {/* Comments Toggle & List */}
                <div style={{ marginTop: "8px" }}>
                  {post.comments_count > 0 && activeCommentPost !== post.id && (
                    <button
                      onClick={() => loadComments(post.id)}
                      style={{ background: "none", border: "none", color: "#71717A", fontSize: "0.82rem", cursor: "pointer", padding: 0 }}
                    >
                      View all {post.comments_count} comments
                    </button>
                  )}

                  {activeCommentPost === post.id && (
                    <div style={{ marginTop: "10px", display: "flex", flexDirection: "column", gap: "6px" }}>
                      {(commentsMap[post.id] || []).map((c) => (
                        <div key={c.id} style={{ fontSize: "0.82rem", color: "#CBD5E1" }}>
                          <strong style={{ color: "#FFF", marginRight: "6px" }}>@{c.username}</strong>
                          {c.content}
                        </div>
                      ))}

                      {/* Add Comment Input */}
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "8px" }}>
                        <input
                          type="text"
                          placeholder="Add a comment..."
                          value={commentInput}
                          onChange={(e) => setCommentInput(e.target.value)}
                          onKeyDown={(e) => e.key === "Enter" && submitComment(post.id)}
                          style={{
                            flex: 1,
                            backgroundColor: "rgba(255, 255, 255, 0.05)",
                            border: "1px solid rgba(255, 255, 255, 0.1)",
                            borderRadius: "20px",
                            padding: "6px 14px",
                            color: "#FFF",
                            fontSize: "0.82rem",
                            outline: "none",
                          }}
                        />
                        <button
                          onClick={() => submitComment(post.id)}
                          disabled={!commentInput.trim()}
                          style={{
                            background: "none",
                            border: "none",
                            color: commentInput.trim() ? "#0095F6" : "#64748B",
                            fontWeight: 700,
                            fontSize: "0.82rem",
                            cursor: commentInput.trim() ? "pointer" : "default",
                          }}
                        >
                          Post
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* Timestamp */}
                <div style={{ fontSize: "0.68rem", color: "#71717A", textTransform: "uppercase", marginTop: "8px" }}>
                  {new Date(post.created_at).toLocaleDateString([], { month: "short", day: "numeric" })}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
};

// ============================================================================
// 2. REAL WHATSAPP CLIENT (AUTHENTIC WHATSAPP WEB UI)
// ============================================================================
const RealWhatsAppClient: React.FC<{
  currentUser: SocialUser | null;
  users: SocialUser[];
  onBlocked: (res: any) => void;
  showNotify: (text: string, type: "success" | "error" | "info") => void;
}> = ({ currentUser, users, onBlocked, showNotify }) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [messageText, setMessageText] = useState<string>("");
  const [, setIsSending] = useState<boolean>(false);
  const [otpModalOpen, setOtpModalOpen] = useState<boolean>(false);
  const [phoneInput, setPhoneInput] = useState<string>("+91 98765 43210");
  const [otpInput, setOtpInput] = useState<string>("");
  const [issuedOtp, setIssuedOtp] = useState<string | null>(null);
  const [newGroupModal, setNewGroupModal] = useState<boolean>(false);
  const [groupNameInput, setGroupNameInput] = useState<string>("");
  const [selectedGroupMembers, setSelectedGroupMembers] = useState<string[]>([]);
  const [smsBanner, setSmsBanner] = useState<{ phone: string; code: string; time: string } | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    fetchConversations();
  }, [currentUser]);

  useEffect(() => {
    if (activeConvId) {
      fetchMessages(activeConvId);
    }
  }, [activeConvId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const fetchConversations = async () => {
    if (!currentUser) return;
    try {
      const res = await fetch(withBase(`/api/v1/social/whatsapp/conversations?user_id=${currentUser.id}`));
      if (res.ok) {
        const data = await res.json();
        setConversations(data);
        if (data.length > 0 && !activeConvId) {
          setActiveConvId(data[0].id);
        }
      }
    } catch (e) {
      console.error("Failed to fetch WhatsApp conversations", e);
    }
  };

  const fetchMessages = async (convId: string) => {
    if (!currentUser) return;
    try {
      const res = await fetch(withBase(`/api/v1/social/whatsapp/conversations/${convId}/messages?user_id=${currentUser.id}`));
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
      }
    } catch (e) {
      console.error("Failed to fetch messages", e);
    }
  };

  const handleSendMessage = async () => {
    if (!messageText.trim() || !activeConvId || !currentUser) return;
    setIsSending(true);
    try {
      const res = await fetch(withBase(`/api/v1/social/whatsapp/conversations/${activeConvId}/messages`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sender_id: currentUser.id,
          content: messageText,
        }),
      });

      if (res.ok) {
        setMessageText("");
        fetchMessages(activeConvId);
        fetchConversations();
      } else {
        const body = await res.json();
        showNotify(body.detail || "Failed to send message", "error");
      }
    } catch (e) {
      showNotify("Error sending message", "error");
    } finally {
      setIsSending(false);
    }
  };

  const handleSendMedia = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !e.target.files[0] || !activeConvId || !currentUser) return;
    const file = e.target.files[0];
    const formData = new FormData();
    formData.append("file", file);
    formData.append("sender_id", currentUser.id);
    formData.append("text", "Attached media file");

    try {
      const res = await fetch(withBase(`/api/v1/social/whatsapp/conversations/${activeConvId}/messages`), {
        method: "POST",
        body: formData,
      });

      const body = await res.json();
      if (res.status === 403 || body.blocked) {
        onBlocked(body);
        showNotify("WhatsApp Pre-Send Quarantine: Synthetic media intercepted.", "error");
      } else if (res.ok) {
        showNotify("Media delivered securely.", "success");
        fetchMessages(activeConvId);
        fetchConversations();
      } else {
        showNotify(body.detail || "Upload rejected", "error");
      }
    } catch (e) {
      showNotify("Failed to upload media", "error");
    }
  };

  const handleRequestOtp = async () => {
    try {
      const res = await fetch(withBase("/api/v1/social/otp/request"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone_number: phoneInput }),
      });
      if (res.ok) {
        const data = await res.json();
        setIssuedOtp(data.demo_otp_code);
        setOtpInput(data.demo_otp_code); // auto-fill for frictionless UX
        const nowTime = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        setSmsBanner({ phone: phoneInput, code: data.demo_otp_code, time: nowTime });
        setTimeout(() => setSmsBanner(null), 10000);
        showNotify(`Demo OTP Generated: ${data.demo_otp_code}`, "info");
      }
    } catch (e) {
      showNotify("Failed to request OTP", "error");
    }
  };

  const handleVerifyOtp = async () => {
    try {
      const res = await fetch(withBase("/api/v1/social/otp/verify"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone_number: phoneInput, otp_code: otpInput }),
      });
      const data = await res.json();
      if (data.success) {
        showNotify("WhatsApp verified and session issued!", "success");
        setOtpModalOpen(false);
      } else {
        showNotify(data.error || "Invalid OTP code", "error");
      }
    } catch (e) {
      showNotify("Verification error", "error");
    }
  };

  const handleCreateGroup = async () => {
    if (!groupNameInput.trim() || !currentUser) return;
    try {
      const res = await fetch(withBase("/api/v1/social/whatsapp/groups"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          group_name: groupNameInput,
          creator_id: currentUser.id,
          member_ids: [currentUser.id, ...selectedGroupMembers],
        }),
      });
      if (res.ok) {
        showNotify(`Group '${groupNameInput}' created!`, "success");
        setNewGroupModal(false);
        setGroupNameInput("");
        fetchConversations();
      }
    } catch (e) {
      showNotify("Failed to create group", "error");
    }
  };

  const activeConv = conversations.find((c) => c.id === activeConvId);

  return (
    <div style={{
      maxWidth: "1400px",
      margin: "0 auto",
      height: "82vh",
      backgroundColor: "#111B21",
      borderRadius: "16px",
      border: "1px solid rgba(255, 255, 255, 0.08)",
      overflow: "hidden",
      display: "flex",
      boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.6)",
      position: "relative",
    }}>
      {/* Simulated SMS Push Notification Banner */}
      {smsBanner && (
        <div style={{
          position: "absolute",
          top: "16px",
          right: "24px",
          zIndex: 800,
          backgroundColor: "#1E293B",
          border: "1px solid #38BDF8",
          borderRadius: "12px",
          padding: "12px 16px",
          boxShadow: "0 10px 30px rgba(0, 0, 0, 0.6)",
          maxWidth: "380px",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#38BDF8" }}>
              💬 MESSAGES • {smsBanner.time}
            </span>
            <button
              onClick={() => setSmsBanner(null)}
              style={{ background: "none", border: "none", color: "#94A3B8", cursor: "pointer", fontSize: "0.8rem" }}
            >
              ✕
            </button>
          </div>
          <div style={{ fontSize: "0.82rem", color: "#F8FAFC", marginBottom: "8px" }}>
            <strong>Secura Auth:</strong> Your WhatsApp verification code is <strong>{smsBanner.code}</strong>. Valid for 5 minutes.
          </div>
          <button
            onClick={() => {
              setOtpInput(smsBanner.code);
              setOtpModalOpen(true);
              setSmsBanner(null);
            }}
            style={{
              backgroundColor: "#00A884",
              border: "none",
              color: "#FFF",
              padding: "4px 12px",
              borderRadius: "6px",
              fontSize: "0.75rem",
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            ⚡ Open & Auto-fill Code
          </button>
        </div>
      )}
      {/* ==================================================================== */}
      {/* LEFT COLUMN: CHAT LIST                                               */}
      {/* ==================================================================== */}
      <div style={{
        width: "400px",
        backgroundColor: "#111B21",
        borderRight: "1px solid #222E35",
        display: "flex",
        flexDirection: "column",
        flexShrink: 0,
      }}>
        {/* Left Header */}
        <div style={{
          backgroundColor: "#202C33",
          padding: "10px 16px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          height: "60px",
          boxSizing: "border-box",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <img
              src={currentUser?.avatar_url || "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150"}
              alt="My Avatar"
              style={{ width: "40px", height: "40px", borderRadius: "50%", objectFit: "cover" }}
            />
            <span style={{ fontWeight: 700, fontSize: "0.92rem", color: "#E9EDEF" }}>
              {currentUser?.display_name || "WhatsApp"}
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "#AEBAC1" }}>
            <button
              onClick={() => setOtpModalOpen(true)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "5px",
                backgroundColor: "rgba(37, 211, 102, 0.15)",
                border: "1px solid #25D366",
                color: "#25D366",
                padding: "4px 10px",
                borderRadius: "16px",
                fontWeight: 700,
                fontSize: "0.75rem",
                cursor: "pointer",
              }}
              title="Simulate SMS OTP Phone Verification"
            >
              <span>📱</span> Verify Phone (OTP)
            </button>
            <button
              onClick={() => setNewGroupModal(true)}
              title="Create New Group"
              style={{ background: "none", border: "none", color: "#AEBAC1", cursor: "pointer", fontSize: "1.1rem" }}
            >
              👥
            </button>
          </div>
        </div>

        {/* Search Bar */}
        <div style={{ padding: "8px 12px", borderBottom: "1px solid #222E35" }}>
          <div style={{
            backgroundColor: "#202C33",
            borderRadius: "8px",
            display: "flex",
            alignItems: "center",
            padding: "6px 12px",
            gap: "10px",
          }}>
            <span style={{ color: "#8696A0", fontSize: "0.9rem" }}>🔍</span>
            <input
              type="text"
              placeholder="Search or start new chat"
              style={{
                background: "transparent",
                border: "none",
                color: "#D1D7DB",
                fontSize: "0.85rem",
                width: "100%",
                outline: "none",
              }}
            />
          </div>
        </div>

        {/* Chat Items List */}
        <div style={{ flex: 1, overflowY: "auto" }}>
          {conversations.map((conv) => {
            const isSelected = conv.id === activeConvId;
            const isBot = conv.name.includes("Secura") || conv.name.includes("Bot") || conv.id.startsWith("c_bot_");
            return (
              <div
                key={conv.id}
                onClick={() => setActiveConvId(conv.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  padding: "12px 16px",
                  gap: "14px",
                  cursor: "pointer",
                  backgroundColor: isSelected ? "#2A3942" : isBot ? "rgba(37, 211, 102, 0.05)" : "transparent",
                  borderBottom: "1px solid #202C33",
                  borderLeft: isBot ? "3px solid #00A884" : "3px solid transparent",
                  transition: "background-color 0.15s ease",
                }}
                onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.backgroundColor = "#202C33"; }}
                onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.backgroundColor = isBot ? "rgba(37, 211, 102, 0.05)" : "transparent"; }}
              >
                <div style={{ position: "relative" }}>
                  <img
                    src={conv.avatar_url || "https://images.unsplash.com/photo-1557804506-669a67965ba0?w=150"}
                    alt={conv.name}
                    style={{
                      width: "48px",
                      height: "48px",
                      borderRadius: "50%",
                      objectFit: "cover",
                      border: isBot ? "2px solid #00A884" : "none",
                    }}
                  />
                  {isBot && (
                    <span style={{
                      position: "absolute",
                      bottom: "-2px",
                      right: "-2px",
                      backgroundColor: "#00A884",
                      borderRadius: "50%",
                      width: "16px",
                      height: "16px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "10px",
                    }}>
                      🛡️
                    </span>
                  )}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <span style={{ fontWeight: 600, fontSize: "0.92rem", color: "#E9EDEF" }}>{conv.name}</span>
                      {isBot && (
                        <span style={{
                          fontSize: "0.65rem",
                          backgroundColor: "rgba(0, 168, 132, 0.2)",
                          color: "#00A884",
                          padding: "1px 5px",
                          borderRadius: "4px",
                          fontWeight: 700,
                        }}>
                          OFFICIAL
                        </span>
                      )}
                    </div>
                    <span style={{ fontSize: "0.72rem", color: "#8696A0" }}>11:42 AM</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "4px", marginTop: "2px" }}>
                    <span style={{ color: "#53BDEB", fontSize: "0.82rem" }}>✓✓</span>
                    <span style={{ fontSize: "0.82rem", color: isBot ? "#34D399" : "#8696A0", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {conv.last_message || (isBot ? "Ready for media inspection & statutory Q&A" : "Tap to chat")}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ==================================================================== */}
      {/* RIGHT COLUMN: ACTIVE CHAT CONVERSATION                               */}
      {/* ==================================================================== */}
      <div style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        backgroundColor: "#0B141A",
        position: "relative",
      }}>
        {activeConv ? (
          <>
            {/* Chat Header */}
            <div style={{
              backgroundColor: "#202C33",
              padding: "10px 16px",
              height: "60px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              borderBottom: "1px solid #222E35",
              boxSizing: "border-box",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div style={{ position: "relative" }}>
                  <img
                    src={activeConv.avatar_url}
                    alt={activeConv.name}
                    style={{
                      width: "40px",
                      height: "40px",
                      borderRadius: "50%",
                      objectFit: "cover",
                      border: (activeConv.name.includes("Secura") || activeConv.name.includes("Bot") || activeConv.id.startsWith("c_bot_")) ? "2px solid #00A884" : "none",
                    }}
                  />
                  {(activeConv.name.includes("Secura") || activeConv.name.includes("Bot") || activeConv.id.startsWith("c_bot_")) && (
                    <span style={{
                      position: "absolute",
                      bottom: "-2px",
                      right: "-2px",
                      backgroundColor: "#00A884",
                      borderRadius: "50%",
                      width: "14px",
                      height: "14px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "9px",
                    }}>
                      🛡️
                    </span>
                  )}
                </div>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ fontWeight: 600, fontSize: "0.95rem", color: "#E9EDEF" }}>{activeConv.name}</span>
                    {(activeConv.name.includes("Secura") || activeConv.name.includes("Bot") || activeConv.id.startsWith("c_bot_")) && (
                      <span style={{
                        fontSize: "0.68rem",
                        backgroundColor: "rgba(0, 168, 132, 0.2)",
                        color: "#00A884",
                        padding: "2px 6px",
                        borderRadius: "4px",
                        fontWeight: 700,
                      }}>
                        VERIFIED FORENSIC ASSISTANT
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: "0.74rem", color: "#00A884" }}>
                    {(activeConv.name.includes("Secura") || activeConv.name.includes("Bot") || activeConv.id.startsWith("c_bot_"))
                      ? "● Online • Automated Media Forensics & IT Rules 2021 RAG"
                      : "online • end-to-end encrypted"}
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "18px", color: "#AEBAC1" }}>
                <span style={{ cursor: "pointer" }}>📹</span>
                <span style={{ cursor: "pointer" }}>📞</span>
                <span style={{ cursor: "pointer" }}>⋮</span>
              </div>
            </div>

            {/* Messages Scroll Area with WhatsApp Wallpaper Tone */}
            <div style={{
              flex: 1,
              padding: "20px 24px",
              overflowY: "auto",
              display: "flex",
              flexDirection: "column",
              gap: "8px",
              backgroundImage: "radial-gradient(rgba(255,255,255,0.03) 1px, transparent 1px)",
              backgroundSize: "20px 20px",
            }}>
              {/* Encryption Banner */}
              <div style={{
                alignSelf: "center",
                backgroundColor: "#182229",
                color: "#FFD279",
                padding: "6px 14px",
                borderRadius: "8px",
                fontSize: "0.75rem",
                textAlign: "center",
                marginBottom: "12px",
                maxWidth: "80%",
                boxShadow: "0 1px 2px rgba(0, 0, 0, 0.3)",
              }}>
                🔒 Messages and calls are end-to-end encrypted. Pre-send media evaluated by Secura Shield.
              </div>

              {messages.map((m) => {
                const isMine = m.sender_id === currentUser?.id;
                return (
                  <div
                    key={m.id}
                    style={{
                      alignSelf: isMine ? "flex-end" : "flex-start",
                      maxWidth: "65%",
                      backgroundColor: isMine ? "#005C4B" : "#202C33",
                      color: "#E9EDEF",
                      padding: "8px 12px 6px 12px",
                      borderRadius: isMine ? "8px 0px 8px 8px" : "0px 8px 8px 8px",
                      position: "relative",
                      boxShadow: "0 1px 2px rgba(0, 0, 0, 0.3)",
                      fontSize: "0.9rem",
                    }}
                  >
                    {!isMine && (
                      <div style={{ fontSize: "0.75rem", color: "#53BDEB", fontWeight: 700, marginBottom: "2px" }}>
                        {m.sender_name}
                      </div>
                    )}

                    {m.media_url && (
                      <div style={{ marginBottom: "6px", borderRadius: "6px", overflow: "hidden" }}>
                        <img src={m.media_url} alt="Attached" style={{ width: "100%", maxHeight: "250px", objectFit: "cover" }} />
                      </div>
                    )}

                    <div>{m.text}</div>

                    <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: "4px", marginTop: "2px" }}>
                      <span style={{ fontSize: "0.68rem", color: "rgba(255, 255, 255, 0.6)" }}>
                        {new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                      {isMine && <span style={{ color: "#53BDEB", fontSize: "0.75rem" }}>✓✓</span>}
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            {/* Quick Prompt Chips for Secura AI Forensic Bot */}
            {(activeConv.name.includes("Secura") || activeConv.name.includes("Bot") || activeConv.id.startsWith("c_bot_")) && (
              <div style={{
                backgroundColor: "#182229",
                padding: "8px 16px",
                display: "flex",
                gap: "8px",
                overflowX: "auto",
                borderTop: "1px solid #222E35",
                scrollbarWidth: "none",
              }}>
                <span style={{ fontSize: "0.75rem", color: "#8696A0", alignSelf: "center", fontWeight: 700, whiteSpace: "nowrap" }}>
                  Quick Queries:
                </span>
                {[
                  { label: "📸 Attach Media to Inspect", action: () => fileInputRef.current?.click() },
                  { label: "⚖️ IT Rules 2021 Rule 3(1)(b)", action: () => { setMessageText("What does Rule 3(1)(b) of IT Rules 2021 require intermediaries to do regarding synthetic content?"); } },
                  { label: "📜 DPDP Act Deepfake Penalties", action: () => { setMessageText("What statutory liabilities exist under DPDP Act 2023 and BNS 2023 for impersonation via deepfakes?"); } },
                  { label: "🛡️ Secura Forensic Pipeline", action: () => { setMessageText("How does Secura AI detect deepfakes across CLIP-ViT, Swin, ELA, and metadata?"); } },
                ].map((chip, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={chip.action}
                    style={{
                      whiteSpace: "nowrap",
                      backgroundColor: "rgba(0, 168, 132, 0.15)",
                      border: "1px solid #00A884",
                      color: "#E9EDEF",
                      padding: "4px 10px",
                      borderRadius: "14px",
                      fontSize: "0.74rem",
                      cursor: "pointer",
                      fontWeight: 600,
                      transition: "all 0.15s ease",
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "rgba(0, 168, 132, 0.3)")}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "rgba(0, 168, 132, 0.15)")}
                  >
                    {chip.label}
                  </button>
                ))}
              </div>
            )}

            {/* Chat Input Bar */}
            <div style={{
              backgroundColor: "#202C33",
              padding: "10px 16px",
              display: "flex",
              alignItems: "center",
              gap: "12px",
            }}>
              <span style={{ fontSize: "1.2rem", color: "#8696A0", cursor: "pointer" }}>😊</span>

              {/* Attachment Button */}
              <button
                onClick={() => fileInputRef.current?.click()}
                title="Attach Media (Pre-Send Inspected)"
                style={{ background: "none", border: "none", color: "#8696A0", fontSize: "1.2rem", cursor: "pointer" }}
              >
                📎
              </button>
              <input ref={fileInputRef} type="file" accept="image/*,video/*" onChange={handleSendMedia} style={{ display: "none" }} />

              {/* Input Text Box */}
              <input
                type="text"
                placeholder="Type a message"
                value={messageText}
                onChange={(e) => setMessageText(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
                style={{
                  flex: 1,
                  backgroundColor: "#2A3942",
                  border: "none",
                  borderRadius: "8px",
                  padding: "10px 16px",
                  color: "#D1D7DB",
                  fontSize: "0.92rem",
                  outline: "none",
                }}
              />

              {/* Send or Voice Note Button */}
              <button
                onClick={handleSendMessage}
                style={{
                  background: "none",
                  border: "none",
                  color: messageText.trim() ? "#00A884" : "#8696A0",
                  fontSize: "1.2rem",
                  cursor: "pointer",
                }}
              >
                {messageText.trim() ? "➤" : "🎙️"}
              </button>
            </div>
          </>
        ) : (
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#8696A0" }}>
            Select a conversation to start messaging
          </div>
        )}
      </div>

      {/* ==================================================================== */}
      {/* WHATSAPP SAFE OTP MODAL                                              */}
      {/* ==================================================================== */}
      {otpModalOpen && (
        <div style={{
          position: "fixed",
          inset: 0,
          zIndex: 600,
          backgroundColor: "rgba(0, 0, 0, 0.8)",
          backdropFilter: "blur(8px)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "16px",
        }}>
          <div style={{
            maxWidth: "420px",
            width: "100%",
            backgroundColor: "#222E35",
            borderRadius: "16px",
            padding: "24px",
            color: "#FFF",
            boxShadow: "0 20px 40px rgba(0, 0, 0, 0.5)",
          }}>
            <div style={{ textAlign: "center", marginBottom: "20px" }}>
              <div style={{ fontSize: "2.5rem", marginBottom: "8px" }}>💬</div>
              <h3 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 700 }}>Verify WhatsApp Mobile</h3>
              <p style={{ margin: "4px 0 0 0", color: "#8696A0", fontSize: "0.82rem" }}>
                Safe ephemeral authentication with 5-minute expiry & rate-limiting
              </p>
            </div>

            <div style={{ marginBottom: "16px" }}>
              <label style={{ display: "block", fontSize: "0.78rem", color: "#8696A0", marginBottom: "6px" }}>
                Phone Number (+91)
              </label>
              <input
                type="text"
                value={phoneInput}
                onChange={(e) => setPhoneInput(e.target.value)}
                style={{
                  width: "100%",
                  backgroundColor: "#111B21",
                  border: "1px solid #2A3942",
                  borderRadius: "8px",
                  padding: "10px",
                  color: "#FFF",
                  boxSizing: "border-box",
                }}
              />
              <button
                onClick={handleRequestOtp}
                style={{
                  marginTop: "8px",
                  width: "100%",
                  backgroundColor: "rgba(37, 211, 102, 0.15)",
                  border: "1px solid #25D366",
                  color: "#25D366",
                  padding: "8px",
                  borderRadius: "8px",
                  fontWeight: 700,
                  fontSize: "0.82rem",
                  cursor: "pointer",
                }}
              >
                Request 6-Digit OTP Code
              </button>
            </div>

            {issuedOtp && (
              <div style={{ marginBottom: "16px" }}>
                <div style={{
                  backgroundColor: "rgba(37, 211, 102, 0.1)",
                  padding: "8px 12px",
                  borderRadius: "6px",
                  fontSize: "0.82rem",
                  color: "#25D366",
                  marginBottom: "8px",
                }}>
                  ✅ Demo OTP: <strong>{issuedOtp}</strong>
                </div>
                <label style={{ display: "block", fontSize: "0.78rem", color: "#8696A0", marginBottom: "6px" }}>
                  Enter Verification Code
                </label>
                <input
                  type="text"
                  maxLength={6}
                  value={otpInput}
                  onChange={(e) => setOtpInput(e.target.value)}
                  style={{
                    width: "100%",
                    backgroundColor: "#111B21",
                    border: "1px solid #25D366",
                    borderRadius: "8px",
                    padding: "10px",
                    color: "#FFF",
                    textAlign: "center",
                    letterSpacing: "0.4em",
                    fontSize: "1.2rem",
                    fontWeight: 700,
                    boxSizing: "border-box",
                  }}
                />
              </div>
            )}

            <div style={{ display: "flex", gap: "10px", marginTop: "20px" }}>
              <button
                onClick={() => setOtpModalOpen(false)}
                style={{ flex: 1, backgroundColor: "#2A3942", border: "none", color: "#FFF", padding: "10px", borderRadius: "8px", cursor: "pointer" }}
              >
                Cancel
              </button>
              <button
                onClick={handleVerifyOtp}
                style={{ flex: 1, backgroundColor: "#00A884", border: "none", color: "#FFF", padding: "10px", borderRadius: "8px", fontWeight: 700, cursor: "pointer" }}
              >
                Verify & Login
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* NEW GROUP CREATION MODAL                                             */}
      {/* ==================================================================== */}
      {newGroupModal && (
        <div style={{
          position: "fixed",
          inset: 0,
          zIndex: 600,
          backgroundColor: "rgba(0, 0, 0, 0.8)",
          backdropFilter: "blur(8px)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "16px",
        }}>
          <div style={{
            maxWidth: "460px",
            width: "100%",
            backgroundColor: "#222E35",
            borderRadius: "16px",
            padding: "24px",
            color: "#FFF",
          }}>
            <h3 style={{ margin: "0 0 16px 0", fontSize: "1.2rem", fontWeight: 700 }}>New WhatsApp Group</h3>
            <input
              type="text"
              placeholder="Group Subject"
              value={groupNameInput}
              onChange={(e) => setGroupNameInput(e.target.value)}
              style={{
                width: "100%",
                backgroundColor: "#111B21",
                border: "1px solid #2A3942",
                borderRadius: "8px",
                padding: "10px",
                color: "#FFF",
                boxSizing: "border-box",
                marginBottom: "16px",
              }}
            />

            <div style={{ fontSize: "0.82rem", color: "#8696A0", marginBottom: "8px" }}>Select Participants:</div>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px", maxHeight: "180px", overflowY: "auto", marginBottom: "20px" }}>
              {users.filter(u => u.id !== currentUser?.id).map((u) => {
                const isSelected = selectedGroupMembers.includes(u.id);
                return (
                  <div
                    key={u.id}
                    onClick={() => {
                      if (isSelected) {
                        setSelectedGroupMembers(selectedGroupMembers.filter(x => x !== u.id));
                      } else {
                        setSelectedGroupMembers([...selectedGroupMembers, u.id]);
                      }
                    }}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "10px",
                      padding: "8px",
                      borderRadius: "6px",
                      backgroundColor: isSelected ? "rgba(0, 168, 132, 0.2)" : "#182229",
                      cursor: "pointer",
                    }}
                  >
                    <input type="checkbox" checked={isSelected} readOnly />
                    <img src={u.avatar_url} alt={u.username} style={{ width: "30px", height: "30px", borderRadius: "50%" }} />
                    <span style={{ fontSize: "0.85rem" }}>{u.display_name} (@{u.username})</span>
                  </div>
                );
              })}
            </div>

            <div style={{ display: "flex", gap: "10px" }}>
              <button
                onClick={() => setNewGroupModal(false)}
                style={{ flex: 1, backgroundColor: "#2A3942", border: "none", color: "#FFF", padding: "10px", borderRadius: "8px", cursor: "pointer" }}
              >
                Cancel
              </button>
              <button
                onClick={handleCreateGroup}
                style={{ flex: 1, backgroundColor: "#00A884", border: "none", color: "#FFF", padding: "10px", borderRadius: "8px", fontWeight: 700, cursor: "pointer" }}
              >
                Create Group
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// 3. REAL TELEGRAM CLIENT (TELEGRAM WEBZ / DESKTOP THEMED)
// ============================================================================
const RealTelegramClient: React.FC<{
  currentUser: SocialUser | null;
  onBlocked: (res: any) => void;
  showNotify: (text: string, type: "success" | "error" | "info") => void;
}> = ({ currentUser, onBlocked, showNotify }) => {
  const [channels, setChannels] = useState<TelegramChannel[]>([]);
  const [activeChannelId, setActiveChannelId] = useState<string | null>(null);
  const [posts, setPosts] = useState<TelegramPost[]>([]);
  const [broadcastText, setBroadcastText] = useState<string>("");
  const [broadcastFile, setBroadcastFile] = useState<File | null>(null);
  const [broadcastPreview, setBroadcastPreview] = useState<string | null>(null);
  const [isBroadcasting, setIsBroadcasting] = useState<boolean>(false);
  const [isPinnedBroadcast, setIsPinnedBroadcast] = useState<boolean>(false);
  const broadcastFileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    fetchChannels();
  }, [currentUser]);

  useEffect(() => {
    if (activeChannelId) {
      fetchChannelPosts(activeChannelId);
    }
  }, [activeChannelId]);

  const fetchChannels = async () => {
    if (!currentUser) return;
    try {
      const res = await fetch(withBase(`/api/v1/social/telegram/channels?user_id=${currentUser.id}`));
      if (res.ok) {
        const data = await res.json();
        setChannels(data);
        if (data.length > 0 && !activeChannelId) {
          setActiveChannelId(data[0].id);
        }
      }
    } catch (e) {
      console.error("Failed to fetch Telegram channels", e);
    }
  };

  const fetchChannelPosts = async (chId: string) => {
    if (!currentUser) return;
    try {
      const res = await fetch(withBase(`/api/v1/social/telegram/channels/${chId}/posts?user_id=${currentUser.id}`));
      if (res.ok) {
        const data = await res.json();
        setPosts(data);
      }
    } catch (e) {
      console.error("Failed to fetch channel posts", e);
    }
  };

  const toggleJoin = async (chId: string) => {
    if (!currentUser) return;
    try {
      const res = await fetch(withBase(`/api/v1/social/telegram/channels/${chId}/join`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: currentUser.id }),
      });
      if (res.ok) {
        const data = await res.json();
        setChannels((prev) =>
          prev.map((c) =>
            c.id === chId
              ? {
                  ...c,
                  is_member: data.is_member,
                  subscribers_count: data.subscribers_count,
                }
              : c
          )
        );
        showNotify(data.is_member ? "Joined Telegram Channel!" : "Left channel.", "info");
      }
    } catch (e) {
      showNotify("Failed to join channel", "error");
    }
  };

  const reactToPost = async (postId: string, emoji: string) => {
    if (!currentUser || !activeChannelId) return;
    try {
      const res = await fetch(withBase(`/api/v1/social/telegram/posts/${postId}/react`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: currentUser.id, emoji }),
      });
      if (res.ok) {
        fetchChannelPosts(activeChannelId);
      }
    } catch (e) {
      console.error("Reaction failed", e);
    }
  };

  const togglePin = async (postId: string) => {
    if (!currentUser || !activeChannelId) return;
    try {
      const res = await fetch(withBase(`/api/v1/social/telegram/posts/${postId}/pin`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channel_id: activeChannelId }),
      });
      if (res.ok) {
        fetchChannelPosts(activeChannelId);
      }
    } catch (e) {
      console.error("Pin failed", e);
    }
  };

  const handleBroadcastFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setBroadcastFile(file);
      setBroadcastPreview(URL.createObjectURL(file));
    }
  };

  const handleBroadcast = async () => {
    if (!activeChannelId || !currentUser) return;
    if (!broadcastText.trim() && !broadcastFile) {
      showNotify("Please enter a broadcast message or attach media.", "error");
      return;
    }

    setIsBroadcasting(true);
    const formData = new FormData();
    formData.append("channel_id", activeChannelId);
    formData.append("sender_id", currentUser.id);
    if (broadcastText.trim()) formData.append("text", broadcastText);
    formData.append("is_pinned", isPinnedBroadcast ? "true" : "false");
    if (broadcastFile) formData.append("file", broadcastFile);

    try {
      const res = await fetch(withBase(`/api/v1/social/telegram/channels/${activeChannelId}/posts`), {
        method: "POST",
        body: formData,
      });

      const body = await res.json();
      if (res.status === 403 || body.blocked) {
        onBlocked(body);
        showNotify("Pre-Broadcast Quarantine: AI-generated media intercepted. Zero deliveries to subscribers.", "error");
      } else if (res.ok) {
        showNotify("Broadcast published to channel subscribers!", "success");
        setBroadcastText("");
        setBroadcastFile(null);
        setBroadcastPreview(null);
        setIsPinnedBroadcast(false);
        fetchChannelPosts(activeChannelId);
      } else {
        showNotify(body.detail || "Broadcast failed", "error");
      }
    } catch (e) {
      showNotify("Network error during broadcast", "error");
    } finally {
      setIsBroadcasting(false);
    }
  };

  const activeChannel = channels.find((c) => c.id === activeChannelId);
  const pinnedPost = posts.find((p) => p.is_pinned);

  return (
    <div style={{
      maxWidth: "1400px",
      margin: "0 auto",
      height: "82vh",
      backgroundColor: "#17212B",
      borderRadius: "16px",
      border: "1px solid rgba(255, 255, 255, 0.08)",
      overflow: "hidden",
      display: "flex",
      boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.6)",
    }}>
      {/* Left Sidebar: Channels List */}
      <div style={{
        width: "380px",
        backgroundColor: "#0E1621",
        borderRight: "1px solid #101921",
        display: "flex",
        flexDirection: "column",
        flexShrink: 0,
      }}>
        {/* Header */}
        <div style={{ padding: "14px 18px", borderBottom: "1px solid #101921", display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "1.2rem", color: "#229ED9" }}>✈️</span>
          <span style={{ fontWeight: 800, fontSize: "1.05rem", color: "#FFF" }}>Telegram Public Channels</span>
        </div>

        {/* Channel Items */}
        <div style={{ flex: 1, overflowY: "auto" }}>
          {channels.map((ch) => {
            const isSelected = ch.id === activeChannelId;
            return (
              <div
                key={ch.id}
                onClick={() => setActiveChannelId(ch.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  padding: "12px 16px",
                  gap: "12px",
                  cursor: "pointer",
                  backgroundColor: isSelected ? "#242F3D" : "transparent",
                  borderBottom: "1px solid rgba(255, 255, 255, 0.04)",
                }}
              >
                <img src={ch.avatar_url} alt={ch.title} style={{ width: "46px", height: "46px", borderRadius: "50%", objectFit: "cover" }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ fontWeight: 700, fontSize: "0.92rem", color: "#FFF" }}>{ch.title}</span>
                    {ch.is_verified && <span style={{ color: "#229ED9", fontSize: "0.85rem" }}>✓</span>}
                  </div>
                  <div style={{ fontSize: "0.76rem", color: "#7F91A4", marginTop: "2px" }}>
                    {ch.subscribers_count.toLocaleString()} subscribers
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Right Area: Broadcast Posts Stream */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", backgroundColor: "#0E1621" }}>
        {activeChannel ? (
          <>
            {/* Channel Top Header */}
            <div style={{
              backgroundColor: "#17212B",
              padding: "12px 20px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              borderBottom: "1px solid #101921",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <img src={activeChannel.avatar_url} alt={activeChannel.title} style={{ width: "40px", height: "40px", borderRadius: "50%" }} />
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ fontWeight: 800, fontSize: "1rem", color: "#FFF" }}>{activeChannel.title}</span>
                    {activeChannel.is_verified && <span style={{ color: "#229ED9" }}>✓</span>}
                  </div>
                  <div style={{ fontSize: "0.76rem", color: "#7F91A4" }}>
                    {activeChannel.subscribers_count.toLocaleString()} subscribers • Public Broadcast
                  </div>
                </div>
              </div>

              <button
                onClick={() => toggleJoin(activeChannel.id)}
                style={{
                  backgroundColor: activeChannel.is_member ? "rgba(255, 255, 255, 0.1)" : "#229ED9",
                  color: "#FFF",
                  border: "none",
                  padding: "8px 18px",
                  borderRadius: "20px",
                  fontWeight: 700,
                  fontSize: "0.82rem",
                  cursor: "pointer",
                }}
              >
                {activeChannel.is_member ? "LEAVE CHANNEL" : "JOIN CHANNEL"}
              </button>
            </div>

            {/* Pinned Announcement Banner */}
            {pinnedPost && (
              <div style={{
                backgroundColor: "#182533",
                padding: "8px 18px",
                borderBottom: "1px solid #229ED9",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                fontSize: "0.82rem",
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", overflow: "hidden" }}>
                  <span style={{ color: "#229ED9", fontSize: "1.1rem" }}>📌</span>
                  <span style={{ color: "#229ED9", fontWeight: 700 }}>Pinned:</span>
                  <span style={{ color: "#D1D7DB", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {pinnedPost.content}
                  </span>
                </div>
                <button
                  onClick={() => togglePin(pinnedPost.id)}
                  style={{ background: "none", border: "none", color: "#7F91A4", cursor: "pointer", fontSize: "0.75rem" }}
                >
                  Unpin
                </button>
              </div>
            )}

            {/* Posts Scroll Feed */}
            <div style={{ flex: 1, padding: "20px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "16px" }}>
              {posts.map((post) => (
                <div
                  key={post.id}
                  style={{
                    backgroundColor: "#182533",
                    borderRadius: "14px",
                    padding: "16px",
                    maxWidth: "680px",
                    border: post.is_pinned ? "1px solid #229ED9" : "1px solid rgba(255, 255, 255, 0.05)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                    <span style={{ fontWeight: 700, fontSize: "0.88rem", color: "#229ED9" }}>{activeChannel.title}</span>
                    <button
                      onClick={() => togglePin(post.id)}
                      title={post.is_pinned ? "Unpin message" : "Pin message to top"}
                      style={{ background: "none", border: "none", color: post.is_pinned ? "#229ED9" : "#7F91A4", cursor: "pointer" }}
                    >
                      📌
                    </button>
                  </div>

                  {post.media_url && (
                    <div style={{ marginBottom: "12px", borderRadius: "8px", overflow: "hidden" }}>
                      <img src={post.media_url} alt="Media" style={{ width: "100%", maxHeight: "320px", objectFit: "cover" }} />
                    </div>
                  )}

                  <div style={{ fontSize: "0.92rem", color: "#E9EDEF", lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
                    {post.content}
                  </div>

                  {/* Reaction Pills Dock */}
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "12px", flexWrap: "wrap" }}>
                    {["👍", "🔥", "❤️", "⚡", "⚠️"].map((emoji) => {
                      const count = (post.reactions && post.reactions[emoji]) || 0;
                      return (
                        <button
                          key={emoji}
                          onClick={() => reactToPost(post.id, emoji)}
                          style={{
                            backgroundColor: "rgba(255, 255, 255, 0.08)",
                            border: "1px solid rgba(255, 255, 255, 0.1)",
                            color: "#E2E8F0",
                            padding: "4px 10px",
                            borderRadius: "16px",
                            fontSize: "0.8rem",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            gap: "4px",
                            transition: "transform 0.1s ease",
                          }}
                          onMouseDown={(e) => (e.currentTarget.style.transform = "scale(0.92)")}
                          onMouseUp={(e) => (e.currentTarget.style.transform = "scale(1)")}
                        >
                          <span>{emoji}</span>
                          <span style={{ fontWeight: 700, fontSize: "0.75rem" }}>{count}</span>
                        </button>
                      );
                    })}

                    <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "6px", color: "#7F91A4", fontSize: "0.75rem" }}>
                      <span>👁 {post.views_count.toLocaleString()}</span>
                      <span>• {new Date(post.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Telegram Channel Admin Broadcast Bar */}
            <div style={{
              backgroundColor: "#17212B",
              padding: "10px 16px",
              borderTop: "1px solid #101921",
              display: "flex",
              flexDirection: "column",
              gap: "8px",
            }}>
              {broadcastPreview && (
                <div style={{
                  position: "relative",
                  alignSelf: "flex-start",
                  maxHeight: "90px",
                  borderRadius: "8px",
                  overflow: "hidden",
                  border: "1px solid #229ED9",
                }}>
                  <img src={broadcastPreview} alt="Broadcast attachment" style={{ height: "90px", objectFit: "cover" }} />
                  <button
                    onClick={() => { setBroadcastFile(null); setBroadcastPreview(null); }}
                    style={{
                      position: "absolute",
                      top: "4px",
                      right: "4px",
                      backgroundColor: "rgba(0,0,0,0.6)",
                      color: "#FFF",
                      border: "none",
                      borderRadius: "50%",
                      width: "20px",
                      height: "20px",
                      cursor: "pointer",
                      fontSize: "10px",
                    }}
                  >
                    ✕
                  </button>
                </div>
              )}

              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                {/* Attachment Button */}
                <button
                  type="button"
                  onClick={() => broadcastFileInputRef.current?.click()}
                  title="Attach Photo/Video for Broadcast"
                  style={{ background: "none", border: "none", color: "#7F91A4", fontSize: "1.2rem", cursor: "pointer" }}
                >
                  📎
                </button>
                <input
                  ref={broadcastFileInputRef}
                  type="file"
                  accept="image/*,video/*"
                  onChange={handleBroadcastFileChange}
                  style={{ display: "none" }}
                />

                {/* Broadcast Text Input */}
                <input
                  type="text"
                  placeholder="Broadcast a message to channel subscribers..."
                  value={broadcastText}
                  onChange={(e) => setBroadcastText(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleBroadcast()}
                  style={{
                    flex: 1,
                    backgroundColor: "#242F3D",
                    border: "none",
                    borderRadius: "8px",
                    padding: "10px 14px",
                    color: "#FFF",
                    fontSize: "0.88rem",
                    outline: "none",
                  }}
                />

                {/* Pin Toggle */}
                <button
                  type="button"
                  onClick={() => setIsPinnedBroadcast(!isPinnedBroadcast)}
                  title={isPinnedBroadcast ? "Will be pinned to top" : "Click to pin broadcast"}
                  style={{
                    background: "none",
                    border: "none",
                    color: isPinnedBroadcast ? "#229ED9" : "#7F91A4",
                    fontSize: "1.1rem",
                    cursor: "pointer",
                  }}
                >
                  📌
                </button>

                {/* Broadcast Send Button */}
                <button
                  type="button"
                  onClick={handleBroadcast}
                  disabled={isBroadcasting || (!broadcastText.trim() && !broadcastFile)}
                  style={{
                    backgroundColor: "#229ED9",
                    border: "none",
                    color: "#FFF",
                    padding: "8px 18px",
                    borderRadius: "8px",
                    fontWeight: 700,
                    fontSize: "0.85rem",
                    cursor: isBroadcasting || (!broadcastText.trim() && !broadcastFile) ? "not-allowed" : "pointer",
                    opacity: isBroadcasting || (!broadcastText.trim() && !broadcastFile) ? 0.6 : 1,
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <span>{isBroadcasting ? "Scanning..." : "Broadcast"}</span>
                  <span>🚀</span>
                </button>
              </div>
            </div>
          </>
        ) : (
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#7F91A4" }}>
            Select a channel to view broadcasts
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// 4. REAL MODERATION DASHBOARD & POLICY RAG AUDIT CONSOLE
// ============================================================================
const RealModerationDashboard: React.FC<{
  demoPolicyActive: boolean;
  showNotify: (text: string, type: "success" | "error" | "info") => void;
}> = ({ demoPolicyActive: _demoPolicyActive, showNotify: _showNotify }) => {
  const [stats, setStats] = useState<any>(null);
  const [audits, setAudits] = useState<ModerationAudit[]>([]);
  const [selectedAppFilter, setSelectedAppFilter] = useState<string>("all");
  const [selectedActionFilter, setSelectedActionFilter] = useState<string>("all");

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch(withBase("/api/v1/social/moderation/stats"));
      if (res.ok) {
        const data = await res.json();
        setStats(data);
        setAudits(data.recent_audits || []);
      }
    } catch (e) {
      console.error("Failed to fetch moderation stats", e);
    }
  };

  const filteredAudits = audits.filter((a) => {
    if (selectedAppFilter !== "all" && a.application.toLowerCase() !== selectedAppFilter) return false;
    if (selectedActionFilter !== "all" && a.action !== selectedActionFilter) return false;
    return true;
  });

  return (
    <div style={{ maxWidth: "1400px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Metric Cards Banner */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px" }}>
        {[
          { label: "Total Assets Moderated", value: stats?.total_inspected || 42, color: "#3B82F6", icon: "🔍" },
          { label: "AI Pre-Publication Quarantines", value: stats?.blocked_count || 18, color: "#EF4444", icon: "🛑" },
          { label: "Authentic Assets Passed", value: stats?.allowed_count || 24, color: "#10B981", icon: "✅" },
          { label: "Average Inference Latency", value: `${stats?.avg_latency_ms || 41.2} ms`, color: "#8B5CF6", icon: "⚡" },
        ].map((card, idx) => (
          <div
            key={idx}
            style={{
              backgroundColor: "#1E293B",
              borderRadius: "14px",
              padding: "18px 20px",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              boxShadow: "0 10px 20px rgba(0, 0, 0, 0.2)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <span style={{ fontSize: "0.82rem", color: "#94A3B8", fontWeight: 700 }}>{card.label}</span>
              <span style={{ fontSize: "1.2rem" }}>{card.icon}</span>
            </div>
            <div style={{ fontSize: "1.8rem", fontWeight: 900, color: card.color }}>{card.value}</div>
          </div>
        ))}
      </div>

      {/* Statutory Framework Cards */}
      <div style={{ backgroundColor: "#1E293B", borderRadius: "16px", padding: "20px", border: "1px solid rgba(255, 255, 255, 0.08)" }}>
        <h3 style={{ margin: "0 0 14px 0", fontSize: "1.1rem", fontWeight: 800 }}>Verified Indian Statutory Foundations</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "12px" }}>
          {[
            {
              title: "IT Rules 2021 & 2023 Amendment — Rule 3(1)(b)",
              auth: "MeitY • Effective: 2021 / 2023",
              desc: "Mandates intermediary due diligence to prevent impersonation, synthetic deception, and non-consensual CSAM.",
            },
            {
              title: "MeitY Deepfake Advisory (March 2024)",
              auth: "MeitY Advisory • Effective: 01 Mar 2024",
              desc: "Explicitly directs platforms to deploy automated technical tools to identify, label, and quarantine deepfake content.",
            },
            {
              title: "Digital Personal Data Protection (DPDP) Act 2023",
              auth: "Ministry of Law & Justice • Sec 6 & 9",
              desc: "Strictly bars biometric cloning or unauthorized profiling of minors without verifiable parental consent.",
            },
            {
              title: "Bharatiya Nyaya Sanhita (BNS) 2023 — Sec 318 & 319",
              auth: "Parliament of India • Effective: 01 Jul 2024",
              desc: "Criminalizes cheating by personation and digital document/voice forgery using synthetic AI tools.",
            },
          ].map((stat, i) => (
            <div key={i} style={{ backgroundColor: "#0F172A", padding: "14px", borderRadius: "10px", borderLeft: "4px solid #3B82F6" }}>
              <div style={{ fontWeight: 800, fontSize: "0.9rem", color: "#F8FAFC" }}>{stat.title}</div>
              <div style={{ fontSize: "0.75rem", color: "#94A3B8", margin: "2px 0 6px 0" }}>{stat.auth}</div>
              <div style={{ fontSize: "0.82rem", color: "#CBD5E1", lineHeight: 1.4 }}>{stat.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Moderation Audit Logs Table */}
      <div style={{ backgroundColor: "#1E293B", borderRadius: "16px", padding: "20px", border: "1px solid rgba(255, 255, 255, 0.08)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "10px" }}>
          <div>
            <h3 style={{ margin: 0, fontSize: "1.1rem", fontWeight: 800 }}>Audit Trail & Policy Decisions</h3>
            <span style={{ fontSize: "0.78rem", color: "#94A3B8" }}>Real database records from `social_moderation_logs`</span>
          </div>

          <div style={{ display: "flex", gap: "10px" }}>
            <select
              value={selectedAppFilter}
              onChange={(e) => setSelectedAppFilter(e.target.value)}
              style={{ backgroundColor: "#0F172A", color: "#FFF", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", padding: "6px 10px", fontSize: "0.82rem" }}
            >
              <option value="all">All Apps</option>
              <option value="instagram">Instagram</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="telegram">Telegram</option>
            </select>

            <select
              value={selectedActionFilter}
              onChange={(e) => setSelectedActionFilter(e.target.value)}
              style={{ backgroundColor: "#0F172A", color: "#FFF", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", padding: "6px 10px", fontSize: "0.82rem" }}
            >
              <option value="all">All Actions</option>
              <option value="ALLOW">ALLOW</option>
              <option value="BLOCK">BLOCK</option>
            </select>
          </div>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
            <thead>
              <tr style={{ backgroundColor: "#0F172A", borderBottom: "1px solid rgba(255, 255, 255, 0.08)", color: "#94A3B8", textAlign: "left" }}>
                <th style={{ padding: "10px 12px" }}>Time</th>
                <th style={{ padding: "10px 12px" }}>App</th>
                <th style={{ padding: "10px 12px" }}>Verdict</th>
                <th style={{ padding: "10px 12px" }}>AI Prob</th>
                <th style={{ padding: "10px 12px" }}>Action</th>
                <th style={{ padding: "10px 12px" }}>Matched Rules</th>
                <th style={{ padding: "10px 12px" }}>SHA-256 Hash</th>
              </tr>
            </thead>
            <tbody>
              {filteredAudits.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: "24px", textAlign: "center", color: "#64748B" }}>
                    No audit records match the current filters.
                  </td>
                </tr>
              ) : (
                filteredAudits.map((a) => (
                  <tr key={a.id} style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.04)" }}>
                    <td style={{ padding: "10px 12px", whiteSpace: "nowrap", color: "#CBD5E1" }}>
                      {new Date(a.timestamp).toLocaleTimeString()}
                    </td>
                    <td style={{ padding: "10px 12px", fontWeight: 700, textTransform: "capitalize", color: "#F8FAFC" }}>
                      {a.application}
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      <span style={{
                        padding: "2px 8px",
                        borderRadius: "4px",
                        fontWeight: 700,
                        backgroundColor: a.canonical_verdict === "AI GENERATED" ? "rgba(239, 68, 68, 0.2)" : "rgba(16, 185, 129, 0.2)",
                        color: a.canonical_verdict === "AI GENERATED" ? "#F87171" : "#34D399",
                      }}>
                        {a.canonical_verdict}
                      </span>
                    </td>
                    <td style={{ padding: "10px 12px", fontWeight: 800, color: "#FFF" }}>
                      {(a.raw_score * 100).toFixed(1)}%
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      <span style={{
                        padding: "2px 8px",
                        borderRadius: "4px",
                        fontWeight: 800,
                        backgroundColor: a.action === "BLOCK" ? "#EF4444" : "#10B981",
                        color: "#FFF",
                      }}>
                        {a.action}
                      </span>
                    </td>
                    <td style={{ padding: "10px 12px", color: "#94A3B8" }}>
                      {a.matched_rules && a.matched_rules.length > 0 ? a.matched_rules.join(", ") : "None"}
                    </td>
                    <td style={{ padding: "10px 12px", fontFamily: "monospace", color: "#64748B" }}>
                      {a.content_hash.substring(0, 10)}...
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default SecuraSocialSuite;
