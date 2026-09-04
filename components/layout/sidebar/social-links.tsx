'use client'

import GithubIcon from '@/components/icons/github'
import { AsideButton } from '../nav-aside'

const links = [
  {
    name: 'Repository',
    href: 'https://github.com/Duckurity/openlabs',
    icon: GithubIcon,
  },
]

export function SocialLinks() {
  return (
    <div className="flex gap-1">
      {links.map((link) => (
        <AsideButton key={link.name} icon={link.icon} label={link.name} asChild>
          <a
            href={link.href}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1"
          />
        </AsideButton>
      ))}
    </div>
  )
}
