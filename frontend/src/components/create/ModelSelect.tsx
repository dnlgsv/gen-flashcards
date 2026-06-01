import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Label } from "@/components/ui/label"
import type { ModelInfo } from "@/types"

interface ModelSelectProps {
  value: string
  onChange: (path: string) => void
  models: ModelInfo[]
  isLoading: boolean
}

const PROVIDER_LABELS: Record<string, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  gemini: "Gemini",
  xai: "xAI",
  deepseek: "DeepSeek",
}

export function ModelSelect({ value, onChange, models, isLoading }: ModelSelectProps) {
  const localModels = models.filter((m) => m.provider === "local")
  const apiModels = models.filter((m) => m.provider !== "local")
  const apiProviders = Array.from(new Set(apiModels.map((m) => m.provider)))

  if (isLoading) {
    return (
      <div className="space-y-1.5">
        <Label>Model</Label>
        <Skeleton className="h-10 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-1.5">
      <Label>Model</Label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="h-10">
          <SelectValue placeholder="Select a model…" />
        </SelectTrigger>
        <SelectContent>
          {localModels.length > 0 && (
            <SelectGroup>
              <SelectLabel>Local models</SelectLabel>
              {localModels.map((m) => (
                <SelectItem key={m.path} value={m.path}>
                  <span className="flex items-center gap-2">
                    {m.name}
                    {m.loaded && (
                      <Badge variant="outline" className="text-xs px-1 py-0">
                        loaded
                      </Badge>
                    )}
                  </span>
                </SelectItem>
              ))}
            </SelectGroup>
          )}
          {apiProviders.map((provider) => (
            <SelectGroup key={provider}>
              <SelectLabel>{PROVIDER_LABELS[provider] ?? provider}</SelectLabel>
              {apiModels
                .filter((m) => m.provider === provider)
                .map((m) => (
                  <SelectItem key={m.path} value={m.path}>
                    {m.name}
                  </SelectItem>
                ))}
            </SelectGroup>
          ))}
          {models.length === 0 && (
            <SelectItem value="__none__" disabled>
              No models available
            </SelectItem>
          )}
        </SelectContent>
      </Select>
    </div>
  )
}
