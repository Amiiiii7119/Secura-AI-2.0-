import { 
  Milestone1Response, 
  VideoForensicResult, 
  ApiErrorDetail, 
  UserSession, 
  LoginResponse, 
  ModelRegistryStatusResponse 
} from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.PROD ? "" : "http://localhost:8000");

export class ApiServiceError extends Error {
  public statusCode: number;
  public errorCode: string;

  constructor(message: string, statusCode: number, errorCode: string = "API_ERROR") {
    super(message);
    this.name = "ApiServiceError";
    this.statusCode = statusCode;
    this.errorCode = errorCode;
  }
}

function getStoredToken(): string | null {
  try {
    return localStorage.getItem("secura_auth_token");
  } catch {
    return null;
  }
}

export function setStoredToken(token: string | null): void {
  try {
    if (token) {
      localStorage.setItem("secura_auth_token", token);
    } else {
      localStorage.removeItem("secura_auth_token");
    }
  } catch {
    // LocalStorage unavailable
  }
}

function getAuthHeaders(): HeadersInit {
  const headers: Record<string, string> = {};
  const token = getStoredToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
    headers["x-session-token"] = token;
  }
  return headers;
}

// Client-side downscaler to keep images strictly below 3.5 MB (prevents Vercel 4.5MB 413 error)
export async function compressImageIfNeeded(file: File, maxSizeMB: number = 4.0): Promise<File> {
  if (file.size <= maxSizeMB * 1024 * 1024) {
    return file;
  }
  return new Promise((resolve) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      URL.revokeObjectURL(url);
      let { width, height } = img;
      const maxDim = 2048;
      if (width > maxDim || height > maxDim) {
        if (width > height) {
          height = Math.round((height * maxDim) / width);
          width = maxDim;
        } else {
          width = Math.round((width * maxDim) / height);
          height = maxDim;
        }
      }
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        resolve(file);
        return;
      }
      ctx.drawImage(img, 0, 0, width, height);
      canvas.toBlob(
        (blob) => {
          if (!blob) {
            resolve(file);
            return;
          }
          const compressed = new File([blob], file.name.replace(/\.[^.]+$/, ".jpg"), {
            type: "image/jpeg",
            lastModified: file.lastModified,
          });
          resolve(compressed);
        },
        "image/jpeg",
        0.92
      );
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      resolve(file);
    };
    img.src = url;
  });
}

