const rawBase = import.meta.env.VITE_API_BASE_URL || "https://researchbridge-r327.onrender.com";
const API_BASE = rawBase.replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(status, message, payload) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

export async function api(path, options = {}) {
  const token = sessionStorage.getItem("rb-token") || localStorage.getItem("rb-token");
  if (token && !sessionStorage.getItem("rb-token")) {
    sessionStorage.setItem("rb-token", token);
  }
  const headers = new Headers(options.headers || {});
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = `${API_BASE}${normalizedPath}`;
  let response;
  try {
    response = await fetch(url, { ...options, headers });
  } catch {
    throw new ApiError(0, "The ResearchBridge API could not be reached.");
  }
  const payload = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg).join(" ")
      : detail || `Request failed (${response.status}).`;
    throw new ApiError(response.status, message, payload);
  }
  return payload;
}

export const json = (method, value) => ({ method, body: JSON.stringify(value) });
