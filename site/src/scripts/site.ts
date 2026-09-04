// openlabs site interactions. No dependencies. Only transform, opacity,
// and color change. Motion stays off for reduced-motion users.

type ThemeMode = 'light' | 'dark' | 'system';

const THEME_KEY = 'openlabs-theme';

function currentTheme(): ThemeMode {
  try {
    const saved = window.localStorage.getItem(THEME_KEY);
    if (saved === 'light' || saved === 'dark' || saved === 'system') return saved;
  } catch {
    /* storage unavailable */
  }
  return 'system';
}

function applyTheme(mode: ThemeMode): void {
  const root = document.documentElement;
  if (mode === 'system') root.removeAttribute('data-theme');
  else root.setAttribute('data-theme', mode);
  document.querySelectorAll<HTMLButtonElement>('[data-theme-toggle]').forEach((btn) => {
    const label = mode === 'system' ? 'System' : mode === 'light' ? 'Light' : 'Dark';
    btn.setAttribute('data-mode', mode === 'system' ? systemGuess() : mode);
    btn.setAttribute('aria-label', `Theme: ${label}. Press to change.`);
    const text = btn.querySelector('.theme-toggle__label');
    if (text) text.textContent = label;
  });
}

function systemGuess(): 'light' | 'dark' {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function nextTheme(mode: ThemeMode): ThemeMode {
  if (mode === 'light') return 'dark';
  if (mode === 'dark') return 'system';
  return 'light';
}

function initTheme(): void {
  applyTheme(currentTheme());
  document.querySelectorAll<HTMLButtonElement>('[data-theme-toggle]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const mode = nextTheme(currentTheme());
      try {
        window.localStorage.setItem(THEME_KEY, mode);
      } catch {
        /* storage unavailable */
      }
      applyTheme(mode);
    });
  });
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (currentTheme() === 'system') applyTheme('system');
  });
}

function initReveal(): void {
  const items = Array.from(document.querySelectorAll<HTMLElement>('[data-reveal]'));
  if (items.length === 0) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    items.forEach((el) => el.classList.add('is-visible'));
    return;
  }
  if (!('IntersectionObserver' in window)) {
    items.forEach((el) => el.classList.add('is-visible'));
    return;
  }
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          io.unobserve(entry.target);
        }
      });
    },
    { rootMargin: '0px 0px -8% 0px', threshold: 0.12 }
  );
  items.forEach((el) => io.observe(el));
}

function initFilters(): void {
  const grid = document.querySelector<HTMLElement>('[data-lab-grid]');
  if (!grid) return;
  const cards = Array.from(grid.querySelectorAll<HTMLElement>('[data-lab-card]'));
  const empty = document.querySelector<HTMLElement>('[data-lab-empty]');
  const count = document.querySelector<HTMLElement>('[data-lab-count]');
  const search = document.querySelector<HTMLInputElement>('[data-lab-search]');
  const clear = document.querySelector<HTMLButtonElement>('[data-lab-clear]');
  let track = 'all';
  let difficulty = 'all';

  function matches(card: HTMLElement): boolean {
    const okTrack = track === 'all' || card.dataset.track === track;
    const okDiff = difficulty === 'all' || card.dataset.difficulty === difficulty;
    const q = (search?.value ?? '').trim().toLowerCase();
    const okQuery =
      q.length === 0 ||
      `${card.dataset.title ?? ''} ${card.dataset.tagline ?? ''} ${card.dataset.track ?? ''}`.toLowerCase().includes(q);
    return okTrack && okDiff && okQuery;
  }

  function render(): void {
    let visible = 0;
    cards.forEach((card) => {
      const show = matches(card);
      card.hidden = !show;
      if (show) visible += 1;
    });
    if (empty) empty.hidden = visible !== 0;
    if (count) {
      const total = cards.length;
      count.textContent = `${visible} of ${total} ${total === 1 ? 'lab' : 'labs'}`;
    }
  }

  document.querySelectorAll<HTMLButtonElement>('[data-filter-track]').forEach((btn) => {
    btn.addEventListener('click', () => {
      track = btn.dataset.filterTrack ?? 'all';
      document
        .querySelectorAll<HTMLButtonElement>('[data-filter-track]')
        .forEach((b) => b.setAttribute('aria-pressed', String(b === btn)));
      render();
    });
  });
  document.querySelectorAll<HTMLButtonElement>('[data-filter-difficulty]').forEach((btn) => {
    btn.addEventListener('click', () => {
      difficulty = btn.dataset.filterDifficulty ?? 'all';
      document
        .querySelectorAll<HTMLButtonElement>('[data-filter-difficulty]')
        .forEach((b) => b.setAttribute('aria-pressed', String(b === btn)));
      render();
    });
  });
  search?.addEventListener('input', render);
  clear?.addEventListener('click', () => {
    track = 'all';
    difficulty = 'all';
    if (search) search.value = '';
    document
      .querySelectorAll<HTMLButtonElement>('[data-filter-track]')
      .forEach((b) => b.setAttribute('aria-pressed', String((b.dataset.filterTrack ?? 'all') === 'all')));
    document
      .querySelectorAll<HTMLButtonElement>('[data-filter-difficulty]')
      .forEach((b) => b.setAttribute('aria-pressed', String((b.dataset.filterDifficulty ?? 'all') === 'all')));
    render();
    search?.focus();
  });

  // Track rows elsewhere on the page can jump into a filtered grid.
  document.querySelectorAll<HTMLButtonElement>('[data-track-jump]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const id = btn.dataset.trackJump ?? 'all';
      track = id;
      document
        .querySelectorAll<HTMLButtonElement>('[data-filter-track]')
        .forEach((b) => b.setAttribute('aria-pressed', String((b.dataset.filterTrack ?? 'all') === id)));
      render();
      document.querySelector('#labs')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });

  render();
}

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'absolute';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    let ok = false;
    try {
      ok = document.execCommand('copy');
    } catch {
      ok = false;
    }
    ta.remove();
    return ok;
  }
}

