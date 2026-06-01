import { Loader2, CheckCircle, AlertCircle } from "lucide-react"
import type { TaskStatus } from "@/types"

interface GenerationStatusProps {
  status: TaskStatus | "idle"
  processed: number
  total: number
  error?: string | null
  currentWord?: string
}

const STATUS_CONFIG = {
  idle:      { icon: Loader2, color: "text-muted-foreground", spin: false, label: "Preparing" },
  pending:   { icon: Loader2, color: "text-amber-500",        spin: true,  label: "In queue" },
  running:   { icon: Loader2, color: "text-blue-500",         spin: true,  label: "Creating cards..." },
  completed: { icon: CheckCircle, color: "text-green-600",    spin: false, label: "Ready" },
  failed:    { icon: AlertCircle, color: "text-destructive",  spin: false, label: "Failed" },
}

export function GenerationStatus({
  status,
  processed,
  total,
  error,
  currentWord,
}: GenerationStatusProps) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.idle
  const Icon = cfg.icon

  const label =
    status === "running" && total > 0
      ? currentWord
        ? `In progress: ${currentWord}`
        : `Creating card ${processed} of ${total}`
      : status === "completed"
      ? `${processed} card${processed !== 1 ? "s" : ""} created`
      : cfg.label

  return (
    <div className="flex items-center gap-3 rounded-xl border bg-background/90 px-4 py-3">
      <Icon className={`h-4 w-4 shrink-0 ${cfg.color} ${cfg.spin ? "animate-spin" : ""}`} />
      <div className="flex-1 min-w-0 text-left">
        <p className="text-sm font-medium tracking-tight truncate">{label}</p>
        {status === "failed" && error && (
          <p className="text-xs text-destructive mt-0.5 truncate">{error}</p>
        )}
      </div>
    </div>
  )
}
