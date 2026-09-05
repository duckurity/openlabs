'use client'

import { formatCount } from '@/lib/github'
import { useLiveStars } from '@/hooks/use-live-stars'

/* Client island for the star count. Server paints the baked count
   first, so this never flashes empty. Swaps live when the refetch
   lands. Renders nothing without a count, same as the server. */
export function LiveStarCount({
  owner,
  repo,
  initial,
  showDivider,
}: {
  owner: string
  repo: string
  initial: number | null
  showDivider: boolean
}) {
  const stars = useLiveStars(owner, repo, initial)
  if (stars === null) return null
  return (
    <>
      {showDivider && (
        <span className="h-3.5 w-px shrink-0 bg-border" aria-hidden="true" />
      )}
      <span className="tnum">{formatCount(stars)}</span>
    </>
  )
}
