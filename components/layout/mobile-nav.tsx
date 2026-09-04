'use client'

import * as React from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import type * as PageTree from 'fumadocs-core/page-tree'
import { cn } from '@/lib/utils'
import { Logo } from '../logos'
import SearchIcon from '@/components/icons/search'
import { useLocalSearch, type SearchItem } from '@/hooks/use-search'
import { SearchResults } from './sidebar/search-results'
import { NoResults } from './sidebar/no-results'
import { themes } from './theme-toggle'
import SunIcon from '@/components/icons/sun'
import MoonIcon from '@/components/icons/moon'
import { useTheme } from 'next-themes'
import { Drawer } from 'vaul'
import { MenuIcon } from '../icons/menu'
import { MobileNavSection } from './mobile-nav-section'

type MobileNavProps = {
  tree: PageTree.Root
  searchItems: SearchItem[]
}

export function MobileNav({ tree, searchItems }: MobileNavProps) {
  const pathname = usePathname()
  const router = useRouter()
  const [open, setOpen] = React.useState(false)
  const [searching, setSearching] = React.useState(false)
  const { query, setQuery, results, hasResults, isEmpty } =
    useLocalSearch(searchItems)
  const { theme, setTheme } = useTheme()

  React.useEffect(() => {
    setOpen(false)
    setSearching(false)
    setQuery('')
  }, [pathname, setQuery])

  const folders = tree.children.filter(
    (child): child is PageTree.Folder => child.type === 'folder'
  )

  const currentLabel = React.useMemo(() => {
    for (const folder of folders) {
      const name =
        typeof folder.name === 'string' ? folder.name : String(folder.name)
      const id =
        folder.$id?.split(':')[1]?.toLowerCase() ?? name.toLowerCase()
      if (pathname.startsWith(`/${id}`)) return name
    }
    return 'openlabs'
  }, [folders, pathname])

  return (
    <>
      <header className="bg-background sticky top-0 z-(--z-header) flex h-14 items-center gap-2 border-b px-4 md:hidden">
        <Link href="/" className="flex items-center gap-2" aria-label="openlabs home">
          <span className="bg-primary text-primary-foreground flex size-8 items-center justify-center">
            <Logo className="size-6" />
          </span>
          <span className="font-mono text-sm tracking-wide">
            openlabs:{currentLabel}
          </span>
        </Link>
        <span className="flex-1" />
        <button
          type="button"
          onClick={() => {
            setSearching((v) => !v)
            setOpen(false)
          }}
          className="focus-ring text-muted-foreground hover:text-foreground hover:bg-accent flex size-10 items-center justify-center transition-[color,background-color] duration-[var(--duration-fast)] ease-[var(--ease-out)] active:scale-[0.96]"
          aria-label="Search"
        >
          <SearchIcon className="size-4" />
        </button>
        <button
          type="button"
          onClick={() => {
            setOpen((v) => !v)
            setSearching(false)
          }}
          className="focus-ring text-muted-foreground hover:text-foreground hover:bg-accent flex size-10 items-center justify-center font-mono text-xs transition-[color,background-color] duration-[var(--duration-fast)] ease-[var(--ease-out)] active:scale-[0.96]"
          aria-label="Menu"
        >
          <span className={cn('icon-swap', (open || searching) && 'is-on')}>
            <MenuIcon data-icon="off" className="size-4" />
            <span data-icon="on" aria-hidden="true">Esc</span>
          </span>
        </button>
      </header>

      <Drawer.Root
        direction="top"
        open={searching}
        onOpenChange={setSearching}
        modal={false}
      >
        <Drawer.Portal>
          <Drawer.Overlay className="cctv-backdrop fixed inset-0 top-14 z-(--z-mobile-nav)" />
          <Drawer.Content
            aria-label="Search labs"
            className="bg-background fixed inset-x-0 top-14 z-(--z-mobile-nav) flex flex-col outline-none md:hidden"
          >
            <div className="bg-muted flex h-14 items-center gap-3 px-4">
              <SearchIcon className="text-muted-foreground size-4" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search labs"
                className="focus-ring h-full flex-1 bg-transparent font-mono text-sm tracking-wide"
              />
            </div>
            <div className="max-h-[60vh] overflow-y-auto">
              {hasResults && (
                <SearchResults
                  results={results}
                  query={query}
                  onSelect={(url) => router.push(url)}
                />
              )}
              {isEmpty && <NoResults query={query} />}
            </div>
          </Drawer.Content>
        </Drawer.Portal>
      </Drawer.Root>

      <Drawer.Root
        direction="top"
        open={open}
        onOpenChange={setOpen}
        modal={false}
      >
        <Drawer.Portal>
          <Drawer.Overlay className="cctv-backdrop fixed inset-0 top-14 z-(--z-mobile-nav)" />
          <Drawer.Content
            aria-label="Menu"
            className="bg-background fixed inset-x-0 top-14 z-(--z-mobile-nav) max-h-[calc(100dvh-3.5rem)] overflow-y-auto outline-none md:hidden"
          >
            <nav className="relative flex flex-col gap-1 p-4">
            {folders.map((folder) => (
              <MobileNavSection key={folder.$id} folder={folder} />
            ))}
            <div className="mt-4 flex items-center gap-2">
              <span className="font-mono text-xs tracking-wide">
                Theme
              </span>
              <span className="flex-1" />
              {themes.map((t) => {
                const Icon = t.icon
                return (
                  <button
                    key={t.name}
                    type="button"
                    onClick={() => setTheme(t.name)}
                    className={cn(
                      'focus-ring text-muted-foreground hover:text-foreground flex size-10 items-center justify-center border transition-[color,background-color,border-color] duration-[var(--duration-fast)] ease-[var(--ease-out)] active:scale-[0.96]',
                      theme === t.name
                        ? 'border-primary text-foreground'
                        : 'border-transparent hover:border-foreground/40'
                    )}
                    aria-label={t.label}
                  >
                    <Icon className="size-5" />
                  </button>
                )
              })}
            </div>
            </nav>
          </Drawer.Content>
        </Drawer.Portal>
      </Drawer.Root>
    </>
  )
}
