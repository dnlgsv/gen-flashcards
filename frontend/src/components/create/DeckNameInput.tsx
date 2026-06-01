import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

interface DeckNameInputProps {
  value: string
  onChange: (v: string) => void
}

export function DeckNameInput({ value, onChange }: DeckNameInputProps) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor="deck-name">Deck name</Label>
      <Input
        id="deck-name"
        className="h-10"
        placeholder="Vocabulary Deck"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  )
}
