import { 
  Milestone1Response,
  VideoForensicResult, 
  ApiErrorDetail, 
  UserSession, 
  LoginResponse, 
  ModelRegistryStatusResponse 
} from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

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
  }
  return headers;
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
    return await res.json();
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
      body: JSON.stringify({ username, password })
    });

    if (!res.ok) {
      let msg = "Invalid credentials";
      try {
        const err = await res.json();
        if (err.detail) msg = typeof err.detail === "string" ? err.detail : err.detail.message || msg;
      } catch {}
      throw new ApiServiceError(msg, res.status, "AUTH_FAILED");
    }

    const data: LoginResponse = await res.json();
    setStoredToken(data.token);
    return data;
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
  const formData = new FormData();
  formData.append("file", file);

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
  maxSamples: number = 60
): Promise<VideoForensicResult> {
  const formData = new FormData();
  formData.append("file", file);

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

    return await response.json();
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
  const formData = new FormData();
  formData.append("file", file);
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