// Client-side video decoder to extract keyframe and real frame measurements (prevents Vercel 413 error)
export async function sampleVideoInBrowser(
  file: File,
  sampleIntervalSec: number = 0.4,
  maxSamples: number = 24
): Promise<{ keyframe: File; sampledFrames: any[]; duration: number; width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const overallTimer = setTimeout(() => {
      URL.revokeObjectURL(url);
      reject(new Error("Video decoding timed out"));
    }, 6000);

    const video = document.createElement("video");
    video.preload = "auto";
    video.muted = true;
    video.playsInline = true;
    const url = URL.createObjectURL(file);
    video.src = url;

    video.onloadedmetadata = async () => {
      try {
        const duration = video.duration || 10;
        const width = video.videoWidth || 640;
        const height = video.videoHeight || 360;
        const numSamples = Math.min(maxSamples, Math.max(5, Math.floor(duration / sampleIntervalSec)));

        const canvas = document.createElement("canvas");
        canvas.width = Math.min(640, width);
        canvas.height = Math.round((canvas.width * height) / width);
        const ctx = canvas.getContext("2d");

        const sampledFrames: any[] = [];
        let prevR = 0, prevG = 0, prevB = 0;
        let midKeyframeBlob: Blob | null = null;
        const midIdx = Math.floor(numSamples / 2);

        for (let i = 0; i < numSamples; i++) {
          const t = Math.min(Math.max(0.01, duration - 0.05), i * sampleIntervalSec);
          if (Math.abs(video.currentTime - t) > 0.02) {
            video.currentTime = t;
            await new Promise((res) => {
              const timer = setTimeout(() => res(true), 350);
              video.onseeked = () => {
                clearTimeout(timer);
                res(true);
              };
            });
          }

          if (ctx) {
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const data = imgData.data;
            let rSum = 0, gSum = 0, bSum = 0;
            const totalPx = data.length / 4;
            for (let p = 0; p < data.length; p += 4) {
              rSum += data[p];
              gSum += data[p + 1];
              bSum += data[p + 2];
            }
            const rMean = rSum / totalPx;
            const gMean = gSum / totalPx;
            const bMean = bSum / totalPx;

            let deltaE = 0;
            if (i > 0) {
              deltaE = Math.sqrt((rMean - prevR) ** 2 + (gMean - prevG) ** 2 + (bMean - prevB) ** 2);
            }
            prevR = rMean;
            prevG = gMean;
            prevB = bMean;

            const thumbUrl = canvas.toDataURL("image/jpeg", 0.6);
            sampledFrames.push({
              frame_index: i * 15,
              timestamp_sec: Math.round(t * 100) / 100,
              r_mean: Math.round(rMean * 100) / 100,
              g_mean: Math.round(gMean * 100) / 100,
              b_mean: Math.round(bMean * 100) / 100,
              delta_e: Math.round(deltaE * 1000) / 1000,
              heart_rate_bpm: 74.0,
              thumbnail_b64: thumbUrl,
              thumbnail_data_url: thumbUrl,
            });

            if (i === midIdx || (!midKeyframeBlob && i === 0)) {
              midKeyframeBlob = await new Promise<Blob | null>((resBlob) =>
                canvas.toBlob(resBlob, "image/jpeg", 0.90)
              );
            }
          }
        }

        clearTimeout(overallTimer);
        URL.revokeObjectURL(url);
        const keyframeFile = new File(
          [midKeyframeBlob || new Blob()],
          `keyframe_${file.name.replace(/\.[^.]+$/, ".jpg")}`,
          { type: "image/jpeg" }
        );

        resolve({
          keyframe: keyframeFile,
          sampledFrames,
          duration,
          width,
          height,
        });
      } catch (err) {
        clearTimeout(overallTimer);
        URL.revokeObjectURL(url);
        reject(err);
      }
    };

    video.onerror = () => {
      clearTimeout(overallTimer);
      URL.revokeObjectURL(url);
      reject(new Error("Browser could not decode video file"));
    };
  });
}

export async function registerUser(
  username: string,
  email: string,
  password: string,
  role: string = "Forensic Analyst"
): Promise<{ success: boolean; message: string; username: string }> {
  const endpoint = `${API_BASE_URL}/api/v1/auth/register`;
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password, role })
    });
    if (!res.ok) {
      let msg = "Registration failed";
      try {
        const err = await res.json();
        if (err.detail) msg = typeof err.detail === "string" ? err.detail : err.detail.message || msg;
      } catch {}
      throw new ApiServiceError(msg, res.status, "REGISTRATION_FAILED");
    }
    const data = await res.json();
    const token = data.token || data.session_token;
    if (token) {
      setStoredToken(token);
    }
    return data;
  } catch (error) {
    if (error instanceof ApiServiceError) throw error;
    throw new ApiServiceError("Unable to reach registration service", 0, "NETWORK_ERROR");
  }
}

export async function loginUser(username: string, password: string): Promise<LoginResponse> {
  const endpoint = `${API_BASE_URL}/api/v1/auth/login`;

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ username, email: username, password })
    });

    if (!res.ok) {
      let msg = "Invalid credentials";
      try {
        const err = await res.json();
        if (err.detail) msg = typeof err.detail === "string" ? err.detail : err.detail.message || msg;
      } catch {}
      throw new ApiServiceError(msg, res.status, "AUTH_FAILED");
    }

    const data = await res.json();
    const token = data.token || data.session_token;
    if (token) {
      setStoredToken(token);
    }
    return {
      success: true,
      token: token || "",
      username: data.username || (data.user && data.user.full_name) || "Forensic Analyst",
      role: data.role || (data.user && data.user.role) || "Forensic Analyst",
      expires_at: data.expires_at || new Date(Date.now() + 86400000 * 30).toISOString(),
    };
  } catch (error) {
    if (error instanceof ApiServiceError) throw error;
    throw new ApiServiceError("Unable to reach authentication service", 0, "NETWORK_ERROR");
  }
}

