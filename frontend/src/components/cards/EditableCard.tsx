"use client"

import { useState, type MouseEvent } from "react"
import { ImageOff, Loader2, RefreshCw, Trash2, Volume2 } from "lucide-react"
import { toast } from "sonner"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { TagInput } from "./TagInput"
import { api } from "@/lib/api"
import { API_BASE } from "@/lib/apiBase"
import { cn } from "@/lib/utils"
import { useGenerationStore } from "@/store/generationStore"
import type { CardInfo } from "@/types"

const PARTS_OF_SPEECH = ["noun", "verb", "adjective", "adverb", "phrase", "other"]
const CEFR_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2", "?"]

interface EditableCardProps {
  card: CardInfo
  onUpdate: (partial: Partial<CardInfo>) => void
  onDelete: () => void
}

function extractAudioFile(tag: string | undefined): string | null {
  if (!tag) return null
  const m = tag.match(/\[sound:(.+?)\]/)
  return m ? m[1] : null
}

function extractImageFile(tag: string | undefined): string | null {
  if (!tag) return null
  const m = tag.match(/src=["']([^"']+)["']/)
  return m ? m[1] : null
}

function AudioButton({ tag }: { tag: string | undefined }) {
  const [playing, setPlaying] = useState(false)
  const file = extractAudioFile(tag)
  if (!file) return null

  const play = (event: MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation()
    if (playing) return
    setPlaying(true)
    const audio = new Audio(`${API_BASE}/static/audio/${encodeURIComponent(file)}`)
    audio.onended = () => setPlaying(false)
    audio.onerror = () => setPlaying(false)
    audio.play().catch(() => setPlaying(false))
  }

  return (
    <button
      onClick={play}
      title={playing ? "Playing…" : `Play: ${file}`}
      className={cn(
        "inline-flex items-center justify-center rounded-full w-6 h-6 shrink-0 transition-colors",
        playing
          ? "text-primary bg-primary/10"
          : "text-muted-foreground hover:text-primary hover:bg-primary/10"
      )}
    >
      {playing ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
      ) : (
        <Volume2 className="h-3.5 w-3.5" />
      )}
    </button>
  )
}

