'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

function PlusIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      aria-hidden="true"
      className={className}
    >
      <path d="M8 2v12M2 8h12" />
    </svg>
  )
}

function MinusIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      aria-hidden="true"
      className={className}
    >
      <path d="M2 8h12" />
    </svg>
  )
}

function PlusMinus({ open }: { open: boolean }) {
  return (
    <span className="text-muted-foreground relative block size-3">
      <PlusIcon
        className={cn(
          'absolute inset-0 size-3 transition-opacity duration-200 ease-out',
          open ? 'opacity-0' : 'opacity-100'
        )}
      />
      <MinusIcon
        className={cn(
          'absolute inset-0 size-3 transition-opacity duration-200 ease-out',
          open ? 'opacity-100' : 'opacity-0'
        )}
      />
    </span>
  )
}

type CollapsibleSectionProps = {
  name: string
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>
  defaultOpen?: boolean
  isActive?: boolean
  children: React.ReactNode
}

export function CollapsibleSection({
  name,
  icon: Icon,
  defaultOpen = true,
  isActive = false,
  children,
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = React.useState(defaultOpen)

  return (
    <div className="flex flex-col">
      <button
        type="button"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((v) => !v)}
        className={cn(
          'focus-ring min-h-aside-width flex items-center gap-2 ps-4 py-5 text-left transition-[color,background-color] duration-[var(--duration-normal)] ease-[var(--ease-out)]',
          'hover:bg-accent',
          '-me-3 pe-[calc(1rem+12px)]',
          isActive && 'text-foreground/70'
        )}
      >
        <Icon className="size-4" />
        <span className="font-mono text-sm font-medium tracking-wide">
          {name}
        </span>
        <span className="ml-auto">
          <PlusMinus open={isOpen} />
        </span>
      </button>

      <div
        className={cn(
          'grid transition-[grid-template-rows,opacity] duration-[var(--duration-normal)] ease-[var(--ease-out)]',
          isOpen ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'
        )}
      >
        <div className="overflow-hidden">
          {children}
          <div className="border-border ml-4 h-3 border-l-2" />
        </div>
      </div>
    </div>
  )
}