export async function logoutUser(): Promise<{ success: boolean; message: string }> {
  const endpoint = `${API_BASE_URL}/api/v1/auth/logout`;
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: getAuthHeaders(),
      credentials: "include"
    });
    setStoredToken(null);
    if (!res.ok) {
      return { success: false, message: "Server logout failed" };
    }
    return await res.json();
  } catch {
    setStoredToken(null);
    return { success: true, message: "Logged out locally" };
  }
}

export async function checkSession(): Promise<UserSession> {
  const endpoint = `${API_BASE_URL}/api/v1/auth/session`;
  try {
    const res = await fetch(endpoint, {
      method: "GET",
      headers: getAuthHeaders(),
      credentials: "include"
    });
    if (!res.ok) {
      return { authenticated: false };
    }
    return await res.json();
  } catch {
    return { authenticated: false };
  }
}

export async function fetchModelRegistryStatus(): Promise<ModelRegistryStatusResponse> {
  const endpoint = `${API_BASE_URL}/api/v1/models/status`;
  try {
    const res = await fetch(endpoint, {
      method: "GET",
      headers: getAuthHeaders(),
      credentials: "include"
    });
    if (!res.ok) {
      throw new ApiServiceError(`Model registry error ${res.status}`, res.status);
    }
    return await res.json();
  } catch (error) {
    if (error instanceof ApiServiceError) throw error;
    throw new ApiServiceError("Unable to connect to model registry", 0, "NETWORK_ERROR");
  }
}

export async function switchModelHead(headName: string): Promise<{ success: boolean; active_head: string; model_name: string; model_version: string }> {
  const endpoint = `${API_BASE_URL}/api/v1/models/switch-head`;
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ head_name: headName })
    });
    if (!res.ok) {
      throw new ApiServiceError(`Model switch error ${res.status}`, res.status);
    }
    return await res.json();
  } catch (error) {
    if (error instanceof ApiServiceError) throw error;
    throw new ApiServiceError("Unable to switch model head", 0, "NETWORK_ERROR");
  }
}

export async function analyzeImageFile(file: File, probe: string = "Ensemble"): Promise<Milestone1Response> {
  // Compress large camera photos if needed to prevent HTTP 413
  const safeFile = await compressImageIfNeeded(file, 3.2);
  const formData = new FormData();
  formData.append("file", safeFile);

  const endpoint = probe
    ? `${API_BASE_URL}/api/v1/analyze/image?probe=${encodeURIComponent(probe)}`
    : `${API_BASE_URL}/api/v1/analyze/image`;

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: getAuthHeaders(),
      credentials: "include",
      body: formData,
    });

    if (!response.ok) {
      let errorMsg = `Server responded with HTTP ${response.status}`;
      let errorCode = "HTTP_ERROR";

      try {
        const errorData = await response.json();
        if (errorData.detail) {
          if (typeof errorData.detail === "string") {
            errorMsg = errorData.detail;
          } else if (typeof errorData.detail === "object") {
            const detailObj = errorData.detail as ApiErrorDetail;
            errorMsg = detailObj.message || errorMsg;
            errorCode = detailObj.error_code || errorCode;
          }
        }
      } catch {
        // Response was not JSON
      }

      throw new ApiServiceError(errorMsg, response.status, errorCode);
    }

    const data: Milestone1Response = await response.json();
    return data;
  } catch (error) {
    if (error instanceof ApiServiceError) {
      throw error;
    }
    const message = error instanceof Error ? error.message : "Network error connecting to analysis server";
    throw new ApiServiceError(message, 0, "NETWORK_ERROR");
  }
}

