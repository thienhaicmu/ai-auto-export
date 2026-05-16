import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { VideoFormat, VideoStyle } from '../lib/types'

interface SetupState {
  keyword: string
  format: VideoFormat
  durationSeconds: number
  outputCount: number
  styles: VideoStyle[]
  outputFolder: string

  setKeyword: (v: string) => void
  setFormat: (v: VideoFormat) => void
  setDuration: (v: number) => void
  setOutputCount: (v: number) => void
  toggleStyle: (s: VideoStyle) => void
  setOutputFolder: (v: string) => void
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

      setKeyword: (v) => set({ keyword: v }),
      setFormat: (v) => set({ format: v }),
      setDuration: (v) => set({ durationSeconds: v }),
      setOutputCount: (v) => set({ outputCount: Math.max(1, Math.min(10, v)) }),
      toggleStyle: (s) => {
        const { styles } = get()
        const next = styles.includes(s)
          ? styles.filter((x) => x !== s)
          : [...styles, s]
        // Always keep at least one style selected
        if (next.length > 0) set({ styles: next })
      },
      setOutputFolder: (v) => set({ outputFolder: v }),
    }),
    {
      name: 'setup-store-v1',
      // Only persist UI prefs — not project state
      partialize: (s) => ({
        format: s.format,
        durationSeconds: s.durationSeconds,
        outputCount: s.outputCount,
        styles: s.styles,
        outputFolder: s.outputFolder,
      }),
    }
  )
)
