/**
 * Viral template runtime.
 * Reads window.__SCENE__ props, populates DOM, then signals window.__SCENE_READY__ = true.
 *
 * RULES:
 *   - Only CSS Web Animations / @keyframes -- NO setTimeout / setInterval
 *   - Must set window.__SCENE_READY__ = true after fonts loaded
 *   - Playwright injects window.__SCENE__ before page load via addInitScript
 */

(function () {
  'use strict';

  const scene  = window.__SCENE__ || {};
  const props  = scene.props || {};

  const ACCENT            = props.accent_color || '#7C5CFF';
  const HEADLINE          = props.headline || 'UNTITLED';
  const SUBHEAD           = props.subhead || '';
  const BG_IMAGE          = props.background_image || null;
  const HIGHLIGHT_INDICES = props.highlight_word_indices || [];
  const SCENE_IDX         = scene.index != null ? scene.index : 0;
  const SCENE_DURATION    = (scene.end - scene.start) || 6;

  // Apply accent colour CSS variables
  document.documentElement.style.setProperty('--accent', ACCENT);
  document.documentElement.style.setProperty('--accent-glow', ACCENT + '73');  // 45% alpha
  document.documentElement.style.setProperty('--accent-dim',  ACCENT + '2E');  // 18% alpha

  // Scene duration drives the progress bar animation
  document.documentElement.style.setProperty('--scene-duration', SCENE_DURATION + 's');

  // Background image
  const bgEl = document.getElementById('bg');
  if (bgEl && BG_IMAGE) {
    bgEl.style.backgroundImage = `url('${BG_IMAGE}')`;
  }

  // Headline with optional word highlights
  const headlineEl = document.getElementById('headline');
  if (headlineEl) {
    const words = HEADLINE.split(' ');
    headlineEl.innerHTML = words.map(function (word, i) {
      return HIGHLIGHT_INDICES.includes(i)
        ? '<span class="hl">' + word + '</span>'
        : word;
    }).join(' ');
  }

  // Subhead
  const subheadEl = document.getElementById('subhead');
  if (subheadEl) subheadEl.textContent = SUBHEAD;

  // Scene badge
  const badgeEl = document.getElementById('badge');
  if (badgeEl) badgeEl.textContent = String(SCENE_IDX + 1).padStart(2, '0');

  // Signal ready after fonts loaded — no image wait unless BG_IMAGE is set
  document.fonts.ready.then(function () {
    if (BG_IMAGE) {
      var img = new Image();
      img.onload  = function () { window.__SCENE_READY__ = true; };
      img.onerror = function () { window.__SCENE_READY__ = true; };
      img.src = BG_IMAGE;
    } else {
      window.__SCENE_READY__ = true;
    }
  });
})();
