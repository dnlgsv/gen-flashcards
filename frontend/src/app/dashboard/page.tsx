"use client"

import { useRef, useState } from "react"
import Link from "next/link"
import {
  ChevronLeft,
  ChevronRight,
  Download,
  Loader2,
  RotateCcw,
  Trash2,
  Upload,
} from "lucide-react"
import { toast } from "sonner"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { EditableCard } from "@/components/cards/EditableCard"
import { BuildDeckButton } from "@/components/deck/BuildDeckButton"
import { DownloadButton } from "@/components/deck/DownloadButton"
import { useGenerationStore } from "@/store/generationStore"
import { api } from "@/lib/api"
import type { CardInfo, DeckHistoryItem } from "@/types"

const STATUS_LABELS: Record<DeckHistoryItem["status"], string> = {
  generating: "Generating",
  ready: "Ready",
  failed: "Failed",
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value))
}

function statusClass(status: DeckHistoryItem["status"]): string {
  if (status === "ready") return "border-emerald-200 bg-emerald-50 text-emerald-700"
  if (status === "failed") return "border-red-200 bg-red-50 text-red-700"
  return "border-sky-200 bg-sky-50 text-sky-700"
}

function ImportedDeckEditor({
  deckName,
  cards,
  onBack,
}: {
  deckName: string
  cards: CardInfo[]
  onBack: () => void
}) {
  const selectedCardIndex = useGenerationStore((s) => s.selectedCardIndex)
  const setSelectedCardIndex = useGenerationStore((s) => s.setSelectedCardIndex)
  const updateCard = useGenerationStore((s) => s.updateCard)
  const deleteCard = useGenerationStore((s) => s.deleteCard)
  const builtDeck = useGenerationStore((s) => s.builtDeck)
  const viewStatus = useGenerationStore((s) => s.viewStatus)
  const selectedCard = cards[selectedCardIndex] ?? null

  return (
    <div className="flex flex-col">
      <div className="sticky top-14 z-10 flex items-center gap-4 border-b bg-background px-6 py-2">
        <Button variant="outline" size="sm" onClick={onBack}>
          Back
        </Button>
        <div className="min-w-0">
          <h1 className="truncate font-semibold">{deckName}</h1>
          <p className="text-xs text-muted-foreground">Imported from .apkg</p>
        </div>
        {cards.length > 0 && (
          <div className="flex items-center gap-1 text-sm text-muted-foreground">
            <button
              onClick={() => setSelectedCardIndex(Math.max(0, selectedCardIndex - 1))}
              disabled={selectedCardIndex === 0}
              className="inline-flex h-7 w-7 items-center justify-center rounded hover:bg-muted disabled:opacity-30"
              title="Previous"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="tabular-nums">
              {selectedCardIndex + 1} / {cards.length}
            </span>
            <button
              onClick={() =>
                setSelectedCardIndex(Math.min(cards.length - 1, selectedCardIndex + 1))
              }
              disabled={selectedCardIndex >= cards.length - 1}
              className="inline-flex h-7 w-7 items-center justify-center rounded hover:bg-muted disabled:opacity-30"
              title="Next"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}
        <div className="flex-1" />
        {viewStatus === "done" && builtDeck ? (
          <DownloadButton
            filename={builtDeck.filename}
            cardCount={builtDeck.card_count}
          />
        ) : (
          <BuildDeckButton cards={cards} deckName={deckName} />
        )}
      </div>

      {selectedCard ? (
        <EditableCard
          card={selectedCard}
          onUpdate={(partial) => updateCard(selectedCardIndex, partial)}
          onDelete={() => deleteCard(selectedCardIndex)}
        />
      ) : (
        <div className="py-16 text-center text-muted-foreground">
          No cards in this deck.
        </div>
      )}
    </div>
  )
}

export default function DashboardPage() {
  const deckHistory = useGenerationStore((s) => s.deckHistory)
  const clearDeckHistory = useGenerationStore((s) => s.clearDeckHistory)
  const cards = useGenerationStore((s) => s.cards)
  const reset = useGenerationStore((s) => s.reset)
  const setCards = useGenerationStore((s) => s.setCards)
  const setFormField = useGenerationStore((s) => s.setFormField)
  const setSelectedCardIndex = useGenerationStore((s) => s.setSelectedCardIndex)
  const setViewStatus = useGenerationStore((s) => s.setViewStatus)
  const [importedDeckName, setImportedDeckName] = useState<string | null>(null)
  const [isImporting, setIsImporting] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const importDeck = async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".apkg")) {
      toast.error("Choose an .apkg file")
      return
    }
    setIsImporting(true)
    try {
      const imported = await api.importDeck(file)
      reset()
      setCards(imported.cards)
      setFormField("deckName", imported.deck_name)
      setSelectedCardIndex(0)
      setViewStatus("reviewing")
      setImportedDeckName(imported.deck_name)
      toast.success(`Imported ${imported.card_count} card${imported.card_count === 1 ? "" : "s"}`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to import deck")
    } finally {
      setIsImporting(false)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  if (importedDeckName) {
    return (
      <ImportedDeckEditor
        deckName={importedDeckName}
        cards={cards}
        onBack={() => {
          reset()
          setImportedDeckName(null)
        }}
      />
    )
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <div className="mb-8 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">My Decks</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Local deck history saved in this browser
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".apkg"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) void importDeck(file)
            }}
          />
          <Button
            variant="outline"
            onClick={() => fileInputRef.current?.click()}
            disabled={isImporting}
            className="gap-2"
          >
            {isImporting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            Import .apkg
          </Button>
          {deckHistory.length > 0 && (
            <Button variant="outline" onClick={clearDeckHistory} className="gap-2">
              <Trash2 className="h-4 w-4" />
              Clear
            </Button>
          )}
          <Button asChild>
            <Link href="/create">New Deck</Link>
          </Button>
        </div>
      </div>

      {deckHistory.length === 0 ? (
        <div className="py-16 text-center text-muted-foreground">
          <p className="mb-4">No deck history yet.</p>
          <Button asChild variant="outline">
            <Link href="/create">Create your first deck</Link>
          </Button>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <div className="grid min-w-[760px] grid-cols-[minmax(0,1fr)_110px_110px_140px_120px] gap-4 border-b bg-muted/40 px-4 py-3 text-xs font-medium uppercase text-muted-foreground">
            <span>Deck</span>
            <span>Status</span>
            <span>Cards</span>
            <span>Updated</span>
            <span className="text-right">Action</span>
          </div>
          <div className="divide-y">
            {deckHistory.map((item) => (
              <div
                key={item.task_id}
                className="grid min-w-[760px] grid-cols-[minmax(0,1fr)_110px_110px_140px_120px] items-center gap-4 px-4 py-4"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium">{item.deck_name}</p>
                  <p className="text-sm text-muted-foreground">
                    {item.word_count} source word{item.word_count === 1 ? "" : "s"}
                  </p>
                </div>
                <Badge variant="outline" className={statusClass(item.status)}>
                  {STATUS_LABELS[item.status]}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  {item.card_count || "-"}
                </span>
                <span className="text-sm text-muted-foreground">
                  {formatDate(item.updated_at)}
                </span>
                <div className="flex justify-end">
                  {item.status === "ready" && item.filename ? (
                    <Button variant="outline" size="sm" asChild className="gap-2">
                      <a
                        href={api.getDeckDownloadUrl(item.filename)}
                        download={item.filename}
                      >
                        <Download className="h-4 w-4" />
                        Download
                      </a>
                    </Button>
                  ) : (
                    <Button variant="outline" size="sm" asChild className="gap-2">
                      <Link href={`/create?task=${item.task_id}`}>
                        <RotateCcw className="h-4 w-4" />
                        Open
                      </Link>
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
