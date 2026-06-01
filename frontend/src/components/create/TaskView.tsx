"use client"

import { useEffect, useCallback, useState, useRef } from "react"
import Link from "next/link"
import { Loader2, ChevronLeft, ChevronRight, Search } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { GenerationStatus } from "@/components/progress/GenerationStatus"
import { ProgressBar } from "@/components/progress/ProgressBar"
import { EditableCard } from "@/components/cards/EditableCard"
import { BuildDeckButton } from "@/components/deck/BuildDeckButton"
import { DownloadButton } from "@/components/deck/DownloadButton"
import { useSSE } from "@/hooks/useSSE"
import { useGenerationStore } from "@/store/generationStore"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"

interface PageProps {
  taskId: string
}

/** Editable index input: shows current 1-based position, allows typing a number to jump */
function CardIndexInput({
  index,
  total,
  onChange,
}: {
  index: number
  total: number
  onChange: (i: number) => void
}) {
  const [draft, setDraft] = useState(String(index + 1))
  const [focused, setFocused] = useState(false)

  // Keep in sync when navigating externally
  useEffect(() => {
    if (!focused) setDraft(String(index + 1))
  }, [index, focused])

  const commit = (raw: string) => {
    setFocused(false)
    const n = parseInt(raw, 10)
    if (!isNaN(n) && n >= 1 && n <= total) {
      onChange(n - 1)
    } else {
      setDraft(String(index + 1))
    }
  }

  return (
    <input
      type="text"
      inputMode="numeric"
      value={draft}
      onFocus={(e) => { setFocused(true); e.currentTarget.select() }}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={(e) => commit(e.target.value)}
      onKeyDown={(e) => { if (e.key === "Enter") e.currentTarget.blur() }}
      className="w-9 text-center text-sm tabular-nums bg-transparent border-b border-input focus:border-primary outline-none transition-colors"
    />
  )
}