function initCopy(): void {
  document.querySelectorAll<HTMLButtonElement>('[data-copy]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const target = btn.getAttribute('data-copy-target');
      const inline = btn.getAttribute('data-copy');
      let text = inline && inline.length > 0 ? inline : '';
      if (target) {
        const node = document.querySelector(target);
        if (node instanceof HTMLElement) text = node.innerText;
        else if (node) text = node.textContent ?? '';
      }
      if (!text) return;
      const ok = await copyText(text.trim());
      if (!ok) return;
      btn.setAttribute('data-copied', 'true');
      const label = btn.querySelector('[data-copy-label]');
      const prev = label?.textContent ?? btn.textContent ?? '';
      if (label) label.textContent = 'Copied';
      else btn.textContent = 'Copied';
      window.setTimeout(() => {
        btn.setAttribute('data-copied', 'false');
        if (label) label.textContent = prev;
        else btn.textContent = prev;
      }, 1400);
    });
  });
}

function formatTime(total: number): string {
  if (!Number.isFinite(total) || total < 0) return '0:00';
  const s = Math.floor(total);
  const m = Math.floor(s / 60);
  const rest = s % 60;
  return `${m}:${rest < 10 ? '0' : ''}${rest}`;
}

function initListen(): void {
  document.querySelectorAll<HTMLElement>('[data-listen]').forEach((root) => {
    const audio = root.querySelector<HTMLAudioElement>('audio');
    const play = root.querySelector<HTMLButtonElement>('[data-listen-play]');
    const track = root.querySelector<HTMLElement>('[data-listen-track]');
    const fill = root.querySelector<HTMLElement>('[data-listen-fill]');
    const cur = root.querySelector<HTMLElement>('[data-listen-cur]');
    const dur = root.querySelector<HTMLElement>('[data-listen-dur]');
    if (!audio || !play) return;

    function paint(): void {
      const pct = audio.duration > 0 ? (audio.currentTime / audio.duration) * 100 : 0;
      if (fill) fill.style.width = `${pct}%`;
      if (cur) cur.textContent = formatTime(audio.currentTime);
      if (dur) dur.textContent = formatTime(audio.duration);
      track?.setAttribute('aria-valuenow', String(Math.round(pct)));
    }
    function setPlaying(on: boolean): void {
      root.classList.toggle('is-playing', on);
      play.setAttribute('aria-pressed', String(on));
      play.setAttribute('aria-label', on ? 'Pause the welcome' : 'Play the welcome');
    }

    play.addEventListener('click', () => {
      if (audio.paused) void audio.play().catch(() => undefined);
      else audio.pause();
    });
    audio.addEventListener('play', () => setPlaying(true));
    audio.addEventListener('pause', () => setPlaying(false));
    audio.addEventListener('loadedmetadata', paint);
    audio.addEventListener('timeupdate', paint);
    audio.addEventListener('ended', () => {
      paint();
      setPlaying(false);
    });
    track?.addEventListener('click', (event) => {
      const rect = track.getBoundingClientRect();
      const ratio = Math.min(Math.max((event.clientX - rect.left) / rect.width, 0), 1);
      if (audio.duration > 0) audio.currentTime = ratio * audio.duration;
      paint();
    });
    track?.addEventListener('keydown', (event) => {
      if (!(event instanceof KeyboardEvent)) return;
      const step = (audio.duration || 0) / 20;
      if (event.key === 'ArrowRight') {
        audio.currentTime = Math.min(audio.currentTime + step, audio.duration || 0);
        event.preventDefault();
      } else if (event.key === 'ArrowLeft') {
        audio.currentTime = Math.max(audio.currentTime - step, 0);
        event.preventDefault();
      }
      paint();
    });
    paint();
  });
}

function initHeader(): void {
  const header = document.querySelector<HTMLElement>('[data-site-header]');
  if (!header) return;
  function onScroll(): void {
    header.toggleAttribute('data-scrolled', window.scrollY > 8);
  }
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });
}

initTheme();
initReveal();
initFilters();
initCopy();
initListen();
initHeader();
