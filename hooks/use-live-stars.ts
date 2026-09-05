'use client'

import * as React from 'react'

/* Live star count with a baked fallback. Paints `initial` instantly,
   then refetches once on mount and swaps on success. Any failure,
   abort, or unmount resolves silently to the baked count. */
export function useLiveStars(
  owner: string,
  repo: string,
  initial: number | null
): number | null {
  const [stars, setStars] = React.useState<number | null>(initial)

  React.useEffect(() => {
    const controller = new AbortController()
    fetch(`https://api.github.com/repos/${owner}/${repo}`, {
      headers: { Accept: 'application/vnd.github.v3+json' },
      signal: controller.signal,
    })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (
          data &&
          typeof data.stargazers_count === 'number' &&
          data.stargazers_count !== initial
        ) {
          setStars(data.stargazers_count)
        }
      })
      // Offline, rate-limited, or unmounted. Keep the baked count.
      .catch(() => {})
    return () => controller.abort()
  }, [owner, repo, initial])

  return stars
}
