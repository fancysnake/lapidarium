// Progressive enhancement: every page works without this file.

// Video facades are links to the provider; with scripts on, the player loads
// in place on click, so nothing from the provider loads before that.
for (const facade of document.querySelectorAll('[data-embed-url]')) {
  facade.addEventListener('click', (event) => {
    event.preventDefault();
    const iframe = document.createElement('iframe');
    iframe.src = facade.dataset.embedUrl;
    iframe.title = facade.dataset.title || '';
    iframe.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
    iframe.allowFullscreen = true;
    const frame = document.createElement('div');
    frame.className = facade.className;
    frame.append(iframe);
    facade.replaceWith(frame);
  });
}
