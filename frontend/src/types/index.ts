// Shared TypeScript types for the local browser app.

export interface CardInfo {
  expression: string
  original_form: string
  part_of_speech: string
  definition: string
  examples: string[]
  synonyms: string[]
  antonyms: string[]
  collocations: string[]
  translations: string[]
  cefr_level: string
  topics: string[]
  audio_expression?: string
  audio_definition?: string
  audio_examples?: string
  audio_collocations?: string
  audio_synonyms?: string
  image?: string
}

export type CardType = "recognition" | "reverse" | "production" | "cloze"

export interface ModelInfo {
  name: string
  path: string
  provider: string
  loaded: boolean
}

export type TaskStatus = "pending" | "running" | "completed" | "failed"

export type ViewStatus =
  | "idle"
  | "loading"
  | "streaming"
  | "reviewing"
  | "building"
  | "done"
  | "error"

export interface GenerateRequest {
  words: string[]
  model_name: string
  deck_name: string
  tts_provider: "qwen3" | "openai" | "google"
  tts_model?: string | null
  language: string
  target_language: string
  speaker: string
  audio_format: "mp3" | "wav"
  learner_level: "auto" | "A1" | "A2" | "B1" | "B2" | "C1" | "C2"
  enable_audio?: boolean
  enable_images?: boolean
  image_provider?: "local" | "openai" | "google"
  image_model?: string | null
}

export interface GenerateResponse {
  task_id: string
  status: TaskStatus
  message: string
}

export interface Candidate {
  expression: string
  kind: "word" | "phrase"
  score: number
  frequency: number
  contexts: string[]
  reason: string
}

export interface CandidateExtractRequest {
  text: string
  language: string
  learner_level: "auto" | "A1" | "A2" | "B1" | "B2" | "C1" | "C2"
  target_count: number
  include_phrases: boolean
  use_model_rerank: boolean
  model_name?: string | null
}

export interface CandidateExtractResponse {
  candidates: Candidate[]
}

export interface TaskStatusResponse {
  task_id: string
  status: TaskStatus
  total_words: number
  processed_words: number
  progress_pct: number
  result: CardInfo[] | null
  error: string | null
  created_at: string
  updated_at: string
}

export interface BuildDeckRequest {
  cards_data: CardInfo[]
  deck_name: string
  card_types: CardType[]
  task_id?: string
}

export interface BuildDeckResponse {
  filename: string
  deck_name: string
  card_count: number
  download_url: string
}

export interface ImportDeckResponse {
  deck_name: string
  card_count: number
  cards: CardInfo[]
}

export interface DeckHistoryItem {
  task_id: string
  deck_name: string
  word_count: number
  card_count: number
  status: "generating" | "ready" | "failed"
  filename?: string
  download_url?: string
  created_at: string
  updated_at: string
}

export interface TTSRequest {
  text: string
  language: string
  provider: "qwen3" | "openai" | "google"
  model?: string | null
  speaker: string
  response_format?: "mp3" | "wav"
}

export interface TTSResponse {
  filename: string
  url: string
}

export interface RegenerateCardFieldRequest {
  card: CardInfo
  field: "definition" | "examples"
  model_name: string
  learner_level: "auto" | "A1" | "A2" | "B1" | "B2" | "C1" | "C2"
  target_language: string
}

export interface RegenerateCardFieldResponse {
  field: "definition" | "examples"
  value: string | string[]
}

export interface RegenerateCardImageRequest {
  card: CardInfo
  provider: "local" | "openai" | "google"
  model?: string | null
}

export interface RegenerateCardImageResponse {
  filename: string
  url: string
  image: string
}

export interface DetectLanguageResponse {
  language: string | null
  language_name: string | null
}

export interface CacheStatsResponse {
  total_entries: number
  valid_entries: number
  expired_entries: number
  total_size_bytes: number
  cache_dir: string
}

export interface HealthResponse {
  status: "ok"
  version: string
  device: string
  loaded_models: string[]
  cache_enabled: boolean
}

export type SSEEventType =
  | "word_start"
  | "word_complete"
  | "word_error"
  | "complete"
  | "failed"

export interface SSEEventRecord {
  type: SSEEventType | string
  processed?: number
  total?: number
  timestamp?: string
  data?: {
    word?: string
    index?: number
    total?: number
    error?: string
    card?: CardInfo
    message?: string
    total_cards?: number
    skipped?: number
  }
}

export interface FormState {
  rawWords: string
  modelName: string
  deckName: string
  ttsProvider: "qwen3" | "openai" | "google"
  ttsModel: string
  language: string
  targetLanguage: string
  speaker: string
  audioFormat: "mp3" | "wav"
  learnerLevel: "auto" | "A1" | "A2" | "B1" | "B2" | "C1" | "C2"
  enableAudio: boolean
  enableImages: boolean
  imageProvider: "local" | "openai" | "google"
  imageModel: string
}
