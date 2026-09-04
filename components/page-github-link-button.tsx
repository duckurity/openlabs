import Link from 'next/link'
import { Button } from './ui/button'
import GithubIcon from './icons/github'
import { ArrowUpRightIcon } from './icons/mini'
import { cn } from '@/lib/utils'

const REPO = 'https://github.com/Duckurity/openlabs/blob/main'

export function PageGithubLinkButton({
  path,
  className,
}: {
  path: string
  className?: string
}) {
  return (
    <Button
      asChild
      variant="secondary"
      size="sm"
      className={cn('font-mono tracking-wide', className)}
    >
      <Link href={`${REPO}/content/${path}`} target="_blank" rel="noopener noreferrer">
        <GithubIcon className="size-4" />
        Open in GitHub
        <ArrowUpRightIcon className="size-3" />
      </Link>
    </Button>
  )
}
