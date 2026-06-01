import { Progress } from "@/components/ui/progress"

interface ProgressBarProps {
  pct: number
  label?: string
}

export function ProgressBar({ pct, label }: ProgressBarProps) {
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs text-muted-foreground/90">
        <span>{label ?? "Progress"}</span>
        <span className="tabular-nums">{Math.round(pct)}%</span>
      </div>
      <Progress value={pct} className="h-1.5 rounded-full" />
    </div>
  )
}
