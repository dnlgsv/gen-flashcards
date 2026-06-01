export function getApiBase(): string {
  if (typeof window !== "undefined") {
    if (window.location.port.startsWith("300")) return "http://localhost:8000"
    return window.location.origin
  }
  return "http://127.0.0.1:8000"
}

export const API_BASE = getApiBase()
