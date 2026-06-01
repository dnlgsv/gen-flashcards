import { create } from "zustand"
import { createJSONStorage, persist } from "zustand/middleware"
import type {
  BuildDeckResponse,
  CardInfo,
  DeckHistoryItem,
  FormState,
  SSEEventRecord,
  TaskStatus,
  ViewStatus,
} from "@/types"
import {
  getDefaultImageModel,
  getDefaultTTSModel,
  getDefaultTTSVoice,
} from "@/lib/mediaCatalog"

// ─── Default form values ──────────────────────────────────────────────────────

const defaultForm: FormState = {
  rawWords: "",
  modelName: "",
  deckName: "Vocabulary Deck",
  ttsProvider: "qwen3",
  ttsModel: getDefaultTTSModel("qwen3"),
  language: "auto",
  targetLanguage: "ru",
  speaker: getDefaultTTSVoice("qwen3"),
  audioFormat: "mp3",
  learnerLevel: "auto",
  enableAudio: true,
  enableImages: true,
  imageProvider: "local",
  imageModel: getDefaultImageModel("local"),
}

const MAX_HISTORY_ITEMS = 20

function upsertHistoryItem(
  history: DeckHistoryItem[],
  item: DeckHistoryItem
): DeckHistoryItem[] {
  const withoutExisting = history.filter((entry) => entry.task_id !== item.task_id)
  return [item, ...withoutExisting].slice(0, MAX_HISTORY_ITEMS)
}

// ─── Store interface ──────────────────────────────────────────────────────────

interface GenerationStore {
  // Form
  form: FormState
  setFormField: <K extends keyof FormState>(key: K, value: FormState[K]) => void
  resetForm: () => void

  // Task
  taskId: string | null
  taskStatus: TaskStatus | null
  setTaskId: (id: string) => void
  setTaskStatus: (s: TaskStatus) => void

  // Progress (built from SSE events)
  processed: number
  total: number
  events: SSEEventRecord[]
  pushEvent: (ev: SSEEventRecord) => void
  clearEvents: () => void

  // Cards (accumulated from word_complete SSE events)
  cards: CardInfo[]
  addCard: (card: CardInfo) => void
  setCards: (cards: CardInfo[]) => void // hydration after page refresh
  updateCard: (index: number, partial: Partial<CardInfo>) => void
  deleteCard: (index: number) => void

  // Selected card for editor / preview
  selectedCardIndex: number
  setSelectedCardIndex: (i: number) => void

  // Page view state machine
  viewStatus: ViewStatus
  setViewStatus: (s: ViewStatus) => void
  error: string | null
  setError: (msg: string | null) => void

  // Built deck result
  builtDeck: BuildDeckResponse | null
  setBuiltDeck: (d: BuildDeckResponse) => void

  // Local history
  deckHistory: DeckHistoryItem[]
  recordTaskStart: (taskId: string, deckName: string, wordCount: number) => void
  markTaskFailed: (taskId: string) => void
  clearDeckHistory: () => void

  // Global reset (start over)
  reset: () => void
}

// ─── Store implementation ─────────────────────────────────────────────────────

export const useGenerationStore = create<GenerationStore>()(
  persist(
    (set) => ({
      // Form
      form: defaultForm,
      setFormField: (key, value) =>
        set((s) => ({ form: { ...s.form, [key]: value } })),
      resetForm: () => set({ form: defaultForm }),

      // Task
      taskId: null,
      taskStatus: null,
      setTaskId: (id) => set({ taskId: id }),
      setTaskStatus: (s) => set({ taskStatus: s }),

      // Progress
      processed: 0,
      total: 0,
      events: [],
      pushEvent: (ev) =>
        set((s) => ({
          events: [...s.events, ev],
          processed: ev.processed ?? s.processed,
          total: ev.total ?? s.total,
        })),
      clearEvents: () => set({ events: [], processed: 0, total: 0 }),

      // Cards
      cards: [],
      addCard: (card) => set((s) => ({ cards: [...s.cards, card] })),
      setCards: (cards) => set({ cards }),
      updateCard: (index, partial) =>
        set((s) => {
          const next = [...s.cards]
          next[index] = { ...next[index], ...partial }
          return { cards: next }
        }),
      deleteCard: (index) =>
        set((s) => {
          const cards = s.cards.filter((_, i) => i !== index)
          const shiftedIndex =
            s.selectedCardIndex > index
              ? s.selectedCardIndex - 1
              : s.selectedCardIndex
          return {
            cards,
            selectedCardIndex: Math.max(
              0,
              Math.min(shiftedIndex, cards.length - 1)
            ),
          }
        }),

      // Selected
      selectedCardIndex: 0,
      setSelectedCardIndex: (i) => set({ selectedCardIndex: i }),

      // View
      viewStatus: "idle",
      setViewStatus: (s) => set({ viewStatus: s }),
      error: null,
      setError: (msg) => set({ error: msg }),

      // Deck
      builtDeck: null,
      setBuiltDeck: (d) =>
        set((s) => {
          const now = new Date().toISOString()
          const taskId = s.taskId ?? d.filename
          const existing = s.deckHistory.find((entry) => entry.task_id === taskId)
          return {
            builtDeck: d,
            deckHistory: upsertHistoryItem(s.deckHistory, {
              task_id: taskId,
              deck_name: d.deck_name,
              word_count: existing?.word_count ?? s.cards.length,
              card_count: d.card_count,
              status: "ready",
              filename: d.filename,
              download_url: d.download_url,
              created_at: existing?.created_at ?? now,
              updated_at: now,
            }),
          }
        }),

      // Local history
      deckHistory: [],
      recordTaskStart: (taskId, deckName, wordCount) =>
        set((s) => {
          const now = new Date().toISOString()
          return {
            deckHistory: upsertHistoryItem(s.deckHistory, {
              task_id: taskId,
              deck_name: deckName,
              word_count: wordCount,
              card_count: 0,
              status: "generating",
              created_at: now,
              updated_at: now,
            }),
          }
        }),
      markTaskFailed: (taskId) =>
        set((s) => ({
          deckHistory: s.deckHistory.map((entry) =>
            entry.task_id === taskId
              ? {
                  ...entry,
                  status: "failed",
                  updated_at: new Date().toISOString(),
                }
              : entry
          ),
        })),
      clearDeckHistory: () => set({ deckHistory: [], builtDeck: null }),

      // Reset
      reset: () =>
        set({
          taskId: null,
          taskStatus: null,
          events: [],
          processed: 0,
          total: 0,
          cards: [],
          selectedCardIndex: 0,
          viewStatus: "idle",
          error: null,
          builtDeck: null,
        }),
    }),
    {
      name: "anki-generation",
      storage: createJSONStorage(() =>
        // localStorage keeps task/deck history after closing the tab.
        typeof window !== "undefined" ? localStorage : sessionStorage
      ),
      // Only persist what's needed for refresh resilience
      partialize: (s) => ({
        taskId: s.taskId,
        cards: s.cards,
        form: { ...s.form, rawWords: "" }, // don't persist the raw textarea
        builtDeck: s.builtDeck,
        deckHistory: s.deckHistory,
      }),
    }
  )
)
