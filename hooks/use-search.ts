'use client'

import * as React from 'react'

export type SearchItem = {
  url: string
  title: string
  description?: string
}

export function useLocalSearch(items: SearchItem[]) {
  const [query, setQuery] = React.useState('')

  const results = React.useMemo(() => {
    const q = query.trim().toLowerCase()
    if (q.length < 2) return []
    return items
      .filter(
        (item) =>
          item.title.toLowerCase().includes(q) ||
          (item.description ?? '').toLowerCase().includes(q) ||
          item.url.toLowerCase().includes(q)
      )
      .slice(0, 8)
  }, [items, query])

  return {
    query,
    setQuery,
    results,
    hasResults: results.length > 0,
    isEmpty: query.trim().length >= 2 && results.length === 0,
  }
}
