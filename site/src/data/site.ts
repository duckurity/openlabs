// Shared, hand-sourced data for the site. Tracks, difficulty tiers, and the
// lab catalogue. This is the single source used by both the landing grid and
// the detail pages so labels never drift.

export interface Track {
  id: 'web' | 'binary' | 'crypto' | 'network' | 'osint';
  label: string;
  focus: string;
}

export const TRACKS: Track[] = [
  { id: 'web', label: 'Web', focus: 'injection, broken access control, auth bypass, SSRF' },
  { id: 'binary', label: 'Binary', focus: 'memory corruption, exploitation, reverse engineering' },
  { id: 'crypto', label: 'Crypto', focus: 'weak primitives, protocol misuse, implementation faults' },
  { id: 'network', label: 'Network', focus: 'protocol abuse, traffic analysis, pivoting' },
  { id: 'osint', label: 'OSINT', focus: 'recon, source analysis, signature tracing' },
];

export type Difficulty = 'easy' | 'medium' | 'hard' | 'insane';

export const DIFFICULTY_ORDER: Difficulty[] = ['easy', 'medium', 'hard', 'insane'];

export const DIFFICULTY_META: Record<Difficulty, string> = {
  easy: 'one vector, minimal recon, the brief points at the surface',
  medium: 'chained steps, some enumeration, the vector needs a decision',
  hard: 'multiple systems or stages, custom tooling, dead ends that punish assumptions',
  insane: 'research-level, an original technique, no public reference walkthrough',
};

export function trackById<T extends Track[]>(tracks: T, id: string): Track | undefined {
  return tracks.find((t) => t.id === id);
}

export const WELCOME_AUDIO_URL =
  'https://raw.githubusercontent.com/Duckurity/openlabs/main/.github/assets/audio/welcome.mp3';