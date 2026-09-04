/**
 * Structured data builders. One shared helper per schema family so
 * head markup and visible content never drift apart.
 *
 * Notes on eligibility:
 * - BreadcrumbList is the only guaranteed rich-result win here.
 * - TechArticle/Article earn article display; LearningResource rides
 *   along as a dual type only, never standalone.
 * - FAQPage earns no search display since the 2026 sunset. It ships
 *   for machine parsing of the visible FAQ only.
 */

import { source } from './source'
import { APP_BASE_URL } from './constants'

const PUBLISHER = {
  '@type': 'Organization',
  name: 'openlabs',
  url: APP_BASE_URL,
}

const PROFICIENCY: Record<string, string> = {
  easy: 'Beginner',
  medium: 'Intermediate',
  hard: 'Advanced',
  insane: 'Expert',
}

function titleCase(slug: string): string {
  return slug.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export interface Crumb {
  name: string
  url?: string
}

export function breadcrumbs(slugs: string[]): Crumb[] {
  const crumbs: Crumb[] = [{ name: 'Home', url: `${APP_BASE_URL}/` }]
  slugs.forEach((_, i) => {
    const prefix = slugs.slice(0, i + 1)
    const target = source.getPage(prefix)
    crumbs.push({
      name: target?.data.title ?? titleCase(slugs[i]),
      url: target ? `${APP_BASE_URL}${target.url}` : undefined,
    })
  })
  return crumbs
}

export function breadcrumbJsonLd(slugs: string[]): Record<string, unknown> | null {
  if (slugs.length === 0) return null
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: breadcrumbs(slugs).map((crumb, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: crumb.name,
      ...(crumb.url ? { item: crumb.url } : {}),
    })),
  }
}

interface ArticleInput {
  url: string
  title: string
  description?: string
  image?: string
  dateModified?: string
  keywords?: { primary?: string; secondary?: string[] }
  section?: string
}

function articleBase(input: ArticleInput): Record<string, unknown> {
  const keywords = [
    ...(input.keywords?.primary ? [input.keywords.primary] : []),
    ...(input.keywords?.secondary ?? []),
  ]
  return {
    headline: input.title,
    description: input.description,
    mainEntityOfPage: `${APP_BASE_URL}${input.url}`,
    ...(input.image ? { image: `${APP_BASE_URL}${input.image}` } : {}),
    ...(input.dateModified ? { dateModified: input.dateModified } : {}),
    ...(keywords.length > 0 ? { keywords: keywords.join(', ') } : {}),
    ...(input.section ? { articleSection: input.section } : {}),
    inLanguage: 'en',
    author: { ...PUBLISHER },
    publisher: { ...PUBLISHER },
  }
}

export interface LabInput extends ArticleInput {
  authorName?: string
  authorUrl?: string
  datePublished?: string
  difficulty?: string
  intent?: string
}

export function labJsonLd(input: LabInput): Record<string, unknown> {
  return {
    '@context': 'https://schema.org',
    '@type': ['TechArticle', 'LearningResource'],
    ...articleBase(input),
    ...(input.authorName
      ? { author: { '@type': 'Person', name: input.authorName, ...(input.authorUrl ? { url: input.authorUrl } : {}) } }
      : {}),
    ...(input.datePublished ? { datePublished: input.datePublished } : {}),
    ...(input.difficulty && PROFICIENCY[input.difficulty]
      ? { proficiencyLevel: PROFICIENCY[input.difficulty] }
      : {}),
    ...(input.intent ? { teaches: input.intent } : {}),
    isAccessibleForFree: true,
  }
}

export function guideJsonLd(input: ArticleInput & { technical?: boolean }): Record<string, unknown> {
  return {
    '@context': 'https://schema.org',
    '@type': input.technical ? 'TechArticle' : 'Article',
    ...articleBase(input),
  }
}

export function labsIndexJsonLd(
  url: string,
  title: string,
  description: string | undefined,
  labs: { url: string; title: string }[]
): Record<string, unknown> {
  return {
    '@context': 'https://schema.org',
    '@type': 'ItemList',
    name: title,
    description,
    url: `${APP_BASE_URL}${url}`,
    itemListElement: labs.map((lab, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: lab.title,
      url: `${APP_BASE_URL}${lab.url}`,
    })),
  }
}

function plainText(markdown: string): string {
  return markdown
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/`([^`]*)`/g, '$1')
    .replace(/[*_~]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

/** Extract verbatim h2 question + answer pairs from raw Markdown. */
export function faqPairs(raw: string): { question: string; answer: string }[] {
  const pairs: { question: string; answer: string }[] = []
  const lines = raw.split('\n')
  let current: { question: string; body: string[] } | null = null
  const flush = () => {
    if (!current) return
    const answer = plainText(current.body.join('\n'))
    if (current.question && answer) {
      pairs.push({ question: current.question, answer })
    }
    current = null
  }
  for (const line of lines) {
    const heading = line.match(/^##\s+(.*)$/)
    if (heading) {
      flush()
      current = { question: plainText(heading[1]), body: [] }
    } else if (current && !line.startsWith('---')) {
      current.body.push(line)
    }
  }
  flush()
  return pairs
}

export function faqJsonLd(
  url: string,
  pairs: { question: string; answer: string }[]
): Record<string, unknown> | null {
  if (pairs.length === 0) return null
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: pairs.map((pair) => ({
      '@type': 'Question',
      name: pair.question,
      acceptedAnswer: { '@type': 'Answer', text: pair.answer },
    })),
    url: `${APP_BASE_URL}${url}`,
  }
}
