'use client'

import { cn } from '@/lib/utils'
import type { SearchItem } from '@/hooks/use-search'

type SearchResultsProps = {
  results: SearchItem[]
  query: string
  onSelect: (url: string) => void
  className?: string
}

function HighlightedText({ text, query }: { text: string; query: string }) {
  if (!query.trim()) return <>{text}</>
  const regex = new RegExp(
    `(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`,
    'gi'
  )
  const parts = text.split(regex)
  return (
    <>
      {parts.map((part, i) =>
        regex.test(part) ? (
          <mark key={i} className="bg-primary text-primary-foreground px-0.5">
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  )
}

export function SearchResults({
  results,
  query,
  onSelect,
  className,
}: SearchResultsProps) {
  if (results.length === 0) return null
  return (
    <div
      role="listbox"
      aria-label="Search results"
      className={cn(
        'bg-accent/70 flex max-h-none flex-col overflow-y-auto outline-none',
        className
      )}
    >
      <div className="flex flex-col pt-2 pb-4">
        <div className="border-border ml-4 flex flex-col border-l">
          {results.map((item) => (
            <button
              key={item.url}
              type="button"
              role="option"
              aria-selected="false"
              onClick={() => onSelect(item.url)}
              className={cn(
                'focus-ring flex cursor-pointer flex-col gap-0.5 py-1.5 pr-4 pl-4 text-left transition-[color,background-color] duration-[var(--duration-normal)] ease-[var(--ease-out)]',
                'text-muted-foreground',
                'hover:text-foreground hover:bg-accent focus-visible:text-foreground focus-visible:bg-accent active:text-foreground active:bg-accent'
              )}
            >
              <span className="font-mono text-sm tracking-wide">
                <HighlightedText text={item.title} query={query} />
              </span>
              {item.description && (
                <span className="text-muted-foreground/70 line-clamp-2 text-xs normal-case">
                  <HighlightedText text={item.description} query={query} />
                </span>
              )}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
