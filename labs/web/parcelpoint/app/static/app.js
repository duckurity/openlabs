'use strict';

(() => {
  const $ = (selector, parent = document) => parent.querySelector(selector);
  const state = { lockers: [], selected: null, detailController: null, user: null, token: null, courierLoading: false };
  const statusNames = { available: 'Available', in_transit: 'In transit', held: 'Held' };
  let noticeTimer;

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function notice(message, error = false) {
    const node = $('#status-message');
    node.textContent = message;
    node.classList.toggle('error', error);
    node.hidden = false;
    clearTimeout(noticeTimer);
    noticeTimer = setTimeout(() => { node.hidden = true; }, error ? 12000 : 7000);
  }

  async function api(path, options = {}) {
    const headers = { Accept: 'application/json', ...options.headers };
    if (options.body !== undefined) headers['Content-Type'] = 'application/json';
    if (state.token) headers.Authorization = `Bearer ${state.token}`;
    let response;
    try {
      response = await fetch(path, {
        ...options, headers, credentials: 'same-origin',
        body: options.body === undefined ? undefined : JSON.stringify(options.body)
      });
    } catch (error) {
      if (error.name === 'AbortError') throw error;
      throw new Error('Cannot reach ParcelPoint. Check the service and try again.');
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (response.status === 401 && state.token && !['/api/auth/login', '/api/auth/register'].includes(path)) {
        clearSession();
        notice('Your session has expired. Sign in again to continue.', true);
      }
      const error = new Error(data.error || `Request failed (${response.status}). Try again.`);
      error.status = response.status;
      throw error;
    }
    return data;
  }

  async function busy(button, action) {
    if (button.disabled) return;
    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    const original = button.textContent;
    button.textContent = 'Working…';
    try { return await action(); }
    finally {
      button.disabled = false;
      button.removeAttribute('aria-busy');
      button.textContent = original;
    }
  }

  function showView() {
    const requested = location.hash.slice(1) || 'depot';
    const view = ['depot', 'account', 'courier'].includes(requested) ? requested : 'depot';
    document.querySelectorAll('.view').forEach(node => { node.hidden = node.id !== `view-${view}`; });
    document.querySelectorAll('[data-view]').forEach(link => {
      if (link.dataset.view === view) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    document.title = `${{ depot: 'Depot', account: 'My account', courier: 'Courier dispatch' }[view]} · ParcelPoint`;
    if (view === 'courier') loadCourier();
  }

  function badge(status) {
    const safeStatus = Object.hasOwn(statusNames, status) ? status : 'available';
    const node = el('span', `badge ${safeStatus}`);
    const dot = el('i', `status-dot ${safeStatus}`);
    dot.setAttribute('aria-hidden', 'true');
    node.append(dot, document.createTextNode(statusNames[status] || status));
    return node;
  }

  function renderLockers() {
    const search = $('#locker-search').value.trim().toLowerCase();
    const district = $('#district-filter').value;
    const status = $('#status-filter').value;
    const filtered = state.lockers.filter(locker =>
      (!district || locker.district === district) && (!status || locker.status === status) &&
      `${locker.id} ${locker.name} ${locker.district}`.toLowerCase().includes(search));
    const bank = $('#locker-bank');
    bank.replaceChildren();
    $('#match-count').textContent = `${filtered.length} of ${state.lockers.length} lockers`;
    if (!filtered.length) {
      const empty = el('div', 'bank-placeholder');
      empty.append(el('h3', '', 'No matching lockers'), el('p', '', 'Try another name, district or status.'));
      const clear = el('button', 'button secondary', 'Clear filters');
      clear.type = 'button';
      clear.addEventListener('click', clearFilters);
      empty.append(clear);
      bank.append(empty);
      return;
    }
    for (const locker of filtered) {
      const safeStatus = Object.hasOwn(statusNames, locker.status) ? locker.status : 'available';
      const door = el('button', `locker-door ${safeStatus}`);
      door.type = 'button';
      door.setAttribute('aria-pressed', String(state.selected === locker.id));
      door.setAttribute('aria-controls', 'locker-detail');
      door.setAttribute('aria-label', `${locker.id}, ${locker.name}, ${locker.district}, ${statusNames[locker.status] || locker.status}`);
      door.dataset.lockerId = locker.id;
      const statusLabel = el('span', 'locker-status');
      const dot = el('i', `status-dot ${safeStatus}`);
      dot.setAttribute('aria-hidden', 'true');
      statusLabel.append(dot, document.createTextNode(statusNames[locker.status] || locker.status));
      const capacity = el('progress');
      capacity.max = Math.max(1, locker.capacity);
      capacity.value = locker.parcels;
      capacity.setAttribute('aria-label', `${locker.id} capacity: ${locker.parcels} of ${locker.capacity} parcels`);
      door.append(el('span', 'locker-id', locker.id), el('span', 'locker-name', locker.name), statusLabel,
        capacity, el('span', 'locker-capacity', `${locker.parcels} / ${locker.capacity} parcels`));
      door.addEventListener('click', () => selectLocker(locker.id));
      bank.append(door);
    }
  }

  function clearFilters() {
    $('#locker-search').value = '';
    $('#district-filter').value = '';
    $('#status-filter').value = '';
    renderLockers();
    $('#locker-search').focus();
  }

  function readableTime(value) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value || 'Not recorded') : date.toLocaleString([], {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
    });
  }

  async function selectLocker(id) {
    state.selected = id;
    renderLockers();
    // Repainting the bank must not discard keyboard focus on the selected door.
    const selectedDoor = Array.from(document.querySelectorAll('.locker-door')).find(node => node.dataset.lockerId === id);
    if (selectedDoor) selectedDoor.focus({ preventScroll: true });
    if (state.detailController) state.detailController.abort();
    const controller = new AbortController();
    state.detailController = controller;
    const panel = $('#locker-detail');
    panel.setAttribute('aria-busy', 'true');
    panel.replaceChildren(el('p', 'detail-address', `Loading ${id}…`));
    try {
      const { locker } = await api(`/api/lockers/${encodeURIComponent(id)}`, { signal: controller.signal });
      if (state.selected !== id) return;
      const content = el('div', 'detail-content');
      const top = el('div', 'detail-top');
      top.append(el('code', '', locker.id), badge(locker.status));
      const facts = el('dl', 'detail-facts');
      for (const [label, value] of [['District', locker.district], ['Parcels', `${locker.parcels} / ${locker.capacity}`]]) {
        const fact = el('div');
        fact.append(el('dt', '', label), el('dd', '', value));
        facts.append(fact);
      }
      content.append(top, el('h2', '', locker.name), el('p', 'detail-address', locker.address), facts);
      if (locker.courier) {
        const contact = el('p', 'courier-contact', locker.courier.name);
        // Display contact data as text, never interpret server values as markup or links.
        contact.append(el('span', 'contact-email', locker.courier.email));
        content.append(el('h3', '', 'Assigned courier'), contact);
      }
      content.append(el('h3', '', 'Recent activity'));
      const events = el('ol', 'event-list');
      for (const event of locker.events || []) {
        const item = el('li', '', event.text);
        const time = el('time', '', readableTime(event.time));
        time.dateTime = event.time;
        item.append(time);
        events.append(item);
      }
      if (!events.children.length) content.append(el('p', 'detail-address', 'No activity recorded for this locker.'));
      else content.append(events);
      content.append(el('p', 'detail-updated', `Updated ${readableTime(locker.updated_at)}`));
      panel.replaceChildren(content);
      notice(`${locker.id} selected. Locker details loaded.`);
    } catch (error) {
      if (error.name === 'AbortError') return;
      panel.replaceChildren(el('p', 'inline-notice error', error.message));
      const retry = el('button', 'button secondary', 'Retry locker details');
      retry.type = 'button';
      retry.addEventListener('click', () => selectLocker(id));
      panel.append(retry);
      notice(error.message, true);
    } finally {
      if (state.detailController === controller) panel.setAttribute('aria-busy', 'false');
    }
  }

  async function loadLockers() {
    const bank = $('#locker-bank');
    bank.setAttribute('aria-busy', 'true');
    try {
      const { lockers } = await api('/api/lockers');
      state.lockers = lockers;
      const districts = [...new Set(lockers.map(locker => locker.district))].sort();
      const select = $('#district-filter');
      const previous = select.value;
      select.replaceChildren(new Option('All districts', ''));
      districts.forEach(district => select.add(new Option(district, district)));
      select.value = districts.includes(previous) ? previous : '';
      $('#total-lockers').textContent = lockers.length;
      $('#available-lockers').textContent = lockers.filter(locker => locker.status === 'available').length;
      $('#held-lockers').textContent = lockers.filter(locker => locker.status === 'held').length;
      $('#network-updated').textContent = `Synced ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
      renderLockers();
    } catch (error) {
      bank.replaceChildren(el('p', 'bank-placeholder', error.message));
      $('#match-count').textContent = 'Network unavailable';
      notice(error.message, true);
    } finally { bank.setAttribute('aria-busy', 'false'); }
  }

  function feedback(form, message, error = false) {
    const output = $('.form-feedback', form);
    output.textContent = message;
    output.hidden = false;
    output.classList.toggle('error', error);
  }

  function bindForm(id, action) {
    const form = $(id);
    form.addEventListener('submit', event => {
      event.preventDefault();
      const button = $('button[type="submit"]', form);
      busy(button, async () => {
        $('.form-feedback', form).hidden = true;
        try { await action(Object.fromEntries(new FormData(form)), form); }
        catch (error) { feedback(form, error.message, true); notice(error.message, true); }
      });
    });
  }

  function updateAccount() {
    const signedIn = Boolean(state.user);
    $('#auth-panel').hidden = signedIn;
    $('#profile-panel').hidden = !signedIn;
    $('#courier-nav').hidden = !signedIn || state.user.role !== 'courier';
    $('#session-label').textContent = signedIn ? `${state.user.name} · ${state.user.role}` : 'Public access';
    $('#account-link').textContent = signedIn ? 'My account' : 'Sign in';
    if (signedIn) {
      $('#profile-name').textContent = state.user.name;
      $('#profile-email').textContent = state.user.email;
      $('#profile-role').textContent = state.user.role;
      $('#profile-avatar').textContent = state.user.name.slice(0, 1).toUpperCase();
      $('#request-email').value = state.user.email;
    }
  }

  function clearSession() {
    state.token = null;
    state.user = null;
    try { sessionStorage.removeItem('parcelpoint.session'); } catch (_) { /* Storage is optional. */ }
    $('#mailbox-messages').replaceChildren(el('p', 'empty-message', 'Sign in to read your lab mailbox.'));
    $('#route-board').replaceChildren();
    $('#manifest-content').replaceChildren(el('p', 'empty-message', 'Open a held locker to view its release manifest.'));
    $('#checkpoint-value').textContent = '';
    $('#courier-name').textContent = '';
    $('#courier-email').textContent = '';
    $('#courier-assigned').textContent = '–';
    $('#courier-held').textContent = '–';
    $('#courier-workspace').hidden = true;
    $('#courier-gate').hidden = false;
    $('#profile-name').textContent = '';
    $('#profile-email').textContent = '';
    document.querySelectorAll('#profile-panel form').forEach(form => {
      form.reset();
      $('.form-feedback', form).hidden = true;
    });
    updateAccount();
    if (location.hash === '#courier') location.hash = 'account';
  }

  function setSession(data) {
    clearSession();
    state.token = data.token;
    state.user = data.user;
    try { sessionStorage.setItem('parcelpoint.session', data.token); } catch (_) { /* Keep this tab usable without storage. */ }
    updateAccount();
    $('#login-form').reset();
    $('#register-form').reset();
    loadMailbox();
  }

  async function restoreSession() {
    try { state.token = sessionStorage.getItem('parcelpoint.session'); } catch (_) { /* No persisted session. */ }
    if (!state.token) return;
    try {
      const { user } = await api('/api/me');
      state.user = user;
      updateAccount();
      loadMailbox();
      if (location.hash === '#courier') loadCourier();
    } catch (error) {
      if (error.status !== 401) notice(error.message, true);
      clearSession();
    }
  }

  async function loadMailbox() {
    if (!state.user) return;
    const token = state.token;
    const target = $('#mailbox-messages');
    target.setAttribute('aria-busy', 'true');
    try {
      const { messages } = await api('/api/mailbox');
      if (token !== state.token) return;
      target.replaceChildren();
      if (!messages.length) target.append(el('p', 'empty-message', 'Your mailbox is empty. Password reset messages will appear here when requested.'));
      for (const message of messages) {
        const item = el('article', 'mail-message');
        const time = el('time', '', readableTime(message.created_at));
        time.dateTime = message.created_at;
        item.append(el('h3', '', message.subject), time, el('p', '', message.body));
        if (message.code) {
          const code = el('div', 'mail-code');
          const use = el('button', 'button secondary', 'Use reset code');
          use.type = 'button';
          use.addEventListener('click', () => {
            $('#reset-code').value = message.code;
            $('#reset-password').focus();
            notice('Reset code added. Enter your new password to continue.');
          });
          code.append(el('span', 'field-help', 'Reset code'), el('code', '', message.code), use);
          item.append(code);
        }
        target.append(item);
      }
    } catch (error) {
      if (token === state.token) target.replaceChildren(el('p', 'empty-message', error.message));
      notice(error.message, true);
    } finally { target.setAttribute('aria-busy', 'false'); }
  }

  async function loadCourier() {
    const permitted = state.user && state.user.role === 'courier';
    $('#courier-gate').hidden = Boolean(permitted);
    $('#courier-workspace').hidden = !permitted;
    if (!state.user || state.user.role !== 'courier' || state.courierLoading) return;
    const token = state.token;
    state.courierLoading = true;
    const board = $('#route-board');
    board.setAttribute('aria-busy', 'true');
    $('#courier-error').hidden = true;
    if (!board.children.length) board.append(el('p', 'empty-message', 'Loading your assigned routes…'));
    try {
      const [dashboard, { routes }] = await Promise.all([
        api('/api/courier/dashboard'), api('/api/courier/routes')
      ]);
      if (token !== state.token) return;
      $('#courier-name').textContent = dashboard.courier.name;
      $('#courier-email').textContent = dashboard.courier.email;
      $('#courier-assigned').textContent = dashboard.summary.assigned_lockers;
      $('#courier-held').textContent = dashboard.summary.held;
      $('#checkpoint-value').textContent = dashboard.checkpoint_flag;
      board.replaceChildren();
      if (!routes.length) board.append(el('p', 'empty-message', 'No routes assigned. Refresh dispatch to check for new assignments.'));
      for (const route of routes) {
        const section = el('section', 'route-section');
        const heading = el('div', 'route-heading');
        heading.append(el('h2', '', route.name), el('span', '', `${route.id} · ${route.lockers.length} assigned lockers`));
        section.append(heading);
        if (route.dispatch_note) section.append(el('p', 'route-note', route.dispatch_note));
        if (!route.lockers.length) section.append(el('p', 'empty-message', 'This route has no assigned lockers.'));
        for (const locker of route.lockers) {
          const row = el('div', 'route-row');
          const stop = el('div', 'route-stop');
          stop.append(el('code', '', locker.id), el('h3', '', locker.name));
          const actions = el('div', 'route-actions');
          const inspect = el('button', 'text-button', 'View locker');
          inspect.type = 'button';
          inspect.setAttribute('aria-label', `View locker ${locker.id}`);
          inspect.addEventListener('click', () => { location.hash = 'depot'; selectLocker(locker.id); });
          actions.append(inspect);
          if (locker.status === 'held') {
            const open = el('button', 'button', 'Open locker');
            open.type = 'button';
            open.setAttribute('aria-label', `Open locker ${locker.id}`);
            open.addEventListener('click', () => busy(open, () => openLocker(locker.id)));
            actions.append(open);
          } else actions.append(el('span', '', 'No release pending'));
          row.append(stop, badge(locker.status), actions);
          section.append(row);
        }
        board.append(section);
      }
    } catch (error) {
      if (token === state.token) {
        $('#courier-error').textContent = `${error.message} Use Refresh dispatch to try again.`;
        $('#courier-error').hidden = false;
        if (board.textContent.includes('Loading your assigned routes')) board.replaceChildren();
      }
      notice(error.message, true);
    } finally {
      state.courierLoading = false;
      board.setAttribute('aria-busy', 'false');
    }
  }

  async function openLocker(id) {
    if (!state.user || state.user.role !== 'courier') return;
    const token = state.token;
    const target = $('#manifest-content');
    target.setAttribute('aria-busy', 'true');
    try {
      const { manifest } = await api(`/api/courier/lockers/${encodeURIComponent(id)}/open`, { method: 'POST', body: {} });
      if (token !== state.token) return;
      const record = el('div', 'manifest-record detail-content');
      record.append(el('span', 'badge', 'Release authorized'), el('h3', '', manifest.reference));
      const facts = el('dl');
      for (const [label, value] of [['Locker', manifest.locker_id], ['Recipient', manifest.recipient], ['Contents', manifest.contents]]) {
        const fact = el('div');
        fact.append(el('dt', '', label), el('dd', '', typeof value === 'object' ? JSON.stringify(value, null, 2) : value));
        facts.append(fact);
      }
      const release = el('div', 'release-record');
      release.append(el('h3', '', 'Release record'), el('code', '', manifest.release_flag));
      record.append(facts, release);
      target.replaceChildren(record);
      target.focus({ preventScroll: false });
      notice(`Locker ${id} opened. Release manifest loaded.`);
    } catch (error) {
      if (token === state.token) target.replaceChildren(el('p', 'empty-message', `${error.message} Select Open locker to try again.`));
      notice(error.message, true);
    } finally { target.setAttribute('aria-busy', 'false'); }
  }

  $('#refresh-courier').addEventListener('click', event => busy(event.currentTarget, loadCourier));

  function selectAuthTab(tab) {
    document.querySelectorAll('#auth-tabs [role="tab"]').forEach(node => {
      const selected = node === tab;
      node.setAttribute('aria-selected', String(selected));
      node.tabIndex = selected ? 0 : -1;
      $(`#${node.getAttribute('aria-controls')}`).hidden = !selected;
    });
  }

  document.querySelectorAll('#auth-tabs [role="tab"]').forEach(tab => {
    tab.addEventListener('click', () => selectAuthTab(tab));
    tab.addEventListener('keydown', event => {
      const tabs = Array.from(document.querySelectorAll('#auth-tabs [role="tab"]'));
      let index = tabs.indexOf(tab);
      if (event.key === 'ArrowRight') index = (index + 1) % tabs.length;
      else if (event.key === 'ArrowLeft') index = (index - 1 + tabs.length) % tabs.length;
      else if (event.key === 'Home') index = 0;
      else if (event.key === 'End') index = tabs.length - 1;
      else return;
      event.preventDefault();
      selectAuthTab(tabs[index]);
      tabs[index].focus();
    });
  });

  bindForm('#login-form', async (body, form) => {
    const data = await api('/api/auth/login', { method: 'POST', body });
    setSession(data);
    feedback(form, 'Signed in.');
    notice(`Welcome back, ${data.user.name}.`);
    location.hash = data.user.role === 'courier' ? 'courier' : 'account';
  });
  bindForm('#register-form', async (body, form) => {
    const data = await api('/api/auth/register', { method: 'POST', body });
    setSession(data);
    feedback(form, 'Your customer account is ready.');
    notice('Your account is ready. Welcome to ParcelPoint.');
    location.hash = 'account';
  });
  bindForm('#reset-request-form', async (body, form) => {
    const data = await api('/api/auth/reset/request', { method: 'POST', body });
    feedback(form, data.message);
    notice(data.message);
    await loadMailbox();
  });
  bindForm('#reset-confirm-form', async body => {
    const resetEmail = state.user.email;
    const data = await api('/api/auth/reset/confirm', {
      method: 'POST', body: { email: resetEmail, code: body.code, new_password: body.new_password }
    });
    $('#reset-code').value = '';
    $('#reset-password').value = '';
    clearSession();
    selectAuthTab($('#login-tab'));
    $('#login-email').value = resetEmail;
    $('#login-password').focus();
    notice(`${data.message} Sign in with your new password.`);
  });
  $('#logout-button').addEventListener('click', event => busy(event.currentTarget, async () => {
    try {
      await api('/api/auth/logout', { method: 'POST' });
      clearSession();
      notice('You are signed out.');
    } catch (error) { notice(error.message, true); }
  }));
  $('#refresh-mailbox').addEventListener('click', event => busy(event.currentTarget, loadMailbox));

  $('#locker-search').addEventListener('input', renderLockers);
  $('#district-filter').addEventListener('change', renderLockers);
  $('#status-filter').addEventListener('change', renderLockers);
  $('#clear-filters').addEventListener('click', clearFilters);
  $('#refresh-lockers').addEventListener('click', event => busy(event.currentTarget, async () => {
    await loadLockers();
    if (state.selected) await selectLocker(state.selected);
  }));
  window.addEventListener('hashchange', showView);
  showView();
  loadLockers();
  restoreSession();
})();
