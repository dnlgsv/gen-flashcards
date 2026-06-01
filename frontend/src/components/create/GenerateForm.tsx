"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import {
  CheckCheck,
  ImageIcon,
  Loader2,
  Sparkles,
  Trash2,
  Volume2,
  type LucideIcon,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { WordsInput, parseWords, type WordsInputMode } from "./WordsInput"
import { DeckNameInput } from "./DeckNameInput"
import { ModelSelect } from "./ModelSelect"
import { TTSSettings } from "./TTSSettings"
import { useModels } from "@/hooks/useModels"
import { useGenerationStore } from "@/store/generationStore"
import { api } from "@/lib/api"
import {
  IMAGE_MODEL_OPTIONS,
  IMAGE_PROVIDER_OPTIONS,
  type ImageProvider,
  getDefaultImageModel,
} from "@/lib/mediaCatalog"
import { cn } from "@/lib/utils"
import type { Candidate } from "@/types"

const LEARNER_LEVELS = [
  { value: "auto", label: "Auto" },
  { value: "A1", label: "A1" },
  { value: "A2", label: "A2" },
  { value: "B1", label: "B1" },
  { value: "B2", label: "B2" },
  { value: "C1", label: "C1" },
  { value: "C2", label: "C2" },
] as const

interface MediaSwitchProps {
  checked: boolean
  icon: LucideIcon
  label: string
  onChange: (checked: boolean) => void
}

function MediaSwitch({ checked, icon: Icon, label, onChange }: MediaSwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={cn(
        "flex h-10 w-full items-center justify-between rounded-md border px-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
        checked
          ? "border-primary/40 bg-primary/5 text-foreground"
          : "border-input bg-background text-muted-foreground hover:bg-muted/50"
      )}
    >
      <span className="flex items-center gap-2 font-medium">
        <Icon className="h-4 w-4 shrink-0" />
        <span>{label}</span>
      </span>
      <span className="ml-2 flex shrink-0 items-center gap-2">
        <span
          className={cn(
            "text-sm font-medium tabular-nums",
            checked ? "text-primary" : "text-muted-foreground"
          )}
        >
          {checked ? "On" : "Off"}
        </span>
        <span
          className={cn(
            "relative h-5 w-9 rounded-full transition-colors",
            checked ? "bg-primary" : "bg-muted-foreground/30"
          )}
        >
          <span
            className={cn(
              "absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-background shadow-sm transition-transform",
              checked && "translate-x-4"
            )}
          />
        </span>
      </span>
    </button>
  )
}

