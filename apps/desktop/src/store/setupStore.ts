import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { VideoFormat, VideoStyle, Idea } from '../lib/types'

export type QualityMode = 'preview' | 'final'

interface SetupState {
  keyword: string
  format: VideoFormat
  durationSeconds: number
  outputCount: number
  styles: VideoStyle[]
  outputFolder: string
  qualityMode: QualityMode

  // Idea generation (not persisted)
  ideas: Idea[]
  selectedIdeaId: string | null
  isLoadingIdeas: boolean

  setKeyword: (v: string) => void
  setFormat: (v: VideoFormat) => void
  setDuration: (v: number) => void
  setOutputCount: (v: number) => void
  toggleStyle: (s: VideoStyle) => void
  setOutputFolder: (v: string) => void
  setQualityMode: (v: QualityMode) => void

  setIdeas: (ideas: Idea[]) => void
  setSelectedIdeaId: (id: string | null) => void
  setIsLoadingIdeas: (v: boolean) => void
  clearIdeas: () => void
}

export const useSetupStore = create<SetupState>()(
  persist(
    (set, get) => ({
      keyword: '',
      format: '9:16',
      durationSeconds: 30,
      outputCount: 1,
      styles: ['viral'],
      outputFolder: '',
      qualityMode: 'final',

      ideas: [],
      selectedIdeaId: null,
      isLoadingIdeas: false,

      setKeyword: (v) => set({ keyword: v }),
      setFormat: (v) => set({ format: v }),
      setDuration: (v) => set({ durationSeconds: v }),
      setOutputCount: (v) => set({ outputCount: Math.max(1, Math.min(10, v)) }),
      toggleStyle: (s) => {
        const { styles } = get()
        const next = styles.includes(s)
          ? styles.filter((x) => x !== s)
          : [...styles, s]
        if (next.length > 0) set({ styles: next })
      },
      setOutputFolder: (v) => set({ outputFolder: v }),
      setQualityMode: (v) => set({ qualityMode: v }),

      setIdeas: (ideas) => set({ ideas }),
      setSelectedIdeaId: (id) => set({ selectedIdeaId: id }),
      setIsLoadingIdeas: (v) => set({ isLoadingIdeas: v }),
      clearIdeas: () => set({ ideas: [], selectedIdeaId: null, isLoadingIdeas: false }),
    }),
    {
      name: 'setup-store-v1',
      // Only persist UI prefs — not session state like ideas
      partialize: (s) => ({
        format: s.format,
        durationSeconds: s.durationSeconds,
        outputCount: s.outputCount,
        styles: s.styles,
        outputFolder: s.outputFolder,
        qualityMode: s.qualityMode,
      }),
    }
  )
)
