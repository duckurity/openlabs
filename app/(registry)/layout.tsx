import type { CSSProperties } from 'react'
import { source } from '@/lib/source'
import { TreeContextProvider } from 'fumadocs-ui/contexts/tree'
import {
  LayoutContextProvider,
  LayoutBody,
} from '@/components/layout/docs/client'
import { RegistrySidebar } from '@/components/layout/sidebar'
import { MobileNav } from '@/components/layout/mobile-nav'
import { CommandPalette } from '@/components/layout/command-palette'

export default function Layout({ children }: LayoutProps<'/'>) {
  const searchItems = source.getPages().map((page) => ({
    url: page.url,
    title: page.data.title,
    description: page.data.description,
  }))

  return (
    <TreeContextProvider tree={source.pageTree}>
      <LayoutContextProvider>
        <MobileNav tree={source.pageTree} searchItems={searchItems} />
        <LayoutBody
          style={
            {
              '--fd-sidebar-width':
                'calc(var(--aside-width) + var(--spacing) + var(--sidebar-width))',
            } as CSSProperties
          }
        >
          <RegistrySidebar tree={source.pageTree} searchItems={searchItems} />
          {children}
        </LayoutBody>
      </LayoutContextProvider>
      <CommandPalette items={searchItems} />
    </TreeContextProvider>
  )
}
