import Link from 'next/link'
import { Badge } from '@/components/ui/badge'
import { LabGrid } from '@/components/lab/lab-grid'

const SPONSORS_URL = 'https://github.com/sponsors/Duckurity'

/* Sponsor wall. Four slots max. Duckurity ships first. Add a
   row to join the wall. Empty slots stay dashed placeholders. */
const SPONSORS = [
  {
    name: 'Duckurity',
    caption: 'Sponsor',
    url: 'https://github.com/Duckurity',
    logo: 'https://github.com/duckurity.png?s=128',
  },
]
const MAX_SPONSORS = 4

/* One sponsor logo tile. Logo left, mono name and caption right. */
function SponsorTile({
  name,
  caption,
  url,
  logo,
}: {
  name: string
  caption: string
  url: string
  logo: string
}) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`${name} on GitHub`}
      className="focus-ring group bg-card group-hover:bg-accent/50 flex h-full items-center gap-3 px-4 py-3 transition-[color,background-color,border-color] duration-[var(--duration-normal)] ease-[var(--ease-out)]"
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={logo} alt="" loading="eager" className="size-10 shrink-0" />
      <span className="flex min-w-0 flex-col gap-1">
        <span className="text-card-foreground truncate font-mono text-sm font-medium tracking-wide">
          {name}
        </span>
        <span className="text-muted-foreground font-mono text-xs tracking-wide">
          {caption}
        </span>
      </span>
    </a>
  )
}

function SponsorPlaceholder() {
  return (
    <a
      href={SPONSORS_URL}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Become a sponsor"
      className="focus-ring group border-border bg-card/40 hover:bg-card/70 flex h-full items-center justify-center border border-dashed px-4 py-3 transition-[color,background-color,border-color] duration-[var(--duration-normal)] ease-[var(--ease-out)]"
    >
      <span className="text-muted-foreground group-hover:text-foreground font-mono text-xs transition-colors">
        +
      </span>
    </a>
  )
}

/* One card per support option. Mirrors the lab card rows:
   badge, mono title with arrow, short description, action line.
   No banner art. The grid entrance matches the lab grid. */
function SponsorCard({
  badge,
  title,
  description,
  action,
  href,
  external = false,
}: {
  badge: string
  title: string
  description: string
  action: string
  href: string
  external?: boolean
}) {
  return (
    <Link
      href={href}
      {...(external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
      className="focus-ring group relative flex h-full flex-col gap-1 overflow-hidden transition-[color,background-color,border-color,transform] duration-[var(--duration-fast)] ease-[var(--ease-out)] active:scale-[0.98] active:duration-[var(--duration-instant)] has-touch-screen:active:scale-[0.99]"
    >
      <div className="bg-card flex items-center justify-between px-4 py-3">
        <Badge>{badge}</Badge>
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
      <div className="bg-card group-hover:bg-accent/50 flex flex-1 flex-col gap-1 px-4 py-3 transition-[color,background-color,border-color] duration-[var(--duration-normal)] ease-[var(--ease-out)]">
        <span className="text-card-foreground font-mono text-sm font-medium tracking-wide">
          {title}
        </span>
        <span className="text-muted-foreground text-sm leading-relaxed">
          {description}
        </span>
        <span className="text-muted-foreground font-mono text-xs tracking-wide">
          {action}
        </span>
      </div>
    </Link>
  )
}

/* Home support section. Two options: give time or give funds.
   Renders below the lab grid on the home page only. */
export function SponsorSection() {
  return (
    <div className="mt-16">
      <h2 className="mb-1 font-mono text-sm tracking-wide">
        Support the project
      </h2>
      <p className="text-muted-foreground mb-4 text-sm leading-relaxed">
        Labs stay free with help. Give time or give funds.
      </p>
      <p className="readout mb-2">Sponsors</p>
      <LabGrid className="grid-cols-2 sm:grid-cols-4">
        {SPONSORS.map((sponsor) => (
          <SponsorTile key={sponsor.name} {...sponsor} />
        ))}
        {Array.from(
          { length: MAX_SPONSORS - SPONSORS.length },
          (_, i) => i
        ).map((i) => (
          <SponsorPlaceholder key={`slot-${i}`} />
        ))}
      </LabGrid>
      <LabGrid className="mt-2">
        <SponsorCard
          badge="contribute"
          title="Maintain and create"
          description="Review labs. Fix bugs. Author new challenges."
          action="Read the guide"
          href="/contribute"
        />
        <SponsorCard
          badge="sponsor"
          title="Fund the project"
          description="Back maintenance and new labs. Give once or monthly."
          action="Open GitHub Sponsors"
          href={SPONSORS_URL}
          external
        />
      </LabGrid>
    </div>
  )
}
