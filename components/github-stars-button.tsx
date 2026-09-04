/**
 * Link button showing a GitHub repo's star count.
 *
 * Async server component. The count is fetched at build time, so it
 * refreshes on every deploy. Renders the link without a count when
 * the API is unreachable.
 */

import * as React from 'react'
import { cn } from '@/lib/utils'
import GithubIcon from '@/components/icons/github'
import { fetchGitHubRepo, formatCount } from '@/lib/github'

interface GitHubStarsButtonProps extends Omit<React.ComponentProps<'a'>, 'children'> {
  owner: string
  repo: string
  /** Pre-fetched star count. Skips the API call entirely. */
  stars?: number
  showRepo?: boolean
}

async function GitHubStarsButton({
  owner,
  repo,
  stars: starsProp,
  showRepo = false,
  className,
  ...props
}: GitHubStarsButtonProps) {
  const data = starsProp == null ? await fetchGitHubRepo(owner, repo) : null
  const stars = starsProp ?? data?.stars ?? null
  const fullName = data?.fullName ?? `${owner}/${repo}`
  const starLabel =
    stars === null
      ? ''
      : ` — ${stars.toLocaleString('en-US')} star${stars === 1 ? '' : 's'}`

  return (
    <a
      href={`https://github.com/${owner}/${repo}`}
      target="_blank"
      rel="noopener noreferrer"
      data-slot="github-stars-button"
      aria-label={`${fullName} on GitHub${starLabel}`}
      className={cn(
        'focus-ring inline-flex h-8 shrink-0 items-center gap-2 border border-border bg-muted/50 px-3 font-mono text-sm whitespace-nowrap text-muted-foreground transition-colors outline-none hover:bg-accent hover:text-accent-foreground [&_svg]:size-4',
        className
      )}
      {...props}
    >
      <GithubIcon className="shrink-0" />
      {showRepo && <span className="max-w-[12rem] truncate">{fullName}</span>}
      {stars !== null && (
        <>
          {showRepo && (
            <span className="h-3.5 w-px shrink-0 bg-border" aria-hidden="true" />
          )}
          <span className="tnum">{formatCount(stars)}</span>
        </>
      )}
    </a>
  )
}

export { GitHubStarsButton, type GitHubStarsButtonProps }
