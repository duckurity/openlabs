import { defineSeoConfig } from '@contentbit/core'

export default defineSeoConfig({
  pageTypes: {
    guide: {
      requiredFrontmatter: ['type', 'intent', 'keywords.primary'],
    },
    lab: {
      requiredFrontmatter: ['type', 'intent', 'keywords.primary'],
      requiredSections: [
        { id: 'brief', headings: ['Brief'] },
        { id: 'setup', headings: ['Setup'] },
        { id: 'goal', headings: ['Goal'] },
      ],
      minOutgoingLinks: 1,
    },
    technique: {
      requiredFrontmatter: ['type', 'intent', 'keywords.primary'],
      requiredSections: [
        { id: 'overview', headings: ['Overview', 'What it is'] },
        { id: 'examples', headings: ['Examples', 'In the labs'] },
        { id: 'related', headings: ['Related labs'] },
        { id: 'faq', headings: ['FAQ', 'Frequently asked questions'] },
      ],
      minOutgoingLinks: 3,
    },
  },
  pages: {
    'lab-duck-cross': {
      type: 'lab',
      key: 'lab-duck-cross',
      slug: 'labs/duck-cross',
      title: 'Duck cross',
      intent: 'Solve an easy missing-authorization lab in Docker.',
      keywords: {
        primary: 'easy IDOR lab docker',
        secondary: ['broken object level authorization practice', 'openlabs duck-cross'],
      },
      linksTo: ['technique-idor'],
    },
    'technique-idor': {
      type: 'technique',
      key: 'technique-idor',
      slug: 'technique/idor',
      title: 'Broken object-level authorization (IDOR)',
      intent: 'Learn what IDOR is and which labs exercise it.',
      keywords: {
        primary: 'IDOR practice lab',
        secondary: ['broken object level authorization explained', 'access control lab'],
      },
      linksTo: ['lab-duck-cross'],
    },
  },
})
