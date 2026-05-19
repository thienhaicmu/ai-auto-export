/**
 * Viral template runtime — Phase 3A: Premium Motion System
 *
 * Reads window.__SCENE__ props, maps role → design tokens, populates DOM,
 * then signals window.__SCENE_READY__ = true.
 *
 * CONTRACT (must never break):
 *   - Only CSS Web Animations / @keyframes — NO setTimeout / setInterval
 *   - window.__SCENE_READY__ = true set after fonts (+ bg image) loaded
 *   - window.__SCENE__ injected by html_renderer.py via addInitScript
 */

(function () {
  'use strict';

  var scene  = window.__SCENE__ || {};
  var props  = scene.props     || {};

  // ── Extract props ──────────────────────────────────────────────────────────

  var ROLE            = scene.role                       || '';
  var ANIMATION_SEED  = props.animation_seed             || ((scene.index || 0) * 37 + 1000);
  var HEADLINE        = (props.headline || 'UNTITLED').toUpperCase();
  var SUBHEAD         = props.subhead                    || '';
  var BG_IMAGE        = props.background_image           || null;
  var HIGHLIGHT_IDX   = props.highlight_word_indices     || [];
  var SCENE_IDX       = scene.index != null ? scene.index : 0;
  var SCENE_DURATION  = ((scene.end || 0) - (scene.start || 0)) || 6;

  // ── Role → design tokens ───────────────────────────────────────────────────
  //
  //   Each narrative role maps to an accent colour and a short label.
  //   scene.js also sets data-role on <html> so the CSS fallback selectors
  //   in style.css activate (scene.js inline vars win via higher specificity,
  //   but the CSS selectors ensure correct colours even before JS runs).

  var ROLE_MAP = {
    hook:        { accent: '#FF3D2E', label: 'BREAKING'   },
    context:     { accent: '#00C2E0', label: 'CONTEXT'    },
    escalation:  { accent: '#FF8C00', label: 'ESCALATION' },
    twist:       { accent: '#FFD700', label: 'REVEAL'     },
    payoff:      { accent: '#06D6A0', label: 'ACTION'     },
  };

  var roleData   = ROLE_MAP[ROLE] || { accent: '#7C5CFF', label: 'SCENE' };
  var ACCENT     = props.accent_color || roleData.accent;
  var LABEL_TEXT = roleData.label;

  // ── Derive glow / dim variants from accent hex ─────────────────────────────

  function hexToRgb(hex) {
    var h = hex.replace('#', '');
    if (h.length === 3) h = h[0]+h[0]+h[1]+h[1]+h[2]+h[2];
    return parseInt(h.slice(0,2),16) + ',' +
           parseInt(h.slice(2,4),16) + ',' +
           parseInt(h.slice(4,6),16);
  }

  var rgb = hexToRgb(ACCENT);

  // ── Apply CSS custom properties ────────────────────────────────────────────

  var root = document.documentElement;
  root.style.setProperty('--accent',          ACCENT);
  root.style.setProperty('--accent-glow',     'rgba(' + rgb + ',0.45)');
  root.style.setProperty('--accent-dim',      'rgba(' + rgb + ',0.15)');
  root.style.setProperty('--scene-duration',  SCENE_DURATION + 's');

  // Role attribute activates CSS fallback colour selectors
  if (ROLE) root.setAttribute('data-role', ROLE);

  // ── Headline size — word-count-adaptive + seed micro-variation ─────────────
  //
  //   Short headlines punch larger; longer ones scale down for readability.
  //   The seed adds ±0.4 vw of deterministic variation across scenes.

  var words     = HEADLINE.trim().split(/\s+/);
  var wordCount = words.length;
  var baseSize  = wordCount <= 1 ? 16.0
                : wordCount === 2 ? 13.5
                : wordCount === 3 ? 11.5
                :                   10.0;

  var seedMod = ANIMATION_SEED % 100;
  var sizeVar = ((seedMod % 10) - 5) * 0.08;            // ±0.4 vw
  var finalSize = Math.max(8.0, baseSize + sizeVar).toFixed(1);
  root.style.setProperty('--headline-size', finalSize + 'vw');

  // ── Seed-based halo position — subtle per-scene variation ─────────────────
  //   Range: 44 – 55% horizontally (avoids extremes)

  var haloX = 44 + (seedMod % 12);
  root.style.setProperty('--halo-x', haloX + '%');

  // ── Background image ───────────────────────────────────────────────────────

  var bgEl = document.getElementById('bg');
  if (bgEl && BG_IMAGE) {
    bgEl.style.backgroundImage = "url('" + BG_IMAGE + "')";
    root.classList.add('has-bg');
  }

  // ── Label ──────────────────────────────────────────────────────────────────

  var labelEl = document.getElementById('label');
  if (labelEl) labelEl.textContent = LABEL_TEXT;

  // ── Headline with word highlights ──────────────────────────────────────────

  var headlineEl = document.getElementById('headline');
  if (headlineEl) {
    headlineEl.innerHTML = words.map(function (word, i) {
      return HIGHLIGHT_IDX.indexOf(i) !== -1
        ? '<span class="hl">' + word + '</span>'
        : word;
    }).join(' ');
  }

  // ── Subhead ────────────────────────────────────────────────────────────────

  var subheadEl = document.getElementById('subhead');
  if (subheadEl && SUBHEAD) subheadEl.textContent = SUBHEAD;

  // ── Scene badge ────────────────────────────────────────────────────────────

  var badgeEl = document.getElementById('badge');
  if (badgeEl) badgeEl.textContent = String(SCENE_IDX + 1).padStart(2, '0');

  // ── Signal ready ───────────────────────────────────────────────────────────
  //
  //   Playwright waits for window.__SCENE_READY__ === true before capturing
  //   frames. We wait for:
  //     1. document.fonts.ready  — Noto Sans/CJK @font-face loaded
  //     2. Background image decoded (if present)
  //
  //   If the bg image 404s we revert has-bg so layout stays centred.

  document.fonts.ready.then(function () {
    if (BG_IMAGE) {
      var img      = new Image();
      img.onload   = function () { window.__SCENE_READY__ = true; };
      img.onerror  = function () {
        root.classList.remove('has-bg');   // revert to centred layout
        window.__SCENE_READY__ = true;
      };
      img.src = BG_IMAGE;
    } else {
      window.__SCENE_READY__ = true;
    }
  });

})();
