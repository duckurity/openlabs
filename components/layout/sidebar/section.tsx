'use client'

import * as React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import type * as PageTree from 'fumadocs-core/page-tree'
import { cn } from '@/lib/utils'
import CubeIcon from '@/components/icons/3d-cube'
import TerminalWithCursorIcon from '@/components/icons/terminal-w-cursor'
import FileIcon from '@/components/icons/file'
import FlaskIcon from '@/components/icons/flask'
import { CollapsibleSection } from './collapsible-section'

const sectionIcons: Record<
  string,
  React.ComponentType<React.SVGProps<SVGSVGElement>>
> = {
  labs: FlaskIcon,
  tracks: CubeIcon,
  play: TerminalWithCursorIcon,
  rules: FileIcon,
}

type SidebarSectionProps = {
  folder: PageTree.Folder
  defaultOpen?: boolean
}

export function SidebarSection({ folder, defaultOpen = true }: SidebarSectionProps) {
  const pathname = usePathname()

  const folderName =
    typeof folder.name === 'string' ? folder.name : String(folder.name)
  const sectionId =
    folder.$id?.split(':')[1]?.toLowerCase() ?? folderName.toLowerCase()
  const Icon = sectionIcons[sectionId] ?? CubeIcon
  const isActive = pathname.startsWith(`/${sectionId}`)

  return (
    <CollapsibleSection
      name={folderName}
      icon={Icon}
      defaultOpen={defaultOpen}
      isActive={isActive}
    >
      <div className="border-border ml-4 flex flex-col border-l-2">
        {folder.children.map((child) => {
          if (child.type !== 'page') return null
          const isItemActive = pathname === child.url
          return (
            <Link
              key={child.url}
              href={child.url}
              className={cn(
                'focus-ring -ml-[2px] flex items-center gap-2 px-4 py-1.5 font-mono text-sm tracking-wide transition-[color,background-color,border-color] duration-[var(--duration-normal)] ease-[var(--ease-out)]',
                isItemActive
                  ? 'text-foreground border-foreground bg-accent border-l-4 pl-6 font-medium'
                  : 'text-muted-foreground hover:text-foreground hover:border-foreground/50 focus-visible:text-foreground focus-visible:bg-accent border-l-2'
              )}
            >
              <span className="truncate">{child.name}</span>
            </Link>
          )
        })}
      </div>
    </CollapsibleSection>
  )
}
