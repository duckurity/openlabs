'use client'

type NoResultsProps = {
  query: string
}

export function NoResults({ query }: NoResultsProps) {
  return (
    <div className="flex h-full flex-col">
      <div className="bg-muted lg:h-aside-width flex shrink-0 flex-col justify-center px-5 max-lg:py-4">
        <p className="text-muted-foreground flex min-w-0 items-center font-mono text-sm font-medium">
          <span className="shrink-0">No results for &ldquo;</span>
          <span className="text-foreground min-w-0 truncate font-bold">
            {query}
          </span>
          <span className="shrink-0">&rdquo;</span>
        </p>
        <p className="text-muted-foreground/60 mt-1 text-xs italic">
          Try a track name, a difficulty, or a lab title.
        </p>
      </div>
    </div>
  )
}
