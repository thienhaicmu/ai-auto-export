import { create } from 'zustand'

interface PreviewState {
  selectedVariantId: string | null
  currentTime: number
  isFullscreen: boolean

  selectVariant: (id: string) => void
  setCurrentTime: (t: number) => void
  setFullscreen: (v: boolean) => void
  clear: () => void
}

export const usePreviewStore = create<PreviewState>()((set) => ({
  selectedVariantId: null,
  currentTime: 0,
  isFullscreen: false,

  selectVariant: (id) => set({ selectedVariantId: id }),
  setCurrentTime: (t) => set({ currentTime: t }),
  setFullscreen: (v) => set({ isFullscreen: v }),
  clear: () => set({ selectedVariantId: null, currentTime: 0, isFullscreen: false }),
}))
