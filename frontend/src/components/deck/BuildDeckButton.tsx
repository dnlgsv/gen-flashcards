"use client"

import { useState } from "react"
import { AlertTriangle, Loader2, Package } from "lucide-react"
import { toast } from "sonner"
import { useMutation } from "@tanstack/react-query"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"
import { useGenerationStore } from "@/store/generationStore"
import type { CardInfo, CardType } from "@/types"

interface BuildDeckButtonProps {
  cards: CardInfo[]
  deckName: string
}

const CARD_TYPE_OPTIONS: { value: CardType; label: string }[] = [
  { value: "recognition", label: "Recognition" },
  { value: "reverse", label: "Reverse" },
  { value: "production", label: "Production" },
  { value: "cloze", label: "Cloze" },
]

function getDuplicateExpressions(cards: CardInfo[]): string[] {
  const seen = new Set<string>()
  const duplicates = new Set<string>()

  cards.forEach((card) => {
    const expression = card.expression.trim()
    if (!expression) return
    const key = expression.toLocaleLowerCase()
    if (seen.has(key)) {
      duplicates.add(expression)
    } else {
      seen.add(key)
    }
  })

  return Array.from(duplicates).sort((a, b) => a.localeCompare(b))
}

export function BuildDeckButton({ cards, deckName }: BuildDeckButtonProps) {
  const setBuiltDeck = useGenerationStore((s) => s.setBuiltDeck)
  const setViewStatus = useGenerationStore((s) => s.setViewStatus)
  const taskId = useGenerationStore((s) => s.taskId)
  const [cardTypes, setCardTypes] = useState<CardType[]>(["recognition"])
  const duplicateExpressions = getDuplicateExpressions(cards)
  const hasDuplicates = duplicateExpressions.length > 0

  const toggleCardType = (cardType: CardType) => {
    setCardTypes((current) => {
      if (current.includes(cardType)) {
        return current.length === 1
          ? current
          : current.filter((item) => item !== cardType)
      }
      return [...current, cardType]
    })
  }

  const { mutate, isPending } = useMutation({
    mutationFn: () =>
      api.buildDeck({
        cards_data: cards,
        deck_name: deckName,
        card_types: cardTypes,
        task_id: taskId ?? undefined,
      }),
    onSuccess: (resp) => {
      setBuiltDeck(resp)
      setViewStatus("done")
      toast.success(`Deck "${resp.deck_name}" ready - ${resp.card_count} cards`)
    },
    onError: (err) => {
      const msg = err instanceof Error ? err.message : "Failed to build deck"
      toast.error(msg)
    },
  })

  return (
    <div className="flex items-center gap-3">
      {hasDuplicates && (
        <Badge
          variant="outline"
          className="gap-1 border-amber-300 bg-amber-50 text-amber-800"
          title={`Duplicate cards: ${duplicateExpressions.join(", ")}`}
        >
          <AlertTriangle className="h-3.5 w-3.5" />
          {duplicateExpressions.length} duplicate
          {duplicateExpressions.length === 1 ? "" : "s"}
        </Badge>
      )}
      <div className="flex items-center gap-2">
        {CARD_TYPE_OPTIONS.map((option) => (
          <label
            key={option.value}
            className="flex items-center gap-1.5 text-sm text-muted-foreground"
          >
            <input
              type="checkbox"
              checked={cardTypes.includes(option.value)}
              onChange={() => toggleCardType(option.value)}
              className="h-3.5 w-3.5"
            />
            {option.label}
          </label>
        ))}
      </div>
      <Button
        onClick={() => mutate()}
        disabled={isPending || cards.length === 0 || hasDuplicates}
        className="gap-2"
      >
        {isPending ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Package className="h-4 w-4" />
        )}
        {isPending ? "Building deck..." : "Build Deck"}
      </Button>
    </div>
  )
}