export function EditableCard({ card, onUpdate, onDelete }: EditableCardProps) {
  const [isFlipped, setIsFlipped] = useState(false)
  const [regenerating, setRegenerating] = useState<string | null>(null)
  const form = useGenerationStore((s) => s.form)
  const imageFile = extractImageFile(card.image)

  const toggleSide = () => setIsFlipped((value) => !value)
  const removeImage = () => onUpdate({ image: undefined })
  const isBusy = (key: string) => regenerating === key

  const regenerateTextField = async (field: "definition" | "examples") => {
    if (!form.modelName) {
      toast.error("Select a model before regenerating text")
      return
    }
    setRegenerating(field)
    try {
      const response = await api.regenerateCardField({
        card,
        field,
        model_name: form.modelName,
        learner_level: form.learnerLevel,
        target_language: form.targetLanguage,
      })
      if (field === "examples") {
        onUpdate({
          examples: Array.isArray(response.value)
            ? response.value
            : [response.value].filter(Boolean),
        })
      } else {
        onUpdate({ definition: String(response.value) })
      }
      toast.success(`${field === "examples" ? "Examples" : "Definition"} regenerated`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Regeneration failed")
    } finally {
      setRegenerating(null)
    }
  }

  const regenerateAudio = async (
    sourceField: "expression" | "definition" | "examples",
    audioField: "audio_expression" | "audio_definition" | "audio_examples"
  ) => {
    const text = Array.isArray(card[sourceField])
      ? card[sourceField].filter(Boolean).join("\n")
      : card[sourceField]
    if (!text) {
      toast.error("Nothing to read aloud")
      return
    }
    setRegenerating(audioField)
    try {
      const response = await api.generateTTS({
        text,
        language: form.language === "auto" ? "en" : form.language,
        provider: form.ttsProvider,
        model: form.ttsModel,
        speaker: form.speaker,
        response_format: form.audioFormat,
      })
      onUpdate({ [audioField]: `[sound:${response.filename}]` })
      toast.success("Audio regenerated")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Audio regeneration failed")
    } finally {
      setRegenerating(null)
    }
  }

  const regenerateImage = async () => {
    setRegenerating("image")
    try {
      const response = await api.regenerateCardImage({
        card,
        provider: form.imageProvider,
        model: form.imageModel,
      })
      onUpdate({ image: response.image })
      toast.success("Image regenerated")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Image regeneration failed")
    } finally {
      setRegenerating(null)
    }
  }

  return (
    <div className="bg-[linear-gradient(180deg,rgba(251,245,236,0.72),rgba(255,255,255,0))] px-4 py-4 sm:px-5">
      <div className="mx-auto w-full max-w-4xl">
        <div
          className="perspective-1800 relative grid"
          style={{ filter: isFlipped ? "drop-shadow(0 30px 65px rgba(8,47,73,0.14))" : "drop-shadow(0 28px 60px rgba(120,53,15,0.12))" }}
        >
            <section
              onClick={() => setIsFlipped(true)}
              className={cn(
                "card-face-panel card-face-front col-start-1 row-start-1 flex min-h-[460px] flex-col overflow-hidden rounded-2xl border border-amber-200/80 shadow-[0_18px_48px_rgba(15,23,42,0.11)] backface-hidden",
                isFlipped ? "pointer-events-none" : "cursor-pointer"
              )}
              style={{
                opacity: isFlipped ? 0 : 1,
                transform: isFlipped ? "rotateY(-180deg) scale(0.985)" : "rotateY(0deg) scale(1)",
                zIndex: isFlipped ? 0 : 1,
              }}
            >
              <div className="pointer-events-none absolute inset-0 overflow-hidden">
                <div className="animate-card-float absolute -left-10 top-8 h-28 w-28 rounded-full bg-amber-300/18 blur-3xl" />
                <div className="animate-card-pulse absolute right-10 top-12 h-20 w-20 rounded-full bg-orange-300/18 blur-2xl" />
                <div className="absolute inset-x-0 top-0 h-20 bg-[linear-gradient(180deg,rgba(255,255,255,0.5),transparent)]" />
              </div>

              <div className="relative flex items-start justify-between gap-4 border-b border-amber-200/70 px-4 py-3.5 sm:px-5">
                <div className="min-w-0 space-y-1">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-amber-800/70">
                    Front side
                  </p>
                  <p className="text-sm text-stone-600">
                    Image and description preview
                  </p>
                </div>

                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation()
                    setIsFlipped(true)
                  }}
                  className="inline-flex items-center gap-2 rounded-full border border-amber-300/80 bg-white/85 px-3 py-1.5 text-sm text-amber-900 transition-colors hover:border-amber-400 hover:bg-white"
                >
                  Show back
                </button>
              </div>

              <div className="relative grid flex-1 gap-4 p-4 sm:grid-cols-[minmax(0,1.15fr)_minmax(250px,0.75fr)] sm:p-5">
                <div className="relative flex min-h-[300px] overflow-hidden rounded-2xl border border-amber-200/80 bg-[linear-gradient(145deg,rgba(245,158,11,0.16),rgba(255,255,255,0.98))] shadow-[inset_0_1px_0_rgba(255,255,255,0.9)]">
                  {imageFile ? (
                    <>
                      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_18%,rgba(255,255,255,0.9),transparent_46%)]" />
                      <img
                        src={`${API_BASE}/static/images/${encodeURIComponent(imageFile)}`}
                        alt={card.expression}
                        className="relative h-full max-h-[340px] w-full object-contain p-3 transition-transform duration-500 sm:p-4"
                      />
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation()
                          removeImage()
                        }}
                        className="absolute right-4 top-4 inline-flex items-center gap-2 rounded-full bg-white/95 px-3 py-1.5 text-sm text-stone-700 shadow-sm transition-colors hover:text-destructive"
                      >
                        <ImageOff className="h-3.5 w-3.5" />
                        Remove image
                      </button>
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation()
                          regenerateImage()
                        }}
                        disabled={isBusy("image")}
                        className="absolute left-4 top-4 inline-flex items-center gap-2 rounded-full bg-white/95 px-3 py-1.5 text-sm text-stone-700 shadow-sm transition-colors hover:text-primary disabled:opacity-60"
                      >
                        {isBusy("image") ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <RefreshCw className="h-3.5 w-3.5" />
                        )}
                        Regenerate
                      </button>
                    </>
                  ) : (
                    <div className="flex h-full w-full flex-col items-center justify-center gap-3 px-6 text-center">
                      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-white/90 text-amber-500 shadow-sm">
                        <ImageOff className="h-6 w-6" />
                      </div>
                      <div className="space-y-1.5">
                        <p className="text-sm font-medium text-stone-700">No image on this card</p>
                        <p className="max-w-sm text-sm leading-6 text-muted-foreground">
                          This front side can stay text-only, or you can regenerate visuals later.
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation()
                          regenerateImage()
                        }}
                        disabled={isBusy("image")}
                        className="inline-flex items-center gap-2 rounded-full border border-amber-300/80 bg-white/90 px-3 py-1.5 text-sm text-amber-900 transition-colors hover:border-amber-400 disabled:opacity-60"
                      >
                        {isBusy("image") ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <RefreshCw className="h-3.5 w-3.5" />
                        )}
                        Generate image
                      </button>
                    </div>
                  )}
                </div>

                <div className="flex min-h-[300px] flex-col rounded-2xl border border-amber-200/80 bg-white/70 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.9)]">
                  <div className="space-y-2.5">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-amber-800/70">
                      Description
                    </p>
                    <p className="text-sm leading-6 text-stone-700">
                      {card.definition || "Add a definition on the back side to show a cleaner description here."}
                    </p>
                  </div>

                  <div className="mt-auto border-t border-amber-200/60 pt-4 text-xs leading-5 text-stone-500">
                    Click the card or use the button above to flip to the editable back side.
                  </div>
                </div>
              </div>
            </section>

            <section
              className={cn(
                "card-face-panel card-face-back col-start-1 row-start-1 overflow-hidden rounded-2xl border border-sky-200/80 shadow-[0_18px_48px_rgba(15,23,42,0.11)] backface-hidden",
                !isFlipped && "pointer-events-none"
              )}
              style={{
                opacity: isFlipped ? 1 : 0,
                transform: isFlipped ? "rotateY(0deg) scale(1)" : "rotateY(180deg) scale(0.985)",
                zIndex: isFlipped ? 1 : 0,
              }}
            >
              <div className="relative space-y-3.5 p-4 sm:p-5">
                <div className="pointer-events-none absolute inset-0 overflow-hidden">
                  <div className="animate-card-pulse absolute -right-12 top-10 h-32 w-32 rounded-full bg-sky-300/14 blur-3xl" />
                  <div className="absolute inset-x-0 top-0 h-24 bg-[linear-gradient(180deg,rgba(255,255,255,0.55),transparent)]" />
                </div>

                <div className="space-y-2">
                  <div className="relative flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0 space-y-1">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-sky-900/60">
                        Back side
                      </p>
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="truncate text-2xl font-bold tracking-tight leading-none">
                          {card.expression}
                        </span>
                        <AudioButton tag={card.audio_expression} />
                        <button
                          type="button"
                          onClick={() => regenerateAudio("expression", "audio_expression")}
                          disabled={isBusy("audio_expression")}
                          className="inline-flex items-center gap-1 rounded-full border border-sky-200/80 bg-white/75 px-2 py-1 text-xs text-slate-700 transition-colors hover:text-primary disabled:opacity-60"
                        >
                          {isBusy("audio_expression") ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <RefreshCw className="h-3 w-3" />
                          )}
                          Audio
                        </button>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2 shrink-0 pt-0.5">
                      <Select
                        value={card.part_of_speech || "other"}
                        onValueChange={(v) => onUpdate({ part_of_speech: v === "other" ? "" : v })}
                      >
                        <SelectTrigger className="h-8 w-28 border-sky-200/70 bg-white/90 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {PARTS_OF_SPEECH.map((pos) => (
                            <SelectItem key={pos} value={pos} className="text-xs">
                              {pos}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Select
                        value={card.cefr_level || "?"}
                        onValueChange={(v) => onUpdate({ cefr_level: v === "?" ? "" : v })}
                      >
                        <SelectTrigger className="h-8 w-16 border-sky-200/70 bg-white/90 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {CEFR_LEVELS.map((lvl) => (
                            <SelectItem key={lvl} value={lvl} className="text-xs">
                              {lvl}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>

                      {imageFile && (
                        <button
                          type="button"
                          onClick={removeImage}
                          className="inline-flex items-center gap-1.5 rounded-full border border-sky-200/80 bg-white/75 px-3 py-1.5 text-xs text-slate-700 transition-colors hover:border-destructive/40 hover:text-destructive"
                        >
                          <ImageOff className="h-3.5 w-3.5" />
                          Remove image
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={toggleSide}
                        className="inline-flex items-center gap-1.5 rounded-full border border-sky-300/80 bg-sky-900 px-3 py-1.5 text-xs text-white transition-colors hover:bg-sky-800"
                      >
                        Show front
                      </button>

                      <button
                        type="button"
                        onClick={onDelete}
                        className="inline-flex items-center gap-1 text-xs text-destructive/70 transition-colors hover:text-destructive"
                      >
                        <Trash2 className="h-3 w-3" />
                        Delete card
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-muted-foreground shrink-0">Base form</span>
                    <Input
                      value={card.original_form}
                      onChange={(e) => onUpdate({ original_form: e.target.value })}
                      className="h-6 w-40 rounded-none border-0 border-b border-sky-200 bg-transparent px-0 text-xs shadow-none focus-visible:border-sky-500 focus-visible:ring-0"
                    />
                  </div>
                </div>

                <div className="border-t border-sky-100" />

                <div className="relative space-y-1">
                  <div className="flex items-center gap-1">
                    <Label className="text-xs">Definition</Label>
                    <AudioButton tag={card.audio_definition} />
                    <button
                      type="button"
                      onClick={() => regenerateAudio("definition", "audio_definition")}
                      disabled={isBusy("audio_definition")}
                      className="inline-flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-primary disabled:opacity-60"
                    >
                      {isBusy("audio_definition") ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <RefreshCw className="h-3 w-3" />
                      )}
                      Audio
                    </button>
                    <button
                      type="button"
                      onClick={() => regenerateTextField("definition")}
                      disabled={isBusy("definition")}
                      className="inline-flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-primary disabled:opacity-60"
                    >
                      {isBusy("definition") ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <RefreshCw className="h-3 w-3" />
                      )}
                      Text
                    </button>
                  </div>
                  <Textarea
                    rows={2}
                    className="resize-none border-sky-200/70 bg-white/92 text-sm"
                    value={card.definition}
                    onChange={(e) => onUpdate({ definition: e.target.value })}
                  />
                </div>

                <div className="relative space-y-1">
                  <div className="flex items-center gap-1">
                    <Label className="text-xs">Examples</Label>
                    <AudioButton tag={card.audio_examples} />
                    <button
                      type="button"
                      onClick={() => regenerateAudio("examples", "audio_examples")}
                      disabled={isBusy("audio_examples")}
                      className="inline-flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-primary disabled:opacity-60"
                    >
                      {isBusy("audio_examples") ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <RefreshCw className="h-3 w-3" />
                      )}
                      Audio
                    </button>
                    <button
                      type="button"
                      onClick={() => regenerateTextField("examples")}
                      disabled={isBusy("examples")}
                      className="inline-flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-primary disabled:opacity-60"
                    >
                      {isBusy("examples") ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <RefreshCw className="h-3 w-3" />
                      )}
                      Text
                    </button>
                  </div>
                  <Textarea
                    rows={3}
                    className="resize-none border-sky-200/70 bg-white/92 text-sm"
                    value={card.examples.join("\n")}
                    onChange={(e) => onUpdate({ examples: e.target.value.split("\n") })}
                    onBlur={(e) => onUpdate({ examples: e.target.value.split("\n").filter(Boolean) })}
                    placeholder="One example per line…"
                  />
                </div>

                <TagInput
                  label="Translations"
                  values={card.translations}
                  onChange={(v) => onUpdate({ translations: v })}
                  placeholder="Add translation…"
                />

                <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                  <TagInput
                    label="Synonyms"
                    values={card.synonyms}
                    onChange={(v) => onUpdate({ synonyms: v })}
                    placeholder="Add synonym…"
                  />
                  <TagInput
                    label="Antonyms"
                    values={card.antonyms}
                    onChange={(v) => onUpdate({ antonyms: v })}
                    placeholder="Add antonym…"
                  />
                  <TagInput
                    label="Collocations"
                    values={card.collocations}
                    onChange={(v) => onUpdate({ collocations: v })}
                    placeholder="Add collocation…"
                  />
                </div>

                <TagInput
                  label="Topics"
                  values={card.topics}
                  onChange={(v) => onUpdate({ topics: v })}
                  placeholder="Add topic…"
                />

                {imageFile && (
                  <div className="space-y-2 rounded-2xl border border-sky-100 bg-white/65 p-3">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-xs font-medium">Image</span>
                      <button
                        type="button"
                        onClick={removeImage}
                        className="inline-flex items-center gap-1.5 text-xs text-destructive/70 transition-colors hover:text-destructive"
                      >
                        <ImageOff className="h-3.5 w-3.5" />
                        Remove image
                      </button>
                      <button
                        type="button"
                        onClick={regenerateImage}
                        disabled={isBusy("image")}
                        className="inline-flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-primary disabled:opacity-60"
                      >
                        {isBusy("image") ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <RefreshCw className="h-3.5 w-3.5" />
                        )}
                        Regenerate
                      </button>
                    </div>
                    <img
                      src={`${API_BASE}/static/images/${encodeURIComponent(imageFile)}`}
                      alt={card.expression}
                      className="max-h-72 w-full rounded-xl border border-sky-100 bg-white object-contain p-2"
                    />
                  </div>
                )}
              </div>
            </section>
        </div>
      </div>
    </div>
  )
}
