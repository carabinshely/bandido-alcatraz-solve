(() => {
  'use strict';
  const english = document.documentElement.lang === 'en';
  const text = (ru, en) => english ? en : ru;
  const views = ['ideas', 'policies', 'journey'];
  function read(key) {
    try { return localStorage.getItem(key); } catch { return null; }
  }
  function remember(key, value) {
    try { localStorage.setItem(key, value); } catch { /* Storage is optional. */ }
  }
  const queryView = new URL(location.href).searchParams.get('view');
  const entryView = history.state?.view;
  let view = views.includes(queryView) ? queryView : views.includes(entryView) ? entryView : read('bandido-view');
  if (!views.includes(view)) view = 'ideas';
  const languageSwitch = document.getElementById('language-switch');
  function languageLink() {
    if (!languageSwitch) return;
    const url = new URL(languageSwitch.href);
    url.search = location.search;
    if (new URL(location.href).searchParams.has('view')) url.searchParams.set('view', view);
    url.hash = location.hash;
    languageSwitch.href = url.href;
  }
  languageSwitch?.addEventListener('click', () => {
    languageLink();
    remember('bandido-language', languageSwitch.dataset.language);
  });
  if (!english && document.body.dataset.page === 'home' && location.pathname.endsWith('/') && read('bandido-language') === 'en') {
    languageLink();
    location.replace(languageSwitch.href);
    return;
  }
  function contextualLinks() {
    document.querySelectorAll('a[data-return], a[data-catalog-link], a.policy-link, a.result-link').forEach(link => {
      const url = new URL(link.getAttribute('href'), location.href);
      url.searchParams.set('view', view);
      link.href = url.href;
    });
    languageLink();
  }
  function selectView(next, write = false) {
    if (!views.includes(next)) next = 'ideas';
    view = next;
    document.querySelectorAll('[role=tab][data-view]').forEach(tab => {
      const active = tab.dataset.view === view;
      tab.setAttribute('aria-selected', String(active));
      tab.tabIndex = active ? 0 : -1;
      document.getElementById(tab.getAttribute('aria-controls')).hidden = !active;
    });
    if (write) {
      remember('bandido-view', view);
      const url = new URL(location.href);
      url.searchParams.set('view', view);
      history.pushState({ view }, '', url);
    }
    contextualLinks();
  }
  const tabs = [...document.querySelectorAll('[role=tab][data-view]')];
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectView(tab.dataset.view, true));
    tab.addEventListener('keydown', event => {
      let target;
      if (event.key === 'ArrowRight') target = (index + 1) % tabs.length;
      if (event.key === 'ArrowLeft') target = (index + tabs.length - 1) % tabs.length;
      if (event.key === 'Home') target = 0;
      if (event.key === 'End') target = tabs.length - 1;
      if (target !== undefined) {
        event.preventDefault();
        selectView(tabs[target].dataset.view, true);
        tabs[target].focus();
      }
    });
  });
  selectView(view);
  if (tabs.length) history.replaceState({ ...history.state, view }, '', location.href);
  if (views.includes(queryView)) remember('bandido-view', queryView);
  window.addEventListener('popstate', event => {
    const next = new URL(location.href).searchParams.get('view');
    selectView(views.includes(next) ? next : event.state?.view);
    remember('bandido-view', view);
  });

  const themes = ['system', 'light', 'dark'];
  const themeNames = english ? { system: 'system', light: 'light', dark: 'dark' } : { system: 'системная', light: 'светлая', dark: 'тёмная' };
  let theme = read('bandido-theme');
  if (!themes.includes(theme)) theme = 'system';
  const toggle = document.getElementById('theme-toggle');
  function renderTheme() {
    if (theme === 'system') delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = theme;
    toggle.textContent = text('Тема: ', 'Theme: ') + themeNames[theme];
    toggle.setAttribute('aria-label', text('Цветовая тема: ', 'Colour theme: ') + themeNames[theme] + text('. Переключить', '. Switch'));
  }
  renderTheme();
  toggle.addEventListener('click', () => {
    theme = themes[(themes.indexOf(theme) + 1) % themes.length];
    remember('bandido-theme', theme);
    renderTheme();
  });
  document.querySelectorAll('.header nav a').forEach(link => {
    if (new URL(link.href).pathname === location.pathname) link.setAttribute('aria-current', 'page');
  });
  function revealAnchor() {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
    const target = document.getElementById(id);
    if (!target) return;
    for (let parent = target; parent; parent = parent.parentElement) {
      if (parent.tagName === 'DETAILS') parent.open = true;
    }
    requestAnimationFrame(() => target.scrollIntoView());
  }
  window.addEventListener('hashchange', revealAnchor);
  window.addEventListener('hashchange', languageLink);
  revealAnchor();

  const dataNode = document.getElementById('board-data');
  if (!dataNode) return;
  const data = JSON.parse(dataNode.textContent);
  const dirs = { N: [0, -1], E: [1, 0], S: [0, 1], W: [-1, 0] };
  function node(tag, attrs, parent) {
    const element = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [key, value] of Object.entries(attrs)) element.setAttribute(key, String(value));
    if (parent) parent.append(element);
    return element;
  }
  function drawBoard(target, observation, added = false, hand = false) {
    const cells = observation.board.cells;
    const extents = hand ? cells : [data.original, data.chosen, data.a, data.b].filter(Boolean).flatMap(o => o.board.cells);
    const minX = Math.min(...extents.map(c => c.x)) - .2;
    const minY = Math.min(...extents.map(c => c.y)) - .2;
    const maxX = Math.max(...extents.map(c => c.x)) + 1.2;
    const maxY = Math.max(...extents.map(c => c.y)) + 1.2;
    const svg = node('svg', { viewBox: `${minX} ${minY} ${maxX - minX} ${maxY - minY}`, role: 'img', 'aria-label': hand ? text('Точная геометрия карты', 'Exact card geometry') : text('Игровое поле; кольцами отмечены открытые концы', 'Game board; rings mark open ends') });
    const occupied = new Set(cells.map(c => `${c.x},${c.y}`));
    const last = observation.board.placements.at(-1);
    const newCells = new Set(added ? last.cells.map(c => c.join(',')) : []);
    for (const cell of cells) {
      node('rect', { x: cell.x, y: cell.y, width: 1, height: 1, fill: cell.water ? '#a8d5e0' : newCells.has(`${cell.x},${cell.y}`) ? '#d6e7bd' : '#fffaf0', stroke: '#aba68d', 'stroke-width': .025, 'data-cell': '' }, svg);
      if (cell.water) {
        for (let offset = .68; offset < .94; offset += .1) node('path', { d: `M${cell.x + .1} ${cell.y + offset}q.1 -.06 .2 0t.2 0t.2 0t.2 0`, fill: 'none', stroke: '#23576c', 'stroke-width': .035, 'data-water': '' }, svg);
      }
      for (const edge of cell.tunnel_edges) {
        const [dx, dy] = dirs[edge];
        node('path', { d: `M${cell.x + .5} ${cell.y + .5}L${cell.x + .5 + dx * .5} ${cell.y + .5 + dy * .5}`, fill: 'none', stroke: '#353b2a', 'stroke-width': .16, 'stroke-linecap': 'round' }, svg);
      }
      if (cell.tunnel_edges.length === 1) node('circle', { cx: cell.x + .5, cy: cell.y + .5, r: .08, fill: '#353b2a' }, svg);
    }
    for (const placement of observation.board.placements) {
      const set = new Set(placement.cells.map(c => c.join(',')));
      let d = '';
      for (const [x, y] of placement.cells) {
        if (!set.has(`${x},${y - 1}`)) d += `M${x} ${y}h1`;
        if (!set.has(`${x + 1},${y}`)) d += `M${x + 1} ${y}v1`;
        if (!set.has(`${x},${y + 1}`)) d += `M${x} ${y + 1}h1`;
        if (!set.has(`${x - 1},${y}`)) d += `M${x} ${y}v1`;
      }
      const highlight = added && placement === last;
      node('path', { d, fill: 'none', stroke: highlight ? '#28553b' : placement.kind === 'start' ? '#245da0' : '#79765f', 'stroke-width': highlight || placement.kind === 'start' ? .075 : .035 }, svg);
    }
    if (!hand) for (const cell of cells) for (const edge of cell.tunnel_edges) {
      const [dx, dy] = dirs[edge];
      if (!occupied.has(`${cell.x + dx},${cell.y + dy}`)) node('circle', { cx: cell.x + .5 + dx * .5, cy: cell.y + .5 + dy * .5, r: .065, fill: '#fffaf0', stroke: '#a22921', 'stroke-width': .045, 'data-open-end': '' }, svg);
    }
    target.replaceChildren(svg);
  }
  document.querySelectorAll('[data-board=home]').forEach(target => drawBoard(target, data.original));
  const lesson = document.querySelector('[data-board=lesson]');
  const hand = document.getElementById('hand');
  if (hand) data.original.hand.forEach((card, i) => {
    const item = document.createElement('div');
    item.className = 'hand-piece';
    item.dataset.handIndex = i;
    const board = document.createElement('div');
    board.className = 'board';
    const label = document.createElement('p');
    label.textContent = `${i + 1}. ${card.is_exit ? text('Выход EXIT', 'EXIT card') : card.material ? text('Снаряжение', 'Equipment') : card.cells.some(c => c.water) ? text('Тоннель с водой', 'Tunnel with water') : text('Тоннель', 'Tunnel')}`;
    item.append(board, label);
    hand.append(item);
    drawBoard(board, { board: { cells: card.cells, placements: [{ cells: card.cells.map(c => [c.x, c.y]), kind: 'ordinary' }] } }, false, true);
  });
  function renderStep(step) {
    const observation = step === 'before' ? data.original : data[step];
    if (!observation || !lesson) return;
    drawBoard(lesson, observation, step !== 'before');
    document.querySelectorAll('[data-step]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.step === step)));
    const water = observation.board.cells.filter(c => c.water).length;
    const open = lesson.querySelectorAll('[data-open-end]').length;
    document.getElementById('board-caption').textContent = english ? `${open} open ends · ${water ? `${water} water half-cell${water === 1 ? '' : 's'}` : 'no water'}` : `${open} открытых концов · ${water ? `${water} водное полуполе` : 'воды нет'}`;
    const card = step === 'chosen' ? data.chosenMove.hand_index : step === 'a' ? 2 : step === 'b' ? 4 : null;
    document.querySelectorAll('[data-hand-index]').forEach(item => item.dataset.active = String(Number(item.dataset.handIndex) === card));
    if (data.ab) {
      document.getElementById('choice-title').textContent = step === 'a' ? text('A: продолжить без новой воды', 'A: extend without new water') : step === 'b' ? text('B: закрыть два конца и добавить воду', 'B: close two ends and add water') : text('Одна позиция — два продолжения', 'One position, two continuations');
      document.getElementById('choice-description').textContent = step === 'a' ? text('Карта 3 продолжает тоннель снизу. Остаётся пять открытых концов, воды нет. Немедленная оценка V4: 0.', 'Card 3 extends the tunnel at the bottom. Five open ends remain, with no water. Immediate V4 score: 0.') : step === 'b' ? text('Карта 5 занимает промежуток слева сверху. Открытых концов три, появилась вода с двумя занятыми соседями. Оценка V4: −21 800.', 'Card 5 fills the gap at the upper left. Three open ends remain, with new water and two occupied neighbours. V4 score: −21,800.') : text('Карта 3 продолжает тоннель без новой воды. Карта 5 закрывает два конца, но добавляет водное полуполе.', 'Card 3 extends a tunnel without new water. Card 5 closes two ends but adds a water half-cell.');
    }
  }
  document.querySelectorAll('[data-step]').forEach(button => button.addEventListener('click', () => renderStep(button.dataset.step)));
  if (lesson) renderStep('before');
})();
