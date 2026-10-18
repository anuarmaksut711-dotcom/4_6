'use strict';
(() => {
  const M = window.PixelMain;
  const search = document.getElementById('games-search');
  if (!search) return;
  const category = document.getElementById('games-category');
  const tools = document.getElementById('games-tools');
  const results = document.getElementById('games-results');
  const empty = document.getElementById('games-empty');
  const games = document.getElementById('games-list');
  const apps = document.getElementById('apps-list');
  const catalog = [...document.querySelectorAll('#games-list > [data-game-id], #apps-list > [data-game-id]')].map(element => ({
    id: element.dataset.gameId,
    name: element.querySelector('h2').textContent,
    category: element.dataset.gameCategory,
    aliases: element.dataset.gameSearch,
    genre: element.querySelector('article > p').textContent,
    template: element.cloneNode(true)
  }));
  function normalize(value) { return value.normalize('NFKC').toLocaleLowerCase('ru-RU').trim().replace(/\s+/g, ' '); }
  function matches(item, query, selectedCategory) {
    const words = normalize(query).split(' ').filter(Boolean);
    return (selectedCategory === 'all' || item.category === selectedCategory)
      && words.every(word => normalize(`${item.name} ${item.aliases}`).includes(word));
  }
  function renderCard(item) {
    // Reuse the original card structure, artwork and all existing classes.
    return item.template.cloneNode(true);
  }
  function renderCards(parent, items) {
    parent.replaceChildren(...items.map(renderCard));
    return items.length;
  }
  function filter() {
    const filtered = catalog.filter(item => matches(item, search.value, category.value));
    const gameCount = renderCards(games, filtered.filter(item => item.category !== 'apps'));
    const appCount = renderCards(apps, filtered.filter(item => item.category === 'apps'));
    results.textContent = `Показано: ${filtered.length} из ${catalog.length}`;
    M.show(empty, filtered.length === 0);
    M.show(document.getElementById('games-heading'), gameCount > 0);
    M.show(games, gameCount > 0);
    M.show(document.getElementById('apps-section'), appCount > 0);
    return filtered.length;
  }
  function reset() { search.value = ''; category.value = 'all'; filter(); search.focus(); }
  search.addEventListener('input', filter);
  category.addEventListener('change', filter);
  document.getElementById('games-reset').addEventListener('click', reset);
  document.getElementById('games-empty-reset').addEventListener('click', reset);
  M.show(tools, true); M.show(results, true); filter();
})();
