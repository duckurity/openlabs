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
  // Flip lands instantly: hold transitions for one frame across the swap.
  root.classList.add('theming-flip');
  if (mode === 'system') root.removeAttribute('data-theme');
  else root.setAttribute('data-theme', mode);
  void root.offsetHeight;
  requestAnimationFrame(() => root.classList.remove('theming-flip'));
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
  let lastPop = 0;

  function matches(card: HTMLElement): boolean {
    const okTrack = track === 'all' || card.dataset.track === track;
    const okDiff = difficulty === 'all' || card.dataset.difficulty === difficulty;
    const q = (search?.value ?? '').trim().toLowerCase();
    const okQuery =
      q.length === 0 ||
      `${card.dataset.title ?? ''} ${card.dataset.tagline ?? ''} ${card.dataset.track ?? ''}`.toLowerCase().includes(q);
    return okTrack && okDiff && okQuery;
  }

  // Digits resolve one by one, never as a block. Skipped for rapid
  // repeats, reduced motion, and screen-reader chatter (aria-live stays).
  function paintCount(visible: number, total: number): void {
    if (!count) return;
    const text = `${visible} of ${total} ${total === 1 ? 'lab' : 'labs'}`;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const now = Date.now();
    if (reduced || now - lastPop <= 150 || count.dataset.full === text) {
      count.textContent = text;
      count.dataset.full = text;
      return;
    }
    lastPop = now;
    count.dataset.full = text;
    count.textContent = '';
    count.classList.add('digit-pop');
    const head = String(visible);
    head.split('').forEach((digit, i) => {
      const tick = document.createElement('span');
      tick.className = 'tick';
      const inner = document.createElement('span');
      inner.textContent = digit;
      inner.style.animationDelay = `${i * 50}ms`;
      tick.append(inner);
      count.append(tick);
    });
    count.append(document.createTextNode(text.slice(head.length)));
    count.classList.remove('armed');
    void count.offsetWidth;
    count.classList.add('armed');
  }

  function render(source: 'chips' | 'search' | 'clear' | 'jump' | 'init'): void {
    let visible = 0;
    cards.forEach((card) => {
      const show = matches(card);
      card.hidden = !show;
      if (show) visible += 1;
    });
    const wasEmpty = empty ? !empty.hidden : false;
    if (empty) empty.hidden = visible !== 0;
    // One shake when a pressed filter empties the grid. Never while typing.
    if (empty && !empty.hidden && !wasEmpty && (source === 'chips' || source === 'jump')) {
      const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const body = empty.querySelector<HTMLElement>('[data-lab-empty-body]');
      if (!reduced && body) {
        body.classList.remove('shake');
        void body.offsetWidth;
        body.classList.add('shake');
      }
    }
    paintCount(visible, cards.length);
  }

  document.querySelectorAll<HTMLButtonElement>('[data-filter-track]').forEach((btn) => {
    btn.addEventListener('click', () => {
      track = btn.dataset.filterTrack ?? 'all';
      document
        .querySelectorAll<HTMLButtonElement>('[data-filter-track]')
        .forEach((b) => b.setAttribute('aria-pressed', String(b === btn)));
      render('chips');
    });
  });
  document.querySelectorAll<HTMLButtonElement>('[data-filter-difficulty]').forEach((btn) => {
    btn.addEventListener('click', () => {
      difficulty = btn.dataset.filterDifficulty ?? 'all';
      document
        .querySelectorAll<HTMLButtonElement>('[data-filter-difficulty]')
        .forEach((b) => b.setAttribute('aria-pressed', String(b === btn)));
      render('chips');
    });
  });
  search?.addEventListener('input', () => render('search'));
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
    render('clear');
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
      render('jump');
      const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      document
        .querySelector('#labs')
        ?.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' });
    });
  });

  render('init');

  initChipRoving();
  initSearchKeys(search);
}

// Roving tabindex across a chip group. Arrows move focus, Home/End jump.
// Selection stays on Space/Enter so exploring never filters by accident.
function initChipRoving(): void {
  ['[data-filter-track]', '[data-filter-difficulty]'].forEach((selector) => {
    const group = Array.from(
      document.querySelectorAll<HTMLButtonElement>(selector)
    );
    if (group.length === 0) return;
    function order(focused: HTMLButtonElement): void {
      group.forEach((btn) => btn.setAttribute('tabindex', btn === focused ? '0' : '-1'));
    }
    const start = group.find((btn) => btn.getAttribute('aria-pressed') === 'true') ?? group[0];
    if (start) order(start);
    group.forEach((btn, i) => {
      btn.addEventListener('focus', () => order(btn));
      btn.addEventListener('keydown', (event) => {
        if (!(event instanceof KeyboardEvent)) return;
        let next: number | null = null;
        if (event.key === 'ArrowRight' || event.key === 'ArrowDown') next = (i + 1) % group.length;
        else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') next = (i - 1 + group.length) % group.length;
        else if (event.key === 'Home') next = 0;
        else if (event.key === 'End') next = group.length - 1;
        if (next === null) return;
        const target = group[next];
        if (target) {
          event.preventDefault();
          target.focus();
        }
      });
    });
  });
}

