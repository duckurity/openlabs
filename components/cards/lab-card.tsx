import Link from 'next/link'
import { cn } from '@/lib/utils'
import { Badge } from '../ui/badge'

type LabCardProps = {
  href: string
  title: string
  description?: string
  track?: string
  difficulty?: string
  port?: string
}

const difficultyLabel: Record<string, string> = {
  easy: 'Easy',
  medium: 'Medium',
  hard: 'Hard',
  insane: 'Insane',
}

export function LabCard({
  href,
  title,
  description,
  track,
  difficulty,
  port,
}: LabCardProps) {
  return (
    <Link
      href={href}
      className="focus-ring group relative flex flex-col gap-1 overflow-hidden transition-[color,background-color,border-color,transform] duration-[var(--duration-fast)] ease-[var(--ease-out)] active:scale-[0.98] active:duration-[var(--duration-instant)] has-touch-screen:active:scale-[0.99]"
    >
      <div className="bg-card flex items-center justify-between px-4 py-3">
        <Badge>
          {track ?? 'lab'}
          {port ? ` :${port}` : ''}
        </Badge>
        {difficulty && (
          <span className="font-mono text-xs tracking-wide">
            {difficultyLabel[difficulty] ?? difficulty}
          </span>
        )}
      </div>
      <div className="bg-card group-hover:bg-accent/50 flex flex-1 flex-col gap-1 px-4 py-3 transition-[color,background-color,border-color] duration-[var(--duration-normal)] ease-[var(--ease-out)]">
        <div className="flex items-start justify-between">
          <span className="text-card-foreground font-mono text-sm font-medium tracking-wide">
            {title}
          </span>
          <svg
            aria-hidden="true"
            className="h-[1.25em] shrink-0 -rotate-45 transition-transform duration-[var(--duration-normal)] ease-[var(--ease-out)] group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </div>
        {description && (
          <span className="text-muted-foreground line-clamp-2 text-sm leading-relaxed">
            {description}
          </span>
        )}
        <span className="text-muted-foreground font-mono text-xs tracking-wide">
          Open the brief
        </span>
      </div>
    </Link>
  )
}