export function GenerateForm() {
  const router = useRouter()
  const { data: modelsData, isLoading: modelsLoading } = useModels()

  const { form, setFormField, setTaskId, recordTaskStart, reset, clearEvents } =
    useGenerationStore()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [wordsError, setWordsError] = useState<string>()
  const [detectedLanguage, setDetectedLanguage] = useState<string | null>(null)
  const [isDetecting, setIsDetecting] = useState(false)
  const [inputMode, setInputMode] = useState<WordsInputMode>("words")
  const [isExtracting, setIsExtracting] = useState(false)
  const [candidates, setCandidates] = useState<
    Array<Candidate & { selected: boolean }>
  >([])
  const enableAudio = form.enableAudio ?? true

  // Debounced language detection whenever the words input changes
  useEffect(() => {
    const text = form.rawWords.trim()
    if (!text) {
      setDetectedLanguage(null)
      setIsDetecting(false)
      return
    }
    const timer = setTimeout(async () => {
      setIsDetecting(true)
      try {
        const result = await api.detectLanguage(text)
        console.log("[detect-language] result:", result)
        setDetectedLanguage(result.language)
      } catch (err) {
        console.error("[detect-language] error:", err)
        setDetectedLanguage(null)
      } finally {
        setIsDetecting(false)
      }
    }, 800)
    return () => clearTimeout(timer)
  }, [form.rawWords])

  const resolvedInputLanguage =
    form.language === "auto" ? (detectedLanguage ?? "en") : form.language

  const handleExtractCandidates = async () => {
    if (!form.rawWords.trim()) {
      setWordsError("Please paste text before extracting candidates")
      return
    }
    setWordsError(undefined)

    try {
      setIsExtracting(true)
      const result = await api.extractCandidates({
        text: form.rawWords,
        language: resolvedInputLanguage,
        learner_level: form.learnerLevel,
        target_count: 30,
        include_phrases: true,
        use_model_rerank: false,
        model_name: form.modelName || null,
      })
      const next = result.candidates.map((candidate) => ({
        ...candidate,
        selected: true,
      }))
      setCandidates(next)
      if (next.length === 0) {
        toast.error("No useful candidates found in this text")
      } else {
        toast.success(
          `Extracted ${next.length} candidate${next.length !== 1 ? "s" : ""}`
        )
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to extract candidates"
      toast.error(msg)
    } finally {
      setIsExtracting(false)
    }
  }

  const applySelectedCandidates = () => {
    const selected = candidates
      .filter((candidate) => candidate.selected)
      .map((candidate) => candidate.expression)
    if (selected.length === 0) {
      setWordsError("Select at least one candidate")
      return
    }
    setFormField("rawWords", selected.join("\n"))
    setInputMode("words")
    setWordsError(undefined)
    toast.success(
      `${selected.length} candidate${selected.length !== 1 ? "s" : ""} ready`
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    const selectedCandidateWords = candidates
      .filter((candidate) => candidate.selected)
      .map((candidate) => candidate.expression)
    const words =
      inputMode === "text"
        ? Array.from(new Set(selectedCandidateWords))
        : parseWords(form.rawWords)
    if (words.length === 0) {
      setWordsError(
        inputMode === "text"
          ? "Extract and select at least one candidate"
          : "Please enter at least one word"
      )
      return
    }
    if (!form.modelName) {
      toast.error("Please select a model")
      return
    }
    setWordsError(undefined)

    try {
      setIsSubmitting(true)
      reset()
      clearEvents()

      const resp = await api.startGeneration({
        words,
        model_name: form.modelName,
        deck_name: form.deckName || "Vocabulary Deck",
        tts_provider: form.ttsProvider,
        tts_model: form.ttsModel,
        language: resolvedInputLanguage,
        target_language: form.targetLanguage,
        speaker: form.speaker,
        audio_format: form.audioFormat,
        learner_level: form.learnerLevel,
        enable_audio: enableAudio,
        enable_images: form.enableImages,
        image_provider: form.imageProvider,
        image_model: form.imageModel,
      })

      setTaskId(resp.task_id)
      recordTaskStart(resp.task_id, form.deckName || "Vocabulary Deck", words.length)
      toast.success(`Generation started for ${words.length} words`)
      router.push(`/create?task=${resp.task_id}`)
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to start generation"
      toast.error(msg)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="grid grid-cols-[2fr_3fr] gap-6 items-start">
        {/* Left column: settings */}
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <DeckNameInput
              value={form.deckName}
              onChange={(v) => setFormField("deckName", v)}
            />
            <div className="space-y-1.5">
              <Label>Learner Level</Label>
              <Select
                value={form.learnerLevel}
                onValueChange={(value) => {
                  setFormField("learnerLevel", value as typeof form.learnerLevel)
                }}
              >
              <SelectTrigger className="h-10">
                <SelectValue />
              </SelectTrigger>
                <SelectContent>
                  {LEARNER_LEVELS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <ModelSelect
            value={form.modelName}
            onChange={(v) => setFormField("modelName", v)}
            models={modelsData?.models ?? []}
            isLoading={modelsLoading}
          />

          <div className="grid grid-cols-2 gap-3">
            <MediaSwitch
              checked={form.enableImages}
              icon={ImageIcon}
              label="Images"
              onChange={(checked) => setFormField("enableImages", checked)}
            />
            <MediaSwitch
              checked={enableAudio}
              icon={Volume2}
              label="Audio"
              onChange={(checked) => setFormField("enableAudio", checked)}
            />
          </div>

          {form.enableImages ? (
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Image Provider</Label>
                <Select
                  value={form.imageProvider}
                  onValueChange={(value) => {
                    const provider = value as ImageProvider
                    setFormField("imageProvider", provider)
                    setFormField("imageModel", getDefaultImageModel(provider))
                  }}
                >
                <SelectTrigger className="h-10">
                  <SelectValue />
                </SelectTrigger>
                  <SelectContent>
                    {IMAGE_PROVIDER_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Image Model</Label>
                <Select
                  value={form.imageModel}
                  onValueChange={(value) => setFormField("imageModel", value)}
                >
                <SelectTrigger className="h-10">
                  <SelectValue />
                </SelectTrigger>
                  <SelectContent>
                    {IMAGE_MODEL_OPTIONS[form.imageProvider].map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          ) : null}
          <TTSSettings
            enableAudio={enableAudio}
            ttsProvider={form.ttsProvider}
            ttsModel={form.ttsModel}
            language={form.language}
            targetLanguage={form.targetLanguage}
            speaker={form.speaker}
            audioFormat={form.audioFormat}
            detectedLanguage={detectedLanguage}
            isDetecting={isDetecting}
            onChange={(partial) => {
              Object.entries(partial).forEach(([k, v]) => {
                setFormField(k as any, v as any)
              })
            }}
          />
        </div>

        {/* Right column: words + submit */}
        <div className="flex flex-col gap-4">
          <WordsInput
            value={form.rawWords}
            onChange={(v) => setFormField("rawWords", v)}
            error={wordsError}
            mode={inputMode}
            onModeChange={(mode) => {
              setInputMode(mode)
              setWordsError(undefined)
            }}
            onExtract={handleExtractCandidates}
            isExtracting={isExtracting}
          />

          {inputMode === "text" && candidates.length > 0 ? (
            <div className="space-y-3 rounded-md border bg-background p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="text-sm font-medium">Candidate review</div>
                  <div className="text-xs text-muted-foreground">
                    {candidates.filter((candidate) => candidate.selected).length} of{" "}
                    {candidates.length} selected
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      setCandidates((items) =>
                        items.map((item) => ({ ...item, selected: true }))
                      )
                    }
                  >
                    <CheckCheck className="h-3.5 w-3.5" />
                    All
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      setCandidates((items) =>
                        items.map((item, index) => ({
                          ...item,
                          selected: index < 30,
                        }))
                      )
                    }
                  >
                    <CheckCheck className="h-3.5 w-3.5" />
                    Top 30
                  </Button>
                  <Button type="button" size="sm" onClick={applySelectedCandidates}>
                    <Sparkles className="h-3.5 w-3.5" />
                    Use selected
                  </Button>
                </div>
              </div>

              <div className="max-h-[360px] space-y-2 overflow-y-auto pr-1">
                {candidates.map((candidate, index) => (
                  <div
                    key={`${candidate.expression}-${index}`}
                    className="rounded-md border p-2.5"
                  >
                    <div className="flex items-start gap-3">
                      <input
                        type="checkbox"
                        checked={candidate.selected}
                        onChange={(event) =>
                          setCandidates((items) =>
                            items.map((item, itemIndex) =>
                              itemIndex === index
                                ? { ...item, selected: event.target.checked }
                                : item
                            )
                          )
                        }
                        className="mt-1 h-4 w-4 rounded border-input"
                        aria-label={`Select ${candidate.expression}`}
                      />
                      <div className="min-w-0 flex-1 space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-medium">{candidate.expression}</span>
                          <Badge variant="secondary">{candidate.kind}</Badge>
                          <span className="text-xs text-muted-foreground">
                            score {candidate.score.toFixed(1)} - {candidate.frequency}x
                          </span>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {candidate.reason}
                        </div>
                        {candidate.contexts[0] ? (
                          <div className="line-clamp-2 text-xs text-muted-foreground">
                            {candidate.contexts[0]}
                          </div>
                        ) : null}
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() =>
                          setCandidates((items) =>
                            items.filter((_, itemIndex) => itemIndex !== index)
                          )
                        }
                        aria-label={`Remove ${candidate.expression}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          <Button
            type="submit"
            size="lg"
            className="w-full gap-2"
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {isSubmitting ? "Starting generation…" : "Generate Cards"}
          </Button>
        </div>
      </div>
    </form>
  )
}
