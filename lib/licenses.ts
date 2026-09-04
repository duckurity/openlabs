/**
 * SPDX license metadata for the license badge.
 *
 * Trimmed to the licenses this site actually shows, plus a fallback
 * for anything else. Full SPDX tables live upstream.
 */

export interface LicenseInfo {
  spdxId: string
  name: string
  description: string
  osiApproved: boolean
  category: 'permissive' | 'copyleft' | 'weak-copyleft' | 'public-domain' | 'proprietary' | 'other'
  url: string
}

const KNOWN_LICENSES: Record<string, LicenseInfo> = {
  'Apache-2.0': {
    spdxId: 'Apache-2.0',
    name: 'Apache License 2.0',
    description: 'Permissive license with patent protection. Requires preserved notices.',
    osiApproved: true,
    category: 'permissive',
    url: 'https://choosealicense.com/licenses/apache-2.0/',
  },
  MIT: {
    spdxId: 'MIT',
    name: 'MIT License',
    description: 'Short permissive license. Commercial use, modification, and distribution allowed.',
    osiApproved: true,
    category: 'permissive',
    url: 'https://choosealicense.com/licenses/mit/',
  },
  'CC-BY-4.0': {
    spdxId: 'CC-BY-4.0',
    name: 'Creative Commons Attribution 4.0',
    description: 'Free culture license. Share and adapt with attribution.',
    osiApproved: false,
    category: 'other',
    url: 'https://creativecommons.org/licenses/by/4.0/',
  },
}

export function resolveLicense(spdxId: string): LicenseInfo {
  const normalized = spdxId.replace(/-only$/i, '').replace(/-or-later$/i, '')
  const direct = KNOWN_LICENSES[normalized] ?? KNOWN_LICENSES[spdxId]
  if (direct) return direct

  const upper = normalized.toUpperCase()
  for (const [key, value] of Object.entries(KNOWN_LICENSES)) {
    if (key.toUpperCase() === upper) return value
  }

  return {
    spdxId,
    name: spdxId,
    description: 'License details not available.',
    osiApproved: false,
    category: 'other',
    url: `https://spdx.org/licenses/${encodeURIComponent(spdxId)}.html`,
  }
}

/** Category display config, mapped to the site status tokens. */
export const CATEGORY_CONFIG: Record<
  LicenseInfo['category'],
  { label: string; className: string }
> = {
  permissive: {
    label: 'Permissive',
    className: 'bg-(--status-success-tint) text-(--status-success-strong)',
  },
  copyleft: {
    label: 'Copyleft',
    className: 'bg-(--status-warning-tint) text-(--status-warning-strong)',
  },
  'weak-copyleft': {
    label: 'Weak copyleft',
    className: 'bg-(--status-info-tint) text-(--status-info-strong)',
  },
  'public-domain': {
    label: 'Public domain',
    className: 'bg-(--status-tip-tint) text-(--status-tip-strong)',
  },
  proprietary: {
    label: 'Proprietary',
    className: 'bg-(--status-error-tint) text-(--status-error-strong)',
  },
  other: {
    label: 'Other',
    className: 'bg-muted text-muted-foreground',
  },
}
