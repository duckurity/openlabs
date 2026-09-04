'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { useLocalSearch, type SearchItem } from '@/hooks/use-search'
import { SearchResults } from './sidebar/search-results'
import { NoResults } from './sidebar/no-results'
import { AnimatePresence, motion } from 'motion/react'
import SearchIcon from '@/components/icons/search'
import { Kbd } from '@/components/ui/kbd'

const suggestedSearches = ['web', 'easy', 'docker', 'flag', 'duck-cross']

export { suggestedSearches }

export function CommandPalette({ items }: { items: SearchItem[] }) {
  const router = useRouter()
  const inputRef = React.useRef<HTMLInputElement>(null)
  const [isOpen, setIsOpen] = React.useState(false)
  const { query, setQuery, results, hasResults, isEmpty } =
    useLocalSearch(items)

  const handleClose = React.useCallback(() => {
    setIsOpen(false)
    setQuery('')
  }, [setQuery])

  const handleSelect = React.useCallback(
    (url: string) => {
      router.push(url)
      handleClose()
    },
    [router, handleClose]
  )

  React.useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
        event.preventDefault()
        setIsOpen((prev) => !prev)
      }
      if (event.key === 'Escape' && isOpen) {
        event.preventDefault()
        handleClose()
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [isOpen, handleClose])

  React.useEffect(() => {
    if (isOpen) {
      requestAnimationFrame(() => inputRef.current?.focus())
    }
  }, [isOpen])

  React.useEffect(() => {
    document.body.style.overflow = isOpen ? 'hidden' : ''
    return () => {
      document.body.style.overflow = ''
    }
  }, [isOpen])

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Search"
      className={`fixed inset-0 z-(--z-dialog) flex items-start justify-center pt-[15vh] ${
        isOpen ? '' : 'pointer-events-none'
      }`}
    >
      <span className="sr-only">Press Escape to close</span>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            key="backdrop"
            onClick={handleClose}
            aria-hidden="true"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2, ease: [0.23, 1, 0.32, 1] }}
            className="cctv-backdrop absolute inset-0 cursor-pointer"
          />
        )}
      </AnimatePresence>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            key="panel"
            initial={{ opacity: 0, scale: 0.95, y: -6, filter: 'blur(4px)' }}
            animate={{ opacity: 1, scale: 1, y: 0, filter: 'blur(0px)' }}
            exit={{ opacity: 0, scale: 0.97, y: -4, filter: 'blur(4px)' }}
            transition={{ type: 'spring', bounce: 0, duration: 0.35 }}
            className="notch bg-background border-border relative mx-4 flex w-full max-w-xl flex-col border"
          >
      <div className="relative">
          <div className="bg-muted flex h-14 w-full items-center gap-3 px-4">
            <SearchIcon className="text-muted-foreground size-4 shrink-0" />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search labs"
              aria-label="Search labs"
              className="focus-ring text-foreground placeholder:text-muted-foreground h-full min-w-0 flex-1 bg-transparent font-mono text-sm tracking-wide"
            />
            <Kbd className="h-[2em] px-2">Esc</Kbd>
          </div>
        </div>
        <div className="max-h-[60vh] overflow-x-hidden overflow-y-auto">
          {hasResults && (
            <SearchResults
              results={results}
              query={query}
              onSelect={handleSelect}
            />
          )}
          {isEmpty && <NoResults query={query} />}
          {!hasResults && !isEmpty && (
            <div className="bg-accent/70 flex flex-col pt-2 pb-4 outline-0">
              <span className="text-muted-foreground px-4 py-2 font-mono text-xs tracking-wide">
                Suggested searches
              </span>
              {suggestedSearches.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => setQuery(suggestion)}
                  className="focus-ring text-muted-foreground hover:text-foreground hover:bg-accent focus-visible:text-foreground focus-visible:bg-accent flex cursor-pointer items-center gap-2 py-3 pr-4 pl-4 text-left transition-[color,background-color] duration-[var(--duration-normal)] ease-[var(--ease-out)] active:scale-[0.99]"
                >
                  <SearchIcon className="size-3.5 shrink-0 opacity-50" />
                  <span className="font-mono text-sm tracking-wide">
                    {suggestion}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
