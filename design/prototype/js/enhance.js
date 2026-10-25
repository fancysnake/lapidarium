// Progressive enhancement: strona działa bez tego pliku.

// 1. Nagranie YouTube ładowane dopiero po kliknięciu (bez skryptów Google przy wejściu).
document.querySelectorAll('[data-youtube-id]').forEach((facade) => {
  const button = facade.querySelector('button');
  if (!button) return;
  button.addEventListener('click', () => {
    const id = facade.dataset.youtubeId;
    const iframe = document.createElement('iframe');
    iframe.src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(id)}?autoplay=1`;
    iframe.title = facade.dataset.title || 'Nagranie sesji';
    iframe.allow = 'autoplay; encrypted-media; picture-in-picture';
    iframe.allowFullscreen = true;
    facade.replaceChildren(iframe);
  });
});

// 2. Przełącznik motywu (tylko w tym prototypie — w silniku motyw wybiera SITE_THEME).
const select = document.querySelector('#theme-select');
const themeLink = document.querySelector('#theme-tokens');
if (select && themeLink) {
  select.hidden = false;
  select.closest('.theme-switch').hidden = false;
  select.addEventListener('change', () => {
    themeLink.disabled = select.value === 'base';
  });
}
