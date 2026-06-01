export type ImageProvider = "local" | "openai" | "google"
export type TTSProvider = "qwen3" | "openai" | "google"

export interface MediaOption {
  value: string
  label: string
}

export const IMAGE_PROVIDER_OPTIONS: MediaOption[] = [
  { value: "local", label: "Local Stable Diffusion" },
  { value: "openai", label: "OpenAI Image API" },
  { value: "google", label: "Google Nano Banana 2" },
]

export const IMAGE_MODEL_OPTIONS: Record<ImageProvider, MediaOption[]> = {
  local: [{ value: "local/stable-diffusion", label: "Stable Diffusion 1.5 + LCM" }],
  openai: [
    { value: "gpt-image-1", label: "GPT Image 1" },
    { value: "dall-e-3", label: "DALL-E 3" },
  ],
  google: [
    {
      value: "gemini/gemini-3.1-flash-image-preview",
      label: "Nano Banana 2 (Gemini 3.1 Flash Image)",
    },
  ],
}

export const TTS_PROVIDER_OPTIONS: MediaOption[] = [
  { value: "qwen3", label: "Local Qwen3 TTS" },
  { value: "openai", label: "OpenAI TTS" },
  { value: "google", label: "Google Gemini TTS" },
]

export const TTS_MODEL_OPTIONS: Record<TTSProvider, MediaOption[]> = {
  qwen3: [
    {
      value: "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
      label: "Qwen3 TTS Custom Voice",
    },
  ],
  openai: [
    { value: "openai/tts-1", label: "TTS 1" },
    { value: "openai/tts-1-hd", label: "TTS 1 HD" },
    { value: "openai/gpt-4o-mini-tts", label: "GPT-4o mini TTS" },
  ],
  google: [
    { value: "gemini/gemini-2.5-flash-preview-tts", label: "Gemini 2.5 Flash TTS" },
    { value: "gemini/gemini-2.5-pro-preview-tts", label: "Gemini 2.5 Pro TTS" },
  ],
}

export const TTS_VOICE_OPTIONS: Record<TTSProvider, MediaOption[]> = {
  qwen3: [
    { value: "Vivian", label: "Vivian" },
    { value: "Ryan", label: "Ryan" },
  ],
  openai: [
    { value: "alloy", label: "alloy" },
    { value: "echo", label: "echo" },
    { value: "fable", label: "fable" },
    { value: "onyx", label: "onyx" },
    { value: "nova", label: "nova" },
    { value: "shimmer", label: "shimmer" },
  ],
  google: [
    { value: "Kore", label: "Kore" },
    { value: "Puck", label: "Puck" },
    { value: "Charon", label: "Charon" },
  ],
}

export function getDefaultImageModel(provider: ImageProvider): string {
  return IMAGE_MODEL_OPTIONS[provider][0].value
}

export function getDefaultTTSModel(provider: TTSProvider): string {
  return TTS_MODEL_OPTIONS[provider][0].value
}

export function getDefaultTTSVoice(provider: TTSProvider): string {
  return TTS_VOICE_OPTIONS[provider][0].value
}