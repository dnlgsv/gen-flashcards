"use client"

import { useEffect, useRef } from "react"
import { api } from "@/lib/api"
import { useGenerationStore } from "@/store/generationStore"
import type { SSEEventType } from "@/types"

const ALL_EVENTS: SSEEventType[] = [
  "word_start",
  "word_complete",
  "word_error",
  "complete",
  "failed",
]

/**
 * Opens an SSE connection to the backend and feeds events into the
 * Zustand store. Uses named addEventListener (NOT onmessage) because
 * the backend sends named events ("event: word_complete").
 *
 * createSSEConnection is async (it fetches the JWT token), so mount and
 * cleanup use a cancelled flag to prevent race conditions.
 *
 * @param taskId - the generation task ID
 * @param active - controls whether SSE should be live; pass false to
 *                 prevent reconnection after completion
 */
export function useSSE(taskId: string | null, active: boolean) {
  const esRef = useRef<EventSource | null>(null)

  const addCard = useGenerationStore((s) => s.addCard)
  const pushEvent = useGenerationStore((s) => s.pushEvent)
  const setViewStatus = useGenerationStore((s) => s.setViewStatus)
  const setError = useGenerationStore((s) => s.setError)
  const markTaskFailed = useGenerationStore((s) => s.markTaskFailed)

  useEffect(() => {
    if (!taskId || !active) return
    if (typeof window === "undefined") return

    let cancelled = false

    api.createSSEConnection(taskId).then((es) => {
      // Component may have unmounted while we were awaiting the token
      if (cancelled) {
        es.close()
        return
      }

      esRef.current = es

      type Handler = (e: Event) => void

      const handlers: Record<string, Handler> = {
        word_start: (e: Event) => {
          const ev = e as MessageEvent
          const parsed = JSON.parse(ev.data as string)
          pushEvent({ type: "word_start", ...parsed })
        },

        word_complete: (e: Event) => {
          const ev = e as MessageEvent
          const parsed = JSON.parse(ev.data as string)
          pushEvent({ type: "word_complete", ...parsed })
          if (parsed?.data?.card) {
            addCard(parsed.data.card)
          }
        },

        word_error: (e: Event) => {
          const ev = e as MessageEvent
          const parsed = JSON.parse(ev.data as string)
          pushEvent({ type: "word_error", ...parsed })
        },

        complete: (e: Event) => {
          const ev = e as MessageEvent
          const parsed = JSON.parse(ev.data as string)
          pushEvent({ type: "complete", ...parsed })
          setViewStatus("reviewing")
          es.close()
        },

        failed: (e: Event) => {
          const ev = e as MessageEvent
          const parsed = JSON.parse(ev.data as string)
          pushEvent({ type: "failed", ...parsed })
          markTaskFailed(taskId)
          setError(parsed?.error ?? "Generation failed")
          setViewStatus("error")
          es.close()
        },
      }

      ALL_EVENTS.forEach((evType) => {
        es.addEventListener(evType, handlers[evType])
      })

      // onerror fires on connection drop. EventSource auto-reconnects via
      // the "retry: 2000" directive from the backend. We only handle
      // permanent closure (CLOSED state).
      es.onerror = () => {
        if (es.readyState === EventSource.CLOSED) {
          setError("SSE connection closed unexpectedly")
          setViewStatus("error")
        }
      }
    })

    return () => {
      cancelled = true
      if (esRef.current) {
        esRef.current.close()
        esRef.current = null
      }
    }
  }, [taskId, active])
}
