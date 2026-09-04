import lastModified from 'fumadocs-mdx/plugins/last-modified'
import rehypePrettyCode from 'rehype-pretty-code'
import { z } from 'zod'
import {
  defineConfig,
  defineDocs,
  frontmatterSchema,
} from 'fumadocs-mdx/config'

import { transformers } from './lib/mdx'
import { cn } from '@/lib/utils'

export const docs = defineDocs({
  dir: 'content',
  docs: {
    schema: frontmatterSchema.extend({
      track: z
        .enum(['web', 'binary', 'crypto', 'network', 'osint'])
        .optional(),
      difficulty: z
        .enum(['easy', 'medium', 'hard', 'insane'])
        .optional(),
      port: z.string().optional(),
      verified: z.boolean().optional(),
      author_name: z.string().optional(),
      author_url: z.string().optional(),
      author_avatar: z.string().optional(),
      author_date: z.string().optional(),
      type: z.string().optional(),
      key: z.string().optional(),
      slug: z.string().optional(),
      intent: z.string().optional(),
      keywords: z
        .object({
          primary: z.string().optional(),
          secondary: z.array(z.string()).optional(),
        })
        .optional(),
      linksTo: z.array(z.string()).optional(),
    }),
    postprocess: {
      includeProcessedMarkdown: true,
    },
  },
})

export default defineConfig({
  mdxOptions: {
    rehypePlugins: (plugins) => {
      plugins.shift()
      plugins.push([
        rehypePrettyCode,
        {
          theme: {
            dark: 'github-dark',
            light: 'github-light-default',
          },
          transformers,
          onVisitTitle(node: { properties: Record<string, unknown> }) {
            node.properties['class'] = cn(
              'not-prose',
              node.properties['class']?.toString()
            )
          },
        },
      ])
      return plugins
    },
  },
  plugins: [lastModified()],
})
