import { Download } from "lucide-react"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"

interface DownloadButtonProps {
  filename: string
  cardCount: number
}

export function DownloadButton({ filename, cardCount }: DownloadButtonProps) {
  const url = api.getDeckDownloadUrl(filename)

  return (
    <Button asChild size="lg" className="gap-2">
      <a href={url} download={filename}>
        <Download className="h-4 w-4" />
        Download {filename} ({cardCount} card{cardCount !== 1 ? "s" : ""})
      </a>
    </Button>
  )
}
