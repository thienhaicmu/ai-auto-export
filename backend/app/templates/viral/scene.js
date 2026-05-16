/**
 * Viral template runtime.
 * Reads window.__SCENE__ props, populates DOM, then signals window.__SCENE_READY__ = true.
 *
 * RULES:
 *   - Only CSS Web Animations / @keyframes — NO setTimeout / setInterval
 *   - Must set window.__SCENE_READY__ = true after fonts + images loaded
 *   - Playwright injects window.__SCENE__ before page load via addInitScript
 */

(function () {
  'use strict';

  const scene = window.__SCENE__ || {};
  const props = scene.props || {};

  const ACCENT = props.accent_color || '#7C5CFF';
  const HEADLINE = props.headline || 'UNTITLED';
  const SUBHEAD = props.subhead || '';
  const BG_IMAGE = props.background_image || null;
  const HIGHLIGHT_INDICES = props.highlight_word_indices || [];
  const SCENE_IDX = scene.index != null ? scene.index : 0;
  const SCENE_DURATION = (scene.end - scene.start) || 6;

  // Apply accent colour CSS variable
  document.documentElement.style.setProperty('--accent', ACCENT);
  document.documentElement.style.setProperty('--accent-glow', ACCENT + '80');

  // Scene duration for progress bar
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
    headlineEl.innerHTML = words.map((word, i) => {
      const isHighlighted = HIGHLIGHT_INDICES.includes(i);
      return isHighlighted
        ? `<span class="hl">${word}</span>`
        : word;
    }).join(' ');
  }

  // Subhead
  const subheadEl = document.getElementById('subhead');
  if (subheadEl) subheadEl.textContent = SUBHEAD;

  // Scene badge
  const badgeEl = document.getElementById('badge');
  if (badgeEl) badgeEl.textContent = String(SCENE_IDX + 1).padStart(2, '0');

  // Spawn particles using seeded deterministic positions (animation_seed)
  spawnParticles(props.animation_seed || 0);

  // Signal ready after fonts loaded
  document.fonts.ready.then(() => {
    if (BG_IMAGE) {
      const img = new Image();
      img.onload = () => { window.__SCENE_READY__ = true; };
      img.onerror = () => { window.__SCENE_READY__ = true; };
      img.src = BG_IMAGE;
    } else {
      window.__SCENE_READY__ = true;
    }
  });

  function spawnParticles(seed) {
    const container = document.getElementById('particles');
    if (!container) return;

    // LCG pseudo-random with seed for determinism
    let s = seed || 42;
    function rand() {
      s = (s * 1664525 + 1013904223) & 0xffffffff;
      return (s >>> 0) / 0xffffffff;
    }

    const count = 12;
    for (let i = 0; i < count; i++) {
      const el = document.createElement('div');
      el.className = 'particle';
      const size = 4 + rand() * 12;
      el.style.cssText = [
        `width: ${size}px`,
        `height: ${size}px`,
        `left: ${rand() * 100}%`,
        `top: ${rand() * 100}%`,
        `--dur: ${2 + rand() * 4}s`,
        `opacity: ${0.2 + rand() * 0.5}`,
        `animation-delay: ${-rand() * 4}s`,
      ].join(';');
      container.appendChild(el);
    }
  }
})();
