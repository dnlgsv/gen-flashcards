"use client"

import { useState, KeyboardEvent } from "react"
import { X } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"

interface TagInputProps {
  label: string
  values: string[]
  onChange: (values: string[]) => void
  placeholder?: string
  className?: string
}

export function TagInput({
  label,
  values,
  onChange,
  placeholder = "Add…",
  className,
}: TagInputProps) {
  const [inputVal, setInputVal] = useState("")

  const addTag = (raw: string) => {
    const trimmed = raw.trim()
    if (trimmed && !values.includes(trimmed)) {
      onChange([...values, trimmed])
    }
    setInputVal("")
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault()
      addTag(inputVal)
    } else if (e.key === "Backspace" && inputVal === "" && values.length > 0) {
      onChange(values.slice(0, -1))
    }
  }

  const removeTag = (index: number) => {
    onChange(values.filter((_, i) => i !== index))
  }

  return (
    <div className={cn("space-y-1.5", className)}>
      <Label className="text-xs">{label}</Label>
      <div className="flex flex-wrap gap-1 rounded-md border bg-background p-2 min-h-[2.5rem]">
        {values.map((tag, i) => (
          <Badge key={i} variant="secondary" className="gap-1 text-xs pr-1">
            {tag}
            <button
              type="button"
              onClick={() => removeTag(i)}
              className="hover:text-destructive transition-colors"
              aria-label={`Remove ${tag}`}
            >
              <X className="h-3 w-3" />
            </button>
          </Badge>
        ))}
        <input
          className="flex-1 min-w-[80px] outline-none bg-transparent text-xs placeholder:text-muted-foreground"
          placeholder={placeholder}
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={() => { if (inputVal) addTag(inputVal) }}
        />
      </div>
    </div>
  )
}
