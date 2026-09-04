import { defineCollection, z } from 'astro:content';

const labs = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    tagline: z.string(),
    track: z.enum(['web', 'binary', 'crypto', 'network', 'osint']),
    difficulty: z.enum(['easy', 'medium', 'hard', 'insane']),
    port: z.string(),
    // Short story a player reads to know why the service exists.
    brief: z.string(),
    // What to do. Plain, no hidden agenda.
    goal: z.string(),
    // Ordered setup steps, each a shell command or a plain instruction.
    setup: z.array(z.union([z.string(), z.object({ text: z.string() })])),
    // Ordered narrative steps for the solve path.
    steps: z.array(z.object({ text: z.string() })),
    flag: z.object({
      format: z.string(),
      location: z.string(),
    }),
    date: z.coerce.string().optional(),
  }),
});

export const collections = { labs };