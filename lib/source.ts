import { loader } from 'fumadocs-core/source'
import { docs } from 'fumadocs-mdx:collections/server'
import type { InferPageType } from 'fumadocs-core/source'

export const source = loader({
  baseUrl: '/',
  source: docs.toFumadocsSource(),
})

export type LabPage = InferPageType<typeof source>

/* Plain card data. Pages carry functions (body, getText) that cannot
   cross into client components, so grids receive this shape. */
export type LabCardData = {
  url: string
  slug: string
  title: string
  description?: string
  track?: Track
  difficulty?: Difficulty
  port?: string
}

export function toLabCardData(page: LabPage): LabCardData {
  return {
    url: page.url,
    slug: page.slugs[page.slugs.length - 1],
    title: page.data.title,
    description: page.data.description,
    track: page.data.track,
    difficulty: page.data.difficulty,
    port: page.data.port,
  }
}

export const TRACKS = ['web', 'binary', 'crypto', 'network', 'osint'] as const
export type Track = (typeof TRACKS)[number]

export const DIFFICULTIES = ['easy', 'medium', 'hard', 'insane'] as const
export type Difficulty = (typeof DIFFICULTIES)[number]

export function isLabPage(page: LabPage): boolean {
  return page.slugs[0] === 'labs' && page.slugs.length > 1
}

export function getLabs(): LabPage[] {
  return source
    .getPages()
    .filter(isLabPage)
    .sort((a, b) => a.data.title.localeCompare(b.data.title))
}

export function getRelatedLabs(current: LabPage, limit = 3): LabPage[] {
  const labs = getLabs().filter((page) => page.url !== current.url)
  const sameTrack = labs.filter(
    (page) => page.data.track && page.data.track === current.data.track
  )
  const rest = labs.filter(
    (page) => page.data.track !== current.data.track
  )
  return [...sameTrack, ...rest].slice(0, limit)
}
