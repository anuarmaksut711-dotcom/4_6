'use strict';
(() => {
  function node(tag, text = '', classes = '') {
    const element = document.createElement(tag);
    element.textContent = text;
    for (const name of classes.split(' ').filter(Boolean)) element.classList.add(name);
    return element;
  }
  function show(element, visible) {
    element.hidden = !visible;
    element.classList.toggle('d-none', !visible);
    return visible;
  }
  function money(amount) { return `${new Intl.NumberFormat('ru-RU').format(amount)} ₸`; }
  function reference() { return Math.floor(Math.random() * 0x100000000).toString(16).padStart(8, '0').toUpperCase(); }
  window.PixelMain = Object.freeze({node, show, money, reference});
  document.addEventListener('DOMContentLoaded', () => {
    const visitNote = document.querySelector('.visit-note .small');
    if (visitNote) visitNote.textContent = 'Составьте план визита. Для реального посещения администратор подтвердит места и условия по телефону.';
    for (const paragraph of document.querySelectorAll('.pixel-disclosure p')) {
      if (paragraph.firstChild?.nodeType === Node.TEXT_NODE) {
        paragraph.firstChild.textContent = paragraph.firstChild.textContent.replace('Кнопка «Отправить заявку»', 'Кнопка «Забронировать»');
      }
    }
    // Existing navigation keeps its appearance and describes the shared selection.
    const update = () => {
      const state = window.PixelCart?.getSnapshot();
      for (const link of document.querySelectorAll('nav a[href="booking.html"]')) {
        if (state?.count) link.title = `Выбрано пакетов: ${state.count}, ${money(state.total)}`;
        else link.removeAttribute('title');
      }
    };
    window.addEventListener('pixel:cartchange', update);
    window.PixelCart?.ready?.then(update);
    update();
  });
})();
