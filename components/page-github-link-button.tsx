import Link from 'next/link'
import { Button } from './ui/button'
import GithubIcon from './icons/github'
import { ArrowUpRightIcon } from './icons/mini'
import { cn } from '@/lib/utils'

const REPO = 'https://github.com/Duckurity/openlabs/blob/main'

export function PageGithubLinkButton({
  path,
  className,
  label = 'Open in GitHub',
}: {
  /** Repo-relative path, e.g. content/labs/duck-cross.mdx */
  path: string
  className?: string
  label?: string
}) {
  return (
    <Button
      asChild
      variant="secondary"
      size="sm"
      className={cn('font-mono tracking-wide', className)}
    >
      <Link href={`${REPO}/${path}`} target="_blank" rel="noopener noreferrer">
        <GithubIcon className="size-4" />
        {label}
        <ArrowUpRightIcon className="size-3" />
      </Link>
    </Button>
  )
}
