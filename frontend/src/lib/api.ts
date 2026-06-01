// Typed API client for the FastAPI backend
import type {
  BuildDeckRequest,
  BuildDeckResponse,
  CacheStatsResponse,
  CandidateExtractRequest,
  CandidateExtractResponse,
  DetectLanguageResponse,
  GenerateRequest,
  GenerateResponse,
  HealthResponse,
  ImportDeckResponse,
  ModelInfo,
  RegenerateCardFieldRequest,
  RegenerateCardFieldResponse,
  RegenerateCardImageRequest,
  RegenerateCardImageResponse,
  TaskStatusResponse,
  TTSRequest,
  TTSResponse,
} from "@/types"
import { API_BASE } from "@/lib/apiBase"

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 10_000)

  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, {
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
      },
      ...init,
    })
  } finally {
    clearTimeout(timeoutId)
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      if (typeof body?.detail === "string") detail = body.detail
    } catch {
      // ignore parse errors
    }
    throw new Error(detail)
  }
  if (res.status === 204) return undefined as unknown as T
  return res.json() as Promise<T>
}

export const api = {
  getHealth: () => request<HealthResponse>("/health"),

  getModels: () => request<{ models: ModelInfo[] }>("/api/models"),

  startGeneration: (body: GenerateRequest) =>
    request<GenerateResponse>("/api/generate", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getTaskStatus: (taskId: string) =>
    request<TaskStatusResponse>(`/api/generate/${taskId}`),

  extractCandidates: (body: CandidateExtractRequest) =>
    request<CandidateExtractResponse>("/api/candidates/extract", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  createSSEConnection: async (taskId: string): Promise<EventSource> =>
    new EventSource(`${API_BASE}/api/generate/${taskId}/stream`),

  buildDeck: (body: BuildDeckRequest) =>
    request<BuildDeckResponse>("/api/deck/build", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getDeckDownloadUrl: (filename: string): string =>
    `${API_BASE}/api/deck/${filename}/download`,

  importDeck: async (file: File): Promise<ImportDeckResponse> => {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 30_000)
    let res: Response
    try {
      res = await fetch(
        `${API_BASE}/api/deck/import?filename=${encodeURIComponent(file.name)}`,
        {
          method: "POST",
          body: file,
          signal: controller.signal,
          headers: {
            "Content-Type": "application/octet-stream",
          },
        }
      )
    } finally {
      clearTimeout(timeoutId)
    }
    if (!res.ok) {
      let detail = `HTTP ${res.status}`
      try {
        const body = await res.json()
        if (typeof body?.detail === "string") detail = body.detail
      } catch {
        // ignore parse errors
      }
      throw new Error(detail)
    }
    return res.json() as Promise<ImportDeckResponse>
  },

  generateTTS: (body: TTSRequest) =>
    request<TTSResponse>("/api/tts/generate", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  regenerateCardField: (body: RegenerateCardFieldRequest) =>
    request<RegenerateCardFieldResponse>("/api/cards/regenerate-field", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  regenerateCardImage: (body: RegenerateCardImageRequest) =>
    request<RegenerateCardImageResponse>("/api/cards/regenerate-image", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  detectLanguage: (text: string) =>
    request<DetectLanguageResponse>("/api/detect-language", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),

  getCacheStats: () => request<CacheStatsResponse>("/api/cache/stats"),

  deleteCache: () => request<void>("/api/cache", { method: "DELETE" }),
}
