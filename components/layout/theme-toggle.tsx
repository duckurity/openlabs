'use client'

import * as React from 'react'
import { useTheme } from 'next-themes'
import { cn } from '@/lib/utils'
import { AsideButton } from './nav-aside'
import SunIcon from '@/components/icons/sun'
import MoonIcon from '@/components/icons/moon'

export const themes = [
  { name: 'light', label: 'Light', icon: SunIcon },
  { name: 'dark', label: 'Dark', icon: MoonIcon },
] as const

export const ThemeToggle = () => {
  const { resolvedTheme } = useTheme()
  const [isOpen, setIsOpen] = React.useState(false)
  const containerRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    if (!isOpen) return
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  const isDark = resolvedTheme !== 'light'

  return (
    <div ref={containerRef} className="relative flex flex-col gap-1">
      {isOpen && <ThemeOptions onSelect={() => setIsOpen(false)} />}
      <AsideButton
        onClick={() => setIsOpen(!isOpen)}
        tooltip={isOpen ? undefined : 'Theme'}
        aria-label="Theme"
      >
        {isOpen ? (
          <span className="font-mono text-xs">Close</span>
        ) : (
          <span className={cn('icon-swap', isDark && 'is-on')}>
            <SunIcon data-icon="off" className="size-5" />
            <MoonIcon data-icon="on" className="size-5" />
          </span>
        )}
        {!isOpen && <span className="sr-only">Theme</span>}
      </AsideButton>
    </div>
  )
}

function ThemeOptions({ onSelect }: { onSelect: () => void }) {
  const { theme, setTheme } = useTheme()

  return (
    <div className="flex flex-col gap-1">
      {themes.map((t) => {
        const Icon = t.icon
        return (
          <AsideButton
            key={t.name}
            icon={Icon}
            label={t.label}
            tooltip={t.label}
            onClick={() => {
              // Kill transitions across the flip so light/dark never smears.
              document.documentElement.classList.add('theme-flip')
              setTheme(t.name)
              requestAnimationFrame(() =>
                requestAnimationFrame(() =>
                  document.documentElement.classList.remove('theme-flip')
                )
              )
              onSelect()
            }}
            aria-label={t.label}
            className={cn(
              theme === t.name && 'bg-accent text-accent-foreground'
            )}
          />
        )
      })}
    </div>
  )
}
