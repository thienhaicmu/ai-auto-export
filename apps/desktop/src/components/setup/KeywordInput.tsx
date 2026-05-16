import { Search } from 'lucide-react'
import { useSetupStore } from '../../store/setupStore'

export function KeywordInput() {
  const keyword = useSetupStore((s) => s.keyword)
  const setKeyword = useSetupStore((s) => s.setKeyword)

  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-semibold text-muted uppercase tracking-wider">
        Keyword
      </label>
      <div className="relative">
        <Search
          size={14}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-muted pointer-events-none"
        />
        <input
          type="text"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          placeholder="karen, trump, bitcoin…"
          className="w-full bg-elevated border border-subtle rounded-lg pl-9 pr-4 py-2.5 text-sm text-primary placeholder:text-muted outline-none transition-colors focus:border-accent focus:ring-1 focus:ring-accent/30"
          aria-label="Keyword input"
          maxLength={120}
          autoComplete="off"
          spellCheck={false}
        />
      </div>
      {keyword.length > 0 && (
        <p className="text-2xs text-muted">
          AI will generate viral video ideas for "{keyword}"
        </p>
      )}
    </div>
  )
}
