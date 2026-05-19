/**
 * Viral template runtime — Phase 3B: AI Visual Direction Layer
 *
 * Reads window.__SCENE__ props, maps role → design tokens,
 * applies visual_direction attributes and CSS vars, populates DOM,
 * then signals window.__SCENE_READY__ = true.
 *
 * CONTRACT (must never break):
 *   - Only CSS Web Animations / @keyframes — NO setTimeout / setInterval
 *   - window.__SCENE_READY__ = true set after fonts (+ bg image) loaded
 *   - window.__SCENE__ injected by html_renderer.py via addInitScript
 *   - Missing visual_direction must not crash (all reads gated with || {})
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

  // ── Visual Direction (Phase 3B) ────────────────────────────────────────────

  var VD = props.visual_direction || {};
  var VD_ENERGY     = Math.max(1, Math.min(5, parseInt(VD.energy_level, 10) || 3));
  var VD_MOTION     = VD.motion_intensity  || 'medium';
  var VD_LAYOUT     = VD.layout_mode       || 'center';
  var VD_TRANSITION = VD.transition_style  || 'cut';
  var VD_BG         = VD.background_treatment || 'gradient';
  var VD_SUB_EM     = !!VD.subtitle_emphasis;
  var VD_EMPHASIS   = Array.isArray(VD.emphasis_words) ? VD.emphasis_words : [];

  // ── Role → design tokens ───────────────────────────────────────────────────

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

  // ── Motion scale — VD_MOTION controls animation speed multiplier ───────────
  //
  //   calm=slow (1.4×), medium=normal (1.0×), high=fast (0.55×), impact=instant (0.22×)
  //   cut transition overrides to near-instant regardless of motion_intensity.

  var MOTION_SCALE = { calm: 1.4, medium: 1.0, high: 0.55, impact: 0.22 };
  var motionFactor = MOTION_SCALE[VD_MOTION] || 1.0;
  if (VD_TRANSITION === 'cut') motionFactor = Math.min(motionFactor, 0.08);

  // ── Energy → glow alpha / dim alpha ──────────────────────────────────────
  //
  //   Energy 1 → subtle; Energy 5 → intense. Applied as CSS vars.

  var glowAlpha = 0.22 + (VD_ENERGY / 5) * 0.38;   // 0.30 – 0.60
  var dimAlpha  = 0.08 + (VD_ENERGY / 5) * 0.16;   // 0.10 – 0.24

  // ── Headline energy boost ─────────────────────────────────────────────────
  //   full_bleed gets a larger multiplier by default (1.15× base)

  var baseBoost     = VD_LAYOUT === 'full_bleed' ? 1.15 : 1.0;
  var energyBoost   = baseBoost * (0.9 + (VD_ENERGY / 5) * 0.2);   // 0.936 – 1.38

  // ── Apply CSS custom properties ────────────────────────────────────────────

  var root = document.documentElement;

  root.style.setProperty('--accent',          ACCENT);
  root.style.setProperty('--accent-glow',     'rgba(' + rgb + ',' + glowAlpha.toFixed(2) + ')');
  root.style.setProperty('--accent-dim',      'rgba(' + rgb + ',' + dimAlpha.toFixed(2)  + ')');
  root.style.setProperty('--scene-duration',  SCENE_DURATION + 's');

  // Scaled motion durations
  root.style.setProperty('--dur-xs', (0.28 * motionFactor).toFixed(3) + 's');
  root.style.setProperty('--dur-sm', (0.42 * motionFactor).toFixed(3) + 's');
  root.style.setProperty('--dur-md', (0.65 * motionFactor).toFixed(3) + 's');
  root.style.setProperty('--dur-lg', (0.92 * motionFactor).toFixed(3) + 's');

  // Energy headline boost (read by full_bleed + general scaling)
  root.style.setProperty('--energy-headline-boost', energyBoost.toFixed(3));

  // ── Apply data attributes for CSS selectors ────────────────────────────────

  if (ROLE)          root.setAttribute('data-role',         ROLE);
  if (VD_MOTION)     root.setAttribute('data-motion',       VD_MOTION);
  if (VD_LAYOUT)     root.setAttribute('data-layout',       VD_LAYOUT);
  if (VD_TRANSITION) root.setAttribute('data-transition',   VD_TRANSITION);
  if (VD_BG)         root.setAttribute('data-bg-treatment', VD_BG);

  if (VD_SUB_EM) root.classList.add('subtitle-emphasis');

  // ── Headline size — word-count-adaptive + seed micro-variation ─────────────

  var words     = HEADLINE.trim().split(/\s+/);
  var wordCount = words.length;
  var baseSize  = wordCount <= 1 ? 16.0
                : wordCount === 2 ? 13.5
                : wordCount === 3 ? 11.5
                :                   10.0;

  var seedMod  = ANIMATION_SEED % 100;
  var sizeVar  = ((seedMod % 10) - 5) * 0.08;            // ±0.4 vw
  var finalSize = Math.max(8.0, baseSize + sizeVar).toFixed(1);
  root.style.setProperty('--headline-size', finalSize + 'vw');

  // ── Seed-based halo position ───────────────────────────────────────────────

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
  //
  //   Highlighted set: HIGHLIGHT_IDX from props + VD_EMPHASIS (case-insensitive,
  //   non-alpha stripped) matched against headline words.

  var emphasisSet = {};
  VD_EMPHASIS.forEach(function (ew) {
    emphasisSet[ew.toLowerCase().replace(/[^a-z0-9]/g, '')] = true;
  });

  var headlineEl = document.getElementById('headline');
  if (headlineEl) {
    headlineEl.innerHTML = words.map(function (word, i) {
      var normalised = word.toLowerCase().replace(/[^a-z0-9]/g, '');
      var isHl = HIGHLIGHT_IDX.indexOf(i) !== -1 || emphasisSet[normalised];
      return isHl ? '<span class="hl">' + word + '</span>' : word;
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