export function TaskView({ taskId: routeTaskId }: PageProps) {

  const {
    taskId: storeTaskId,
    viewStatus,
    cards,
    selectedCardIndex,
    processed,
    total,
    events,
    error,
    builtDeck,
    form,
    setTaskId,
    setViewStatus,
    setCards,
    setError,
    setSelectedCardIndex,
    updateCard,
    deleteCard,
  } = useGenerationStore()

  const [searchQuery, setSearchQuery] = useState("")
  const [searchOpen, setSearchOpen] = useState(false)
  const searchRef = useRef<HTMLDivElement>(null)

  // On mount: determine view state from stored or fetched task status
  useEffect(() => {
    if (storeTaskId === routeTaskId && viewStatus !== "idle" && viewStatus !== "loading") {
      if (viewStatus === "reviewing" || viewStatus === "done" || viewStatus === "error") return
    }

    setTaskId(routeTaskId)
    setViewStatus("loading")

    api
      .getTaskStatus(routeTaskId)
      .then((status) => {
        if (status.status === "completed" && status.result) {
          setCards(status.result)
          setViewStatus("reviewing")
        } else if (status.status === "failed") {
          setError(status.error ?? "Generation failed")
          setViewStatus("error")
        } else {
          setViewStatus("streaming")
        }
      })
      .catch((err: Error) => {
        setError(err.message)
        setViewStatus("error")
      })
  }, [routeTaskId])

  // SSE is active only while streaming
  useSSE(routeTaskId, viewStatus === "streaming")

  // Keyboard navigation between cards
  const goToPrev = useCallback(() => {
    setSelectedCardIndex(Math.max(0, selectedCardIndex - 1))
  }, [selectedCardIndex, setSelectedCardIndex])

  const goToNext = useCallback(() => {
    setSelectedCardIndex(Math.min(cards.length - 1, selectedCardIndex + 1))
  }, [selectedCardIndex, cards.length, setSelectedCardIndex])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      if (e.key === "ArrowLeft") goToPrev()
      if (e.key === "ArrowRight") goToNext()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [goToPrev, goToNext])

  // Search results (max 8)
  const searchResults = searchQuery.trim()
    ? cards
        .map((card, i) => ({ card, i }))
        .filter(({ card }) =>
          card.expression.toLowerCase().includes(searchQuery.toLowerCase())
        )
        .slice(0, 8)
    : []

  // ─── Loading ────────────────────────────────────────────────────────────────
  if (viewStatus === "loading") {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-muted-foreground">Loading task…</p>
      </div>
    )
  }

  // ─── Error ──────────────────────────────────────────────────────────────────
  if (viewStatus === "error") {
    return (
      <div className="max-w-xl mx-auto px-4 py-16 space-y-6">
        <Alert variant="destructive">
          <AlertDescription>{error ?? "An unknown error occurred."}</AlertDescription>
        </Alert>
        <div className="flex gap-3">
          <Button asChild>
            <Link href="/create">Try again</Link>
          </Button>
          <Button variant="outline" onClick={() => window.location.reload()}>
            Reload
          </Button>
        </div>
      </div>
    )
  }

  // ─── Streaming ───────────────────────────────────────────────────────────────
  if (viewStatus === "streaming" || viewStatus === "idle") {
    const pct = total > 0 ? (processed / total) * 100 : 0
    const currentWordEvent = events
      .filter((e) => e.type === "word_start" || e.type === "word_complete" || e.type === "word_error")
      .pop()
    const currentWord = currentWordEvent?.type === "word_start"
      ? currentWordEvent?.data?.word
      : undefined

    return (
      <div className="max-w-md mx-auto px-4 py-20 flex flex-col items-center justify-center text-center">
        <div className="space-y-8 w-full">
          <h1 className="text-3xl font-semibold tracking-tight">Generating cards</h1>
          <div className="space-y-4 w-full px-4">
            <GenerationStatus
              status={total > 0 ? "running" : "pending"}
              processed={processed}
              total={total}
              currentWord={currentWord}
            />
            {total > 0 && (
              <ProgressBar pct={pct} label={`${processed} / ${total} words`} />
            )}
          </div>
        </div>
      </div>
    )
  }

  // ─── Reviewing / Building / Done ──────────────────────────────────────────
  const selectedCard = cards[selectedCardIndex] ?? null

  return (
    <div className="flex flex-col">
      {/* Top bar */}
      <div className="sticky top-14 z-10 bg-background border-b px-6 py-2 flex items-center gap-4 shrink-0">

        {/* Left: title */}
        <h1 className="font-semibold shrink-0">Review cards</h1>

        {/* Navigation: ← [index] / total → */}
        {cards.length > 0 && (
          <div className="flex items-center gap-0.5 shrink-0">
            <button
              onClick={goToPrev}
              disabled={selectedCardIndex === 0}
              className="inline-flex items-center justify-center rounded w-7 h-7 hover:bg-muted disabled:opacity-30 transition-colors"
              title="Previous (←)"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <div className="flex items-center gap-1 text-sm text-muted-foreground px-1">
              <CardIndexInput
                index={selectedCardIndex}
                total={cards.length}
                onChange={setSelectedCardIndex}
              />
              <span>/ {cards.length}</span>
            </div>
            <button
              onClick={goToNext}
              disabled={selectedCardIndex === cards.length - 1}
              className="inline-flex items-center justify-center rounded w-7 h-7 hover:bg-muted disabled:opacity-30 transition-colors"
              title="Next (→)"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Search with dropdown */}
        <div ref={searchRef} className="relative w-52">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setSearchOpen(true) }}
            onFocus={() => setSearchOpen(true)}
            onBlur={() => setTimeout(() => setSearchOpen(false), 150)}
            placeholder="Search cards…"
            className="w-full h-8 rounded-md border bg-background pl-8 pr-3 text-sm outline-none focus:border-primary transition-colors placeholder:text-muted-foreground"
          />
          {searchOpen && searchResults.length > 0 && (
            <div className="absolute top-full mt-1 left-0 z-50 w-64 rounded-md border bg-popover shadow-md overflow-hidden">
              {searchResults.map(({ card, i }) => (
                <button
                  key={i}
                  onMouseDown={() => {
                    setSelectedCardIndex(i)
                    setSearchQuery("")
                    setSearchOpen(false)
                  }}
                  className={cn(
                    "w-full text-left px-3 py-2 text-sm hover:bg-muted transition-colors flex items-center justify-between gap-2",
                    i === selectedCardIndex && "bg-primary/8 font-medium"
                  )}
                >
                  <span className="truncate">{card.expression}</span>
                  <span className="text-xs text-muted-foreground shrink-0">#{i + 1}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Action */}
        <div className="flex items-center gap-3 shrink-0">
          {viewStatus === "done" && builtDeck ? (
            <DownloadButton
              filename={builtDeck.filename}
              cardCount={builtDeck.card_count}
            />
          ) : (
            <BuildDeckButton
              cards={cards}
              deckName={form.deckName || "Vocabulary Deck"}
            />
          )}
        </div>
      </div>

      {/* Main content — full width card editor */}
      <div>
        {selectedCard ? (
          <EditableCard
            card={selectedCard}
            onUpdate={(partial) => updateCard(selectedCardIndex, partial)}
            onDelete={() => deleteCard(selectedCardIndex)}
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-sm text-muted-foreground">No cards yet.</p>
          </div>
        )}
      </div>
    </div>
  )
}
