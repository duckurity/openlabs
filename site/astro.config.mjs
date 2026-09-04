import { defineConfig } from 'astro/config';

// The site is deployed to GitHub Pages from the repo root, under the
// repository name. `site` + `base` keep asset and link URLs correct.
export default defineConfig({
  site: 'https://Duckurity.github.io',
  base: '/openlabs',
  output: 'static',
  compressHTML: true,
  build: {
    inlineStylesheets: 'auto',
  },
  image: {
    service: { entrypoint: 'astro/assets/services/noop' },
  },
});