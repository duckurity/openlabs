'use client'

import * as React from 'react'
import { usePathname, useRouter } from 'next/navigation'
import type * as PageTree from 'fumadocs-core/page-tree'

import { SidebarSearch } from './search'
import { SearchResults } from './search-results'
import { NoResults } from './no-results'
import { SidebarSection } from './section'
import { SocialLinks } from './social-links'
import { NavAside } from '../nav-aside'
import { useLocalSearch, type SearchItem } from '@/hooks/use-search'

type SidebarProps = {
  tree: PageTree.Root
  searchItems: SearchItem[]
}

export function RegistrySidebar({ tree, searchItems }: SidebarProps) {
  const pathname = usePathname()
  const router = useRouter()
  const { query, setQuery, results, hasResults, isEmpty } =
    useLocalSearch(searchItems)
  const searchRef = React.useRef<HTMLInputElement>(null)

  React.useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null
      const typing =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target?.isContentEditable
      if (event.key === '/' && !typing && !event.metaKey && !event.ctrlKey) {
        event.preventDefault()
        searchRef.current?.focus()
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [])

  const folders = tree.children.filter(
    (child): child is PageTree.Folder => child.type === 'folder'
  )

  const currentFolder = folders.find((folder) => {
    const folderName =
      typeof folder.name === 'string' ? folder.name : String(folder.name)
    const sectionId =
      folder.$id?.split(':')[1]?.toLowerCase() ?? folderName.toLowerCase()
    return pathname.startsWith(`/${sectionId}`)
  })

  const handleSelect = React.useCallback(
    (url: string) => {
      router.push(url)
      setQuery('')
    },
    [router, setQuery]
  )

  const renderContent = () => {
    if (hasResults) {
      return (
        <SearchResults results={results} query={query} onSelect={handleSelect} />
      )
    }
    if (isEmpty) {
      return <NoResults query={query} />
    }
    const folder = currentFolder ?? folders[0]
    if (!folder) return null
    return (
      <nav className="bg-accent/70 flex flex-col overflow-x-hidden overflow-y-auto [scrollbar-gutter:stable]">
        <SidebarSection folder={folder} defaultOpen />
      </nav>
    )
  }

  return (
    <div className="sticky top-0 hidden h-screen shrink-0 gap-1 [grid-area:sidebar] md:flex">
      <NavAside />
      <div className="w-sidebar-width flex flex-col gap-1 text-sm">
        <SidebarSearch query={query} setQuery={setQuery} inputRef={searchRef} />
        {renderContent()}
        <div className="bg-muted flex-1" />
        <SocialLinks />
      </div>
    </div>
  )
}
