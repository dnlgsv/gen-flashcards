import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { FileText, ListChecks, Upload } from "lucide-react"
import { cn } from "@/lib/utils"

export type WordsInputMode = "words" | "text"

interface WordsInputProps {
  value: string
  onChange: (v: string) => void
  error?: string
  mode?: WordsInputMode
  onModeChange?: (mode: WordsInputMode) => void
  onExtract?: () => void
  isExtracting?: boolean
}

function parseWordCount(raw: string): number {
  return raw
    .split(/[\n,]+/)
    .map((w) => w.trim())
    .filter(Boolean).length
}

export function WordsInput({
  value,
  onChange,
  error,
  mode = "words",
  onModeChange,
  onExtract,
  isExtracting = false,
}: WordsInputProps) {
  const count = parseWordCount(value)
  const isTextMode = mode === "text"

  const handleFileUpload = async (file: File | undefined) => {
    if (!file) return
    const text = await file.text()
    onChange(text)
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Label>{isTextMode ? "Source Text" : "Words"}</Label>
        <div className="inline-flex rounded-md border bg-background p-0.5">
          <button
            type="button"
            onClick={() => onModeChange?.("words")}
            className={cn(
              "inline-flex h-8 items-center gap-1.5 rounded px-2.5 text-sm font-medium transition-colors",
              !isTextMode
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:bg-muted"
            )}
          >
            <ListChecks className="h-3.5 w-3.5" />
            Words list
          </button>
          <button
            type="button"
            onClick={() => onModeChange?.("text")}
            className={cn(
              "inline-flex h-8 items-center gap-1.5 rounded px-2.5 text-sm font-medium transition-colors",
              isTextMode
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:bg-muted"
            )}
          >
            <FileText className="h-3.5 w-3.5" />
            Text extraction
          </button>
        </div>
      </div>
      <Textarea
        placeholder={
          isTextMode
            ? "Paste a source text, article excerpt, transcript, or notes. Then extract candidate flashcards."
            : "Enter words, one per line or comma-separated\ne.g. ephemeral, ubiquitous, ameliorate"
        }
        rows={isTextMode ? 12 : 9}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={cn("text-sm leading-6", error && "border-destructive")}
      />
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        {error ? (
          <span className="text-destructive">{error}</span>
        ) : count > 0 && !isTextMode ? (
          <span>{count} word{count !== 1 ? "s" : ""} detected</span>
        ) : isTextMode && value.trim() ? (
          <span>{value.trim().split(/\s+/).length} source words</span>
        ) : null}
        {isTextMode ? (
          <div className="ml-auto flex items-center gap-2">
            <Button asChild type="button" variant="outline" size="sm" className="text-sm">
              <label className="cursor-pointer">
                <Upload className="h-3.5 w-3.5" />
                Upload .txt
                <input
                  type="file"
                  accept=".txt,text/plain"
                  className="sr-only"
                  onChange={(event) => handleFileUpload(event.target.files?.[0])}
                />
              </label>
            </Button>
            <Button
              type="button"
              size="sm"
              className="text-sm"
              onClick={onExtract}
              disabled={isExtracting || !value.trim()}
            >
              <FileText className="h-3.5 w-3.5" />
              {isExtracting ? "Extracting..." : "Extract"}
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  )
}

/** Parse raw textarea content into a clean word list */
export function parseWords(raw: string): string[] {
  const words = raw
    .split(/[\n,]+/)
    .map((w) => w.trim())
    .filter(Boolean)
  return Array.from(new Set(words))
}
