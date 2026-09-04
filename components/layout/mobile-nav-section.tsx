'use client'

import * as React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import type * as PageTree from 'fumadocs-core/page-tree'
import { cn } from '@/lib/utils'

export function MobileNavSection({ folder }: { folder: PageTree.Folder }) {
  const pathname = usePathname()
  const name =
    typeof folder.name === 'string' ? folder.name : String(folder.name)
  const [isOpen, setIsOpen] = React.useState(true)
  const isActive = pathname.startsWith(`/${name.toLowerCase()}`)

  return (
    <div className="group relative" data-active={isActive}>
      <button
        type="button"
        aria-expanded={isOpen}
        onClick={() => setIsOpen(!isOpen)}
        className="focus-ring bg-secondary group-data-[active='true']:bg-accent hover:bg-accent flex h-12 w-full items-center gap-3 px-4 text-left transition-[color,background-color] duration-[var(--duration-fast)] ease-[var(--ease-out)] active:scale-[0.99]"
      >
        <span className="font-mono text-xs font-medium tracking-wide">
          {name}
        </span>
        <span
          aria-hidden="true"
          className="text-muted-foreground ml-auto font-mono text-sm leading-none"
        >
          {isOpen ? '−' : '+'}
        </span>
      </button>
      {isOpen && (
        <div className="bg-accent/50 flex flex-col">
          {folder.children.map((child) => {
            if (child.type !== 'page') return null
            const active = pathname === child.url
            return (
              <Link
                key={child.url}
                href={child.url}
                className={cn(
                  'focus-ring px-4 py-3 font-mono text-sm tracking-wide transition-[color,background-color] duration-[var(--duration-fast)] ease-[var(--ease-out)]',
                  active
                    ? 'text-foreground bg-accent font-medium'
                    : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
                )}
              >
                {child.name}
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
