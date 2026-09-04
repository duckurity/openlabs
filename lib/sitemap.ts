import FlaskIcon from '@/components/icons/flask'
import CubeIcon from '@/components/icons/3d-cube'
import FileIcon from '@/components/icons/file'
import TerminalWithCursorIcon from '@/components/icons/terminal-w-cursor'
import type { SVGProps } from 'react'

type SitemapItem = {
  label: string
  href: string
  icon: React.ComponentType<SVGProps<SVGSVGElement>>
}

export const sitemap: SitemapItem[] = [
  {
    label: 'Labs',
    href: '/labs',
    icon: FlaskIcon,
  },
  {
    label: 'Tracks',
    href: '/tracks',
    icon: CubeIcon,
  },
  {
    label: 'How to play',
    href: '/play',
    icon: TerminalWithCursorIcon,
  },
  {
    label: 'Rules',
    href: '/rules',
    icon: FileIcon,
  },
]
