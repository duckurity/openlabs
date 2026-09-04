'use client'

import * as React from 'react'
import SearchIcon from '@/components/icons/search'
import { Kbd } from '@/components/ui/kbd'

type SidebarSearchProps = {
  query: string
  setQuery: (query: string) => void
  inputRef?: React.Ref<HTMLInputElement>
}

export function SidebarSearch({ query, setQuery, inputRef }: SidebarSearchProps) {
  return (
    <div className="relative">
      <div className="h-aside-width bg-muted focus-within:bg-accent/70 active:bg-accent/70 flex w-full items-center gap-3 px-4">
        <SearchIcon className="text-muted-foreground size-4 shrink-0" />
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search"
          aria-label="Search"
          className="focus-ring text-foreground placeholder:text-muted-foreground h-full min-w-0 flex-1 bg-transparent focus:bg-transparent active:bg-transparent font-mono text-sm tracking-wide"
        />
        {!query && <Kbd className="h-[2em] px-2">/</Kbd>}
      </div>
    </div>
  )
}
