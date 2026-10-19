// Shared API base resolution for ALL Secura AI frontend HTTP calls.
// - Dev: VITE_API_BASE_URL unset -> http://localhost:8000 (direct to FastAPI backend)
// - Prod: VITE_API_BASE_URL set in Vercel env -> Railway backend origin
// - Prod fallback: same-origin (Vercel /api rewrites) when env var missing
export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.PROD ? "" : "http://localhost:8000");

export const withBase = (path: string): string => `${API_BASE_URL}${path}`;