// `/` focuses search from anywhere except a field. Escape backs out.
function initSearchKeys(search: HTMLInputElement | null | undefined): void {
  document.addEventListener('keydown', (event) => {
    if (!(event instanceof KeyboardEvent)) return;
    const target = event.target as HTMLElement | null;
    const inField =
      target instanceof HTMLInputElement ||
      target instanceof HTMLTextAreaElement ||
      target instanceof HTMLSelectElement ||
      (target !== null && target.isContentEditable);
    if (event.key === '/' && !inField && !event.ctrlKey && !event.metaKey && !event.altKey) {
      if (search) {
        event.preventDefault();
        search.focus();
      }
    } else if (event.key === 'Escape' && search && target === search) {
      search.blur();
    }
  });
}

// Toast stack: confirmation lands, then politely withdraws. One stack,
// three deep max. Dwell pauses while the reader holds it.
function toast(message: string): void {
  const stack = document.querySelector<HTMLElement>('[data-toasts]');
  if (!stack) return;
  const el = document.createElement('div');
  el.className = 'toast';
  el.setAttribute('role', 'status');
  const mark = document.createElement('span');
  mark.className = 'toast__mark';
  mark.setAttribute('aria-hidden', 'true');
  el.append(mark, document.createTextNode(message));
  stack.append(el);
  while (stack.children.length > 3) stack.firstElementChild?.remove();
  requestAnimationFrame(() =>
    requestAnimationFrame(() => el.setAttribute('data-open', ''))
  );
  let timer = 0;
  const dismiss = () => {
    // FLIP: neighbors slide into the freed space instead of jumping.
    const siblings = Array.from(stack.children) as HTMLElement[];
    const firsts = new Map<HTMLElement, number>();
    siblings.forEach((sib) => firsts.set(sib, sib.getBoundingClientRect().top));
    el.setAttribute('data-closing', '');
    window.setTimeout(() => {
      el.remove();
      const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      if (!reduced) {
        siblings.forEach((sib) => {
          if (sib === el || !sib.isConnected) return;
          const last = sib.getBoundingClientRect().top;
          const delta = (firsts.get(sib) ?? last) - last;
          if (delta !== 0) {
            sib.animate(
              [{ transform: `translateY(${delta}px)` }, { transform: 'translateY(0)' }],
              { duration: 150, easing: 'cubic-bezier(0.77, 0, 0.175, 1)' }
            );
          }
        });
      }
    }, 200);
  };
  const dwell = () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(dismiss, 4000);
  };
  el.addEventListener('mouseenter', () => window.clearTimeout(timer));
  el.addEventListener('mouseleave', dwell);
  el.addEventListener('focusin', () => window.clearTimeout(timer));
  el.addEventListener('focusout', dwell);
  dwell();
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
      toast('Copied.');
      window.setTimeout(() => btn.setAttribute('data-copied', 'false'), 1400);
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
    const player: HTMLAudioElement = audio;
    const playButton: HTMLButtonElement = play;

    function paint(): void {
      const pct = player.duration > 0 ? (player.currentTime / player.duration) * 100 : 0;
      if (fill) fill.style.width = `${pct}%`;
      if (cur) cur.textContent = formatTime(player.currentTime);
      if (dur) dur.textContent = formatTime(player.duration);
      track?.setAttribute('aria-valuenow', String(Math.round(pct)));
    }
    function setPlaying(on: boolean): void {
      root.classList.toggle('is-playing', on);
      playButton.setAttribute('aria-pressed', String(on));
      playButton.setAttribute('aria-label', on ? 'Pause the welcome' : 'Play the welcome');
    }

    playButton.addEventListener('click', () => {
      if (player.paused) void player.play().catch(() => undefined);
      else player.pause();
    });
    player.addEventListener('play', () => setPlaying(true));
    player.addEventListener('pause', () => setPlaying(false));
    player.addEventListener('loadedmetadata', paint);
    player.addEventListener('timeupdate', paint);
    player.addEventListener('ended', () => {
      paint();
      setPlaying(false);
    });
    track?.addEventListener('click', (event) => {
      const rect = track.getBoundingClientRect();
      const ratio = Math.min(Math.max((event.clientX - rect.left) / rect.width, 0), 1);
      if (player.duration > 0) player.currentTime = ratio * player.duration;
      paint();
    });
    track?.addEventListener('keydown', (event) => {
      if (!(event instanceof KeyboardEvent)) return;
      const step = (player.duration || 0) / 20;
      if (event.key === 'ArrowRight') {
        player.currentTime = Math.min(player.currentTime + step, player.duration || 0);
        event.preventDefault();
      } else if (event.key === 'ArrowLeft') {
        player.currentTime = Math.max(player.currentTime - step, 0);
        event.preventDefault();
      }
      paint();
    });
    paint();
  });
}
initTheme();
initReveal();
initFilters();
initCopy();
initListen();
