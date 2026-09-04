import { defineContentConfig } from '@contentbit/core'

export default defineContentConfig({
  content: 'content/**/*.mdx',
  genericBlocks: true,
  seo: './contentbit.seo.config.ts',
})
