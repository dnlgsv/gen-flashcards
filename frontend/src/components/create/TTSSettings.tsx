import { Label } from "@/components/ui/label"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ArrowRight, Sparkles, Loader2 } from "lucide-react"
import {
  TTS_MODEL_OPTIONS,
  TTS_PROVIDER_OPTIONS,
  TTS_VOICE_OPTIONS,
  type TTSProvider,
  getDefaultTTSModel,
  getDefaultTTSVoice,
} from "@/lib/mediaCatalog"

export const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "ru", label: "Russian" },
  { code: "de", label: "German" },
  { code: "fr", label: "French" },
  { code: "es", label: "Spanish" },
  { code: "it", label: "Italian" },
  { code: "zh", label: "Chinese" },
  { code: "ja", label: "Japanese" },
  { code: "ko", label: "Korean" },
  { code: "pt", label: "Portuguese" },
  { code: "ar", label: "Arabic" },
  { code: "nl", label: "Dutch" },
  { code: "pl", label: "Polish" },
  { code: "tr", label: "Turkish" },
]

interface TTSSettingsValue {
  ttsProvider: TTSProvider
  ttsModel: string
  language: string        // source language code, "auto" = detect
  targetLanguage: string  // target language for translations
  speaker: string
  audioFormat: "mp3" | "wav"
}

interface TTSSettingsProps extends TTSSettingsValue {
  enableAudio: boolean
  detectedLanguage?: string | null
  isDetecting?: boolean
  onChange: (partial: Partial<TTSSettingsValue>) => void
}

function getLanguageLabel(code: string): string {
  return LANGUAGES.find((l) => l.code === code)?.label ?? code
}

export function TTSSettings({
  enableAudio,
  ttsProvider,
  ttsModel,
  language,
  targetLanguage,
  speaker,
  audioFormat,
  detectedLanguage,
  isDetecting = false,
  onChange,
}: TTSSettingsProps) {
  const isAuto = (language ?? "auto") === "auto"
  const detectedLabel = detectedLanguage ? getLanguageLabel(detectedLanguage) : null
  const modelOptions = TTS_MODEL_OPTIONS[ttsProvider]
  const voiceOptions = TTS_VOICE_OPTIONS[ttsProvider]

  // What to render inside the source language trigger.
  // NOTE: SelectTrigger applies [&>span]:line-clamp-1 which sets
  // display:-webkit-box + -webkit-box-orient:vertical on direct <span> children,
  // breaking flex layout. Keep the icon as a sibling SVG (not inside the span).
  function SourceTriggerContent() {
    if (isAuto && isDetecting) {
      return (
        <>
          <Loader2 className="h-3 w-3 animate-spin shrink-0 text-muted-foreground" />
          <span className="ml-1.5 text-muted-foreground">Detecting…</span>
        </>
      )
    }
    if (isAuto && detectedLabel) {
      return (
        <>
          <Sparkles className="h-3 w-3 shrink-0 text-muted-foreground" />
          <span className="ml-1.5">{detectedLabel}</span>
        </>
      )
    }
    return <SelectValue />
  }

  return (
    <div className="space-y-3">
      {/* Source → Target language row */}
      <div className="flex items-center gap-2">
        {/* Source language */}
        <div className="flex-1 space-y-1.5">
          <Label>Source language</Label>
          <Select
            value={language ?? "auto"}
            onValueChange={(v) => onChange({ language: v })}
          >
            <SelectTrigger className="h-10">
              <SourceTriggerContent />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="auto">
                <span className="flex items-center gap-1.5">
                  <Sparkles className="h-3 w-3 text-muted-foreground" />
                  Auto-detect
                </span>
              </SelectItem>
              {LANGUAGES.map(({ code, label }) => (
                <SelectItem key={code} value={code}>{label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="mt-6 text-muted-foreground shrink-0">
          <ArrowRight className="h-4 w-4" />
        </div>

        {/* Target language */}
        <div className="flex-1 space-y-1.5">
          <Label>Target language</Label>
          <Select
            value={targetLanguage ?? "ru"}
            onValueChange={(v) => onChange({ targetLanguage: v })}
          >
            <SelectTrigger className="h-10">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {LANGUAGES.map(({ code, label }) => (
                <SelectItem key={code} value={code}>{label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {enableAudio ? (
        <>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>TTS provider</Label>
              <Select
                value={ttsProvider}
                onValueChange={(value) => {
                  const provider = value as TTSProvider
                  onChange({
                    ttsProvider: provider,
                    ttsModel: getDefaultTTSModel(provider),
                    speaker: getDefaultTTSVoice(provider),
                  })
                }}
              >
                <SelectTrigger className="h-10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TTS_PROVIDER_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>TTS model</Label>
              <Select value={ttsModel} onValueChange={(value) => onChange({ ttsModel: value })}>
                <SelectTrigger className="h-10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {modelOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Voice</Label>
              <Select value={speaker} onValueChange={(value) => onChange({ speaker: value })}>
                <SelectTrigger className="h-10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {voiceOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Format</Label>
              <Tabs
                value={audioFormat}
                onValueChange={(v) => onChange({ audioFormat: v as "mp3" | "wav" })}
              >
                <TabsList className="h-10 w-full">
                  <TabsTrigger value="mp3" className="h-8 flex-1 text-sm">MP3</TabsTrigger>
                  <TabsTrigger value="wav" className="h-8 flex-1 text-sm">WAV</TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
          </div>
        </>
      ) : null}
    </div>
  )
}