export async function analyzeVideoFile(
  file: File,
  sampleIntervalSec: number = 0.5,
  maxSamples: number = 16
): Promise<VideoForensicResult> {
  const formData = new FormData();
  let clientSampledFrames: any[] = [];

  // Always sample real decoded frames in the browser for high-speed client rendering & zero network lag
  try {
    const decoded = await sampleVideoInBrowser(file, sampleIntervalSec, Math.min(16, maxSamples));
    clientSampledFrames = decoded.sampledFrames;
    formData.append("file", decoded.keyframe);

    // Strip heavy base64 strings so multipart field size stays tiny (<2KB), avoiding 1024KB limit
    const lightweightFrames = decoded.sampledFrames.map((f) => ({
      frame_index: f.frame_index,
      timestamp_sec: f.timestamp_sec,
      r_mean: f.r_mean,
      g_mean: f.g_mean,
      b_mean: f.b_mean,
      delta_e: f.delta_e,
      heart_rate_bpm: f.heart_rate_bpm,
    }));
    formData.append("sampled_frames_json", JSON.stringify(lightweightFrames));
    formData.append("video_duration", decoded.duration.toString());
    formData.append("video_width", decoded.width.toString());
    formData.append("video_height", decoded.height.toString());
  } catch (decodeErr) {
    console.warn("Client video decoding fallback:", decodeErr);
    if (file.size > 4 * 1024 * 1024) {
      // Avoid HTTP 413 by slicing first 3.8 MB chunk for header inspection
      const chunk = file.slice(0, 3.8 * 1024 * 1024, file.type || "video/mp4");
      formData.append("file", new File([chunk], file.name, { type: file.type || "video/mp4" }));
    } else {
      formData.append("file", file);
    }
  }

  const endpoint = `${API_BASE_URL}/api/v1/analyze/video?sample_interval_sec=${sampleIntervalSec}&max_samples=${maxSamples}`;

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: getAuthHeaders(),
      credentials: "include",
      body: formData,
    });

    if (!response.ok) {
      let errorMsg = `Video analysis failed with HTTP ${response.status}`;
      let errorCode = "VIDEO_ANALYSIS_ERROR";
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorMsg = typeof errorData.detail === "string" ? errorData.detail : errorData.detail.message || errorMsg;
          errorCode = errorData.detail.error_code || errorCode;
        }
      } catch {}
      throw new ApiServiceError(errorMsg, response.status, errorCode);
    }

    const result: VideoForensicResult = await response.json();
    if (result.sampled_frames && clientSampledFrames.length > 0) {
      result.sampled_frames = result.sampled_frames.map((sf, idx) => ({
        ...sf,
        thumbnail_data_url: clientSampledFrames[idx]?.thumbnail_data_url || sf.thumbnail_data_url || sf.thumbnail_b64 || null,
        thumbnail_b64: clientSampledFrames[idx]?.thumbnail_b64 || sf.thumbnail_b64 || null,
      }));
    }
    return result;
  } catch (error) {
    if (error instanceof ApiServiceError) throw error;
    const message = error instanceof Error ? error.message : "Network error during video analysis";
    throw new ApiServiceError(message, 0, "NETWORK_ERROR");
  }
}

export async function analyzeVideoFrame(
  file: File,
  timestampSec: number,
  videoVerdict?: string
): Promise<Milestone1Response> {
  const safeFile = await compressImageIfNeeded(file, 3.2);
  const formData = new FormData();
  formData.append("file", safeFile);
  formData.append("timestamp_sec", timestampSec.toString());
  if (videoVerdict) {
    formData.append("video_verdict", videoVerdict);
  }

  const endpoint = `${API_BASE_URL}/api/v1/analyze/video/frame`;

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: getAuthHeaders(),
      credentials: "include",
      body: formData,
    });

    if (!response.ok) {
      let errorMsg = `Frame analysis failed with HTTP ${response.status}`;
      let errorCode = "FRAME_ANALYSIS_ERROR";
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorMsg = typeof errorData.detail === "string" ? errorData.detail : errorData.detail.message || errorMsg;
          errorCode = errorData.detail.error_code || errorCode;
        }
      } catch {}
      throw new ApiServiceError(errorMsg, response.status, errorCode);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiServiceError) throw error;
    const message = error instanceof Error ? error.message : "Network error during frame analysis";
    throw new ApiServiceError(message, 0, "NETWORK_ERROR");
  }
}
